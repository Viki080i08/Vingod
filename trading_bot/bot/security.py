"""Security helpers: rate limiting (anti-spam) and access control."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from ..config import settings


class RateLimiter:
    """Sliding-window per-user rate limiter to prevent spam / abuse."""

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls: Dict[int, Deque[float]] = defaultdict(deque)

    def check(self, user_id: int) -> bool:
        """Return True if the call is allowed, False if the user is throttled."""
        now = time.monotonic()
        bucket = self._calls[user_id]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.max_calls:
            return False
        bucket.append(now)
        return True

    def retry_after(self, user_id: int) -> int:
        bucket = self._calls.get(user_id)
        if not bucket:
            return 0
        now = time.monotonic()
        return max(0, int(self.window - (now - bucket[0])))


rate_limiter = RateLimiter(settings.rate_limit_max_calls, settings.rate_limit_window_seconds)


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids
