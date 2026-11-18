"""Per-client rate limiting across the whole API, kept in memory."""

import hashlib
import math
import time
from collections import OrderedDict

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

_MAX_KEY_LENGTH = 64
_MAX_TRACKED_KEYS = 10_000


class RateLimiter:
    """One moving-window budget per client key, shared by every route."""

    def __init__(self, limit: str, enabled: bool) -> None:
        """Parse `limit` (e.g. "2/3seconds", see the `limits` string notation) and start with empty counters."""
        self.limit = parse(limit)
        self.enabled = enabled
        self.storage = MemoryStorage()
        self.strategy = MovingWindowRateLimiter(self.storage)
        self._keys: OrderedDict[str, None] = OrderedDict()

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Bound per-key memory: hash any key longer than a validated client address."""
        if len(key) <= _MAX_KEY_LENGTH:
            return key
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _track(self, key: str) -> None:
        """Bound aggregate key count by evicting the least recently used budget when full."""
        if key in self._keys:
            self._keys.move_to_end(key)
            return
        if len(self._keys) >= _MAX_TRACKED_KEYS:
            oldest, _ = self._keys.popitem(last=False)
            self.storage.clear(self.limit.key_for(oldest))
        self._keys[key] = None

    def hit(self, key: str) -> bool:
        """Count a request from `key`; False when it is over the limit."""
        normalized = self._normalize_key(key)
        self._track(normalized)
        return self.strategy.hit(self.limit, normalized)

    def retry_after(self, key: str) -> int:
        """Whole seconds until `key` can make another request."""
        reset_time = self.strategy.get_window_stats(self.limit, self._normalize_key(key)).reset_time
        return max(1, math.ceil(reset_time - time.time()))

    def reset(self) -> None:
        """Forget all counters."""
        self.storage.reset()
        self._keys.clear()
