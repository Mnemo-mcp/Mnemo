"""Dense embedding provider using ONNX all-MiniLM-L6-v2."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import onnxruntime as ort
    from tokenizers import Tokenizer

_MODEL_NAME = "all-MiniLM-L6-v2"
_MAX_LENGTH = 128
_DIM = 384

_session: "ort.InferenceSession | None" = None
_tokenizer: "Tokenizer | None" = None
_unavailable: bool = False


def _model_dir() -> Path:
    return Path.home() / ".cache" / "mnemo" / "models" / _MODEL_NAME


def _ensure_loaded():
    global _session, _tokenizer, _unavailable
    if _session is not None or _unavailable:
        return

    model_path = _model_dir() / "model.onnx"
    tokenizer_path = _model_dir() / "tokenizer.json"

    if not model_path.exists():
        try:
            _download_model()
        except Exception:
            _unavailable = True
            return

    # Validate tokenizer.json is valid JSON before loading
    if not tokenizer_path.exists() or tokenizer_path.stat().st_size < 100:
        _unavailable = True
        return

    try:
        import json
        with open(tokenizer_path) as f:
            json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupted file — remove and mark unavailable
        tokenizer_path.unlink(missing_ok=True)
        _unavailable = True
        return

    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        _tokenizer = Tokenizer.from_file(str(tokenizer_path))
        _tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        _tokenizer.enable_truncation(max_length=_MAX_LENGTH)
        _session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    except Exception:
        _unavailable = True


def _download_model():
    """Download model files from HuggingFace."""
    import subprocess
    d = _model_dir()
    d.mkdir(parents=True, exist_ok=True)
    base = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"
    files = {"model.onnx": f"{base}/onnx/model.onnx", "tokenizer.json": f"{base}/tokenizer.json"}
    for name, url in files.items():
        dest = d / name
        if not dest.exists():
            subprocess.run(
                ["curl", "-sfSL", "--retry", "2", url, "-o", str(dest)],
                check=True,
            )
            # Validate download isn't empty/HTML error
            if dest.stat().st_size < 100:
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"Download of {name} failed: file too small")


def embed(texts: list[str]) -> np.ndarray:
    """Embed texts into 384-dim normalized vectors. Returns (N, 384) float32 array."""
    _ensure_loaded()
    if not texts or _unavailable:
        return np.zeros((len(texts) if texts else 0, _DIM), dtype=np.float32)

    # Batch in chunks of 512 to avoid memory explosion on large repos
    BATCH_SIZE = 512
    if len(texts) <= BATCH_SIZE:
        return _embed_batch(texts)

    parts = []
    for i in range(0, len(texts), BATCH_SIZE):
        parts.append(_embed_batch(texts[i:i + BATCH_SIZE]))
    return np.vstack(parts)


def _embed_batch(texts: list[str]) -> np.ndarray:
    """Embed a single batch of texts."""
    encoded = _tokenizer.encode_batch(texts)
    input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
    token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

    outputs = _session.run(None, {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids,
    })

    token_embeddings = outputs[0]
    mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
    pooled = (token_embeddings * mask_expanded).sum(axis=1) / mask_expanded.sum(axis=1).clip(min=1e-9)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-9)
    return (pooled / norms).astype(np.float32)


def embed_one(text: str) -> np.ndarray:
    """Embed a single text. Returns (384,) float32 array."""
    _ensure_loaded()
    if _unavailable:
        return np.zeros(_DIM, dtype=np.float32)
    return embed([text])[0]


def dim() -> int:
    return _DIM
