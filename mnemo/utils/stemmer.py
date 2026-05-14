"""Minimal Porter stemmer implementation."""

from __future__ import annotations


def _measure(stem: str) -> int:
    """Count VC sequences (consonant-vowel measure) in stem."""

    vowels = "aeiou"
    cv = ""
    for i, ch in enumerate(stem):
        if ch in vowels or (ch == "y" and i > 0 and stem[i - 1] not in vowels):
            cv += "v"
        else:
            cv += "c"
    return cv.replace("c", " ").strip().count(" ") if "v" in cv else 0


def _has_vowel(s: str) -> bool:
    vowels = "aeiou"
    for i, ch in enumerate(s):
        if ch in vowels or (ch == "y" and i > 0 and s[i - 1] not in vowels):
            return True
    return False


def _ends_double(s: str) -> bool:
    return len(s) >= 2 and s[-1] == s[-2] and s[-1] not in "aeiou"


def _cvc(s: str) -> bool:
    if len(s) < 3:
        return False
    vowels = "aeiou"
    c1, v, c2 = s[-3] not in vowels, s[-2] in vowels, s[-1] not in vowels
    return c1 and v and c2 and s[-1] not in "wxy"


def _step1a(w: str) -> str:
    if w.endswith("sses"):
        return w[:-2]
    if w.endswith("ies"):
        return w[:-2]
    if w.endswith("ss"):
        return w
    if w.endswith("s"):
        return w[:-1]
    return w


def _step1b(w: str) -> str:
    if w.endswith("eed"):
        stem = w[:-3]
        return w[:-1] if _measure(stem) > 0 else w
    for suffix in ("ed", "ing"):
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            if _has_vowel(stem):
                w = stem
                if w.endswith(("at", "bl", "iz")):
                    return w + "e"
                if _ends_double(w) and w[-1] not in "lsz":
                    return w[:-1]
                if _measure(w) == 1 and _cvc(w):
                    return w + "e"
                return w
            return w
    return w


def _step1c(w: str) -> str:
    if w.endswith("y") and _has_vowel(w[:-1]):
        return w[:-1] + "i"
    return w


_STEP2 = [
    ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
    ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"),
    ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
    ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
    ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"),
]

_STEP3 = [
    ("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"),
    ("ical", "ic"), ("ful", ""), ("ness", ""),
]

_STEP4 = [
    "al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement",
    "ment", "ent", "ion", "ou", "ism", "ate", "iti", "ous", "ive", "ize",
]


def _step2(w: str) -> str:
    for suffix, repl in _STEP2:
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            if _measure(stem) > 0:
                return stem + repl
            return w
    return w


def _step3(w: str) -> str:
    for suffix, repl in _STEP3:
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            if _measure(stem) > 0:
                return stem + repl
            return w
    return w


def _step4(w: str) -> str:
    for suffix in _STEP4:
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            if suffix == "ion" and stem and stem[-1] in "st":
                if _measure(stem) > 1:
                    return stem
            elif _measure(stem) > 1:
                return stem
            return w
    return w


def _step5(w: str) -> str:
    if w.endswith("e"):
        stem = w[:-1]
        if _measure(stem) > 1 or (_measure(stem) == 1 and not _cvc(stem)):
            return stem
    if w.endswith("ll") and _measure(w[:-1]) > 1:
        return w[:-1]
    return w


def stem(word: str) -> str:
    """Apply Porter stemming rules to a word."""
    if len(word) <= 2:
        return word
    w = word.lower()
    w = _step1a(w)
    w = _step1b(w)
    w = _step1c(w)
    w = _step2(w)
    w = _step3(w)
    w = _step4(w)
    w = _step5(w)
    return w
