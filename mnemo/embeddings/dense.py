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


def _model_dir() -> Path:
    return Path.home() / ".cache" / "mnemo" / "models" / _MODEL_NAME


def _ensure_loaded():
    global _session, _tokenizer
    if _session is not None:
        return

    import onnxruntime as ort
    from tokenizers import Tokenizer

    model_path = _model_dir() / "model.onnx"
    if not model_path.exists():
        _download_model()

    _tokenizer = Tokenizer.from_file(str(_model_dir() / "tokenizer.json"))
    _tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
    _tokenizer.enable_truncation(max_length=_MAX_LENGTH)
    _session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])


def _download_model():
    """Download model files from HuggingFace."""
    import subprocess
    d = _model_dir()
    d.mkdir(parents=True, exist_ok=True)
    base = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"
    files = {"model.onnx": f"{base}/onnx/model.onnx", "tokenizer.json": f"{base}/tokenizer.json"}
    for name, url in files.items():
        if not (d / name).exists():
            subprocess.run(["curl", "-sL", url, "-o", str(d / name)], check=True)


def embed(texts: list[str]) -> np.ndarray:
    """Embed texts into 384-dim normalized vectors. Returns (N, 384) float32 array."""
    _ensure_loaded()
    if not texts:
        return np.zeros((0, _DIM), dtype=np.float32)

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
    return embed([text])[0]


def dim() -> int:
    return _DIM
