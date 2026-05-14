"""Tests for mnemo/circuit_breaker.py."""
import time
import pytest
from mnemo.utils.circuit_breaker import CircuitBreaker


def test_starts_closed():
    cb = CircuitBreaker()
    assert cb.state == "closed"


def test_allows_requests_when_closed():
    cb = CircuitBreaker()
    assert cb.allow_request() is True


def test_opens_after_n_failures():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "closed"
    cb.record_failure()
    assert cb.state == "open"


def test_blocks_requests_when_open():
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow_request() is False


def test_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "open"
    time.sleep(0.15)
    assert cb.state == "half-open"


def test_allows_request_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    assert cb.allow_request() is True


def test_closes_on_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    assert cb.state == "half-open"
    cb.record_success()
    assert cb.state == "closed"
    assert cb.allow_request() is True
