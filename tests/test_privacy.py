"""Tests for mnemo/privacy.py — secret stripping."""
import pytest
from mnemo.utils.privacy import strip_secrets


def test_aws_key_detected():
    text = "key=AKIAIOSFODNN7EXAMPLE"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "[REDACTED]" in cleaned
    assert "AKIA" not in cleaned


def test_github_pat_detected():
    text = "token=ghp_ABCDEFghijklmnopqrst1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "ghp_" not in cleaned


def test_github_oauth_detected():
    text = "gho_abcdefghij1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "gho_" not in cleaned


def test_github_server_detected():
    text = "ghs_abcdefghij1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 1


def test_github_refresh_detected():
    text = "ghr_abcdefghij1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 1


def test_jwt_detected():
    text = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "eyJ" not in cleaned


def test_bearer_token_detected():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef"
    cleaned, count = strip_secrets(text)
    assert count >= 1
    assert "Bearer" not in cleaned or "[REDACTED]" in cleaned


def test_slack_bot_token_detected():
    text = "SLACK_TOKEN=xoxb-123456789-abcdefgh"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "xoxb-" not in cleaned


def test_slack_user_token_detected():
    text = "xoxp-123456789-abcdefgh"
    cleaned, count = strip_secrets(text)
    assert count == 1


def test_google_api_key_detected():
    text = "AIzaSyA1234567890abcdefghijklmnopqrstuvw"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "AIza" not in cleaned


def test_gitlab_pat_detected():
    text = "glpat-abcdefghijklmnopqrstu12345"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "glpat-" not in cleaned


def test_digitalocean_token_detected():
    text = "dop_v1_" + "a" * 64
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "dop_v1_" not in cleaned


def test_npm_token_detected():
    text = "npm_abcdefghij1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "npm_" not in cleaned


def test_private_tags_detected():
    text = "data <private>secret stuff</private> more"
    cleaned, count = strip_secrets(text)
    assert count == 1
    assert "secret stuff" not in cleaned
    assert "data" in cleaned


def test_no_secrets_unchanged():
    text = "This is normal text with no secrets at all."
    cleaned, count = strip_secrets(text)
    assert count == 0
    assert cleaned == text


def test_multiple_secrets():
    text = "AKIAIOSFODNN7EXAMPLE and ghp_ABCDEFghijklmnopqrst1234567890"
    cleaned, count = strip_secrets(text)
    assert count == 2
    assert cleaned.count("[REDACTED]") == 2


def test_partial_match_no_false_positive():
    # "AKIA" alone without 16 chars shouldn't match
    text = "AKIA is a prefix but not a full key"
    cleaned, count = strip_secrets(text)
    assert count == 0
    assert cleaned == text


def test_empty_string():
    cleaned, count = strip_secrets("")
    assert count == 0
    assert cleaned == ""
