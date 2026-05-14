"""Tests for mnemo/stemmer.py — Porter stemmer."""
import pytest
from mnemo.utils.stemmer import stem


@pytest.mark.parametrize("word,expected_suffix_removed", [
    ("running", "ing"),
    ("configuration", "tion"),
    ("happiness", "ness"),
    ("deployment", "ment"),
    ("configurable", "able"),
    ("hopeful", "ful"),
    ("carelessness", "ness"),
    ("optimize", "ize"),
    ("authenticated", "ated"),
])
def test_common_suffixes_removed(word, expected_suffix_removed):
    result = stem(word)
    assert not result.endswith(expected_suffix_removed)
    assert len(result) < len(word)


def test_empty_string():
    assert stem("") == ""


def test_single_char():
    assert stem("a") == "a"


def test_two_chars():
    assert stem("go") == "go"


def test_already_stemmed():
    result = stem("run")
    assert result == "run"


def test_authenticating():
    result = stem("authenticating")
    # Porter stemmer: authenticating -> authenticat (step1b) -> ... -> authent
    assert result == "authent"


def test_configurations():
    result = stem("configurations")
    # configurations -> configuration (step1a) -> configur (step2+step4)
    assert result == "configur"


def test_implementing():
    result = stem("implementing")
    # implementing -> implement (step1b)
    assert result == "implement"


def test_stemmer_lowercase():
    # Stemmer lowercases input
    result = stem("Running")
    assert result == stem("running")
