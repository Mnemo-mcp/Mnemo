"""Authentication middleware with JWT validation and token caching."""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenInfo:
    user_id: str
    org_id: str
    roles: list
    expires_at: float


class AuthMiddleware:
    """JWT-based auth with 5-minute token cache."""

    CACHE_TTL = 300  # 5 minutes

    def __init__(self, identity_service_url: str):
        self.identity_service_url = identity_service_url
        self._cache: dict[str, tuple[TokenInfo, float]] = {}

    def validate_token(self, token: str) -> Optional[TokenInfo]:
        """Validate JWT and return token info. Uses cache to avoid repeated calls."""
        cached = self._cache.get(token)
        if cached and time.time() - cached[1] < self.CACHE_TTL:
            return cached[0]

        # Call identity service to validate
        info = self._validate_with_identity_service(token)
        if info:
            self._cache[token] = (info, time.time())

        return info

    def require_role(self, token: str, role: str) -> bool:
        """Check if token has required role."""
        info = self.validate_token(token)
        return info is not None and role in info.roles

    def extract_org_id(self, token: str) -> Optional[str]:
        """Extract org_id from token — used for tenant isolation."""
        info = self.validate_token(token)
        return info.org_id if info else None

    def _validate_with_identity_service(self, token: str) -> Optional[TokenInfo]:
        """Call identity service for JWT validation."""
        # HTTP call to identity service
        pass
