"""Circuit breaker for external service calls."""

from __future__ import annotations
import time


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30, window=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window = window
        self._failures: list[float] = []
        self._state = 'closed'  # closed, open, half-open
        self._opened_at: float = 0

    @property
    def state(self) -> str:
        if self._state == 'open':
            if time.time() - self._opened_at >= self.recovery_timeout:
                self._state = 'half-open'
        return self._state

    def record_success(self):
        self._state = 'closed'
        self._failures.clear()

    def record_failure(self):
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window]
        self._failures.append(now)
        if len(self._failures) >= self.failure_threshold:
            self._state = 'open'
            self._opened_at = now

    def allow_request(self) -> bool:
        state = self.state
        if state == 'closed':
            return True
        if state == 'half-open':
            return True
        return False
