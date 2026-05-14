"""Tests for mnemo/synonyms.py — synonym expansion."""
import pytest
from mnemo.utils.synonyms import expand_synonyms, get_synonym_group


def test_expand_returns_original_at_weight_1():
    result = expand_synonyms(["auth"])
    originals = [(t, w) for t, w in result if w == 1.0]
    assert ("auth", 1.0) in originals


def test_expand_returns_synonyms_at_weight_07():
    result = expand_synonyms(["auth"])
    synonyms = [(t, w) for t, w in result if w == 0.7]
    assert len(synonyms) > 0
    syn_terms = [t for t, _ in synonyms]
    assert "authentication" in syn_terms or "authn" in syn_terms or "login" in syn_terms


def test_unknown_term_returns_just_itself():
    result = expand_synonyms(["xyznonexistent"])
    assert result == [("xyznonexistent", 1.0)]


def test_get_synonym_group_returns_correct_group():
    group = get_synonym_group("auth")
    assert group is not None
    assert "auth" in group
    assert "authentication" in group
    assert "login" in group


def test_get_synonym_group_unknown():
    group = get_synonym_group("xyznonexistent")
    assert group is None


def test_multiple_terms_expansion():
    result = expand_synonyms(["auth", "db"])
    terms = [t for t, _ in result]
    # Should have both originals
    assert "auth" in terms
    assert "db" in terms
    # Should have synonyms from both groups
    assert "database" in terms or "datastore" in terms
    assert "authentication" in terms or "login" in terms


def test_no_duplicates_in_expansion():
    result = expand_synonyms(["auth", "authentication"])
    terms = [t for t, _ in result]
    assert len(terms) == len(set(terms))
