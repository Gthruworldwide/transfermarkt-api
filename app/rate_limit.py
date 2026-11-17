"""Per-client rate limiting across the whole API, kept in memory."""

import hashlib
import math
import time

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

_MAX_KEY_LENGTH = 64


class RateLimiter:
    """One moving-window budget per client key, shared by every route."""

    def __init__(self, limit: str, enabled: bool) -> None:
        """Parse `limit` (e.g. "2/3seconds", see the `limits` string notation) and start with empty counters."""
        self.limit = parse(limit)
        self.enabled = enabled
        self.storage = MemoryStorage()
        self.strategy = MovingWindowRateLimiter(self.storage)

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Bound per-key memory: hash any key longer than a validated client address."""
        if len(key) <= _MAX_KEY_LENGTH:
            return key
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def hit(self, key: str) -> bool:
        """Count a request from `key`; False when it is over the limit."""
        return self.strategy.hit(self.limit, self._normalize_key(key))

    def retry_after(self, key: str) -> int:
        """Whole seconds until `key` can make another request."""
        reset_time = self.strategy.get_window_stats(self.limit, self._normalize_key(key)).reset_time
        return max(1, math.ceil(reset_time - time.time()))

    def reset(self) -> None:
        """Forget all counters."""
        self.storage.reset()
