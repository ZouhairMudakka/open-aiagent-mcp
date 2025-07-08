import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.history = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        hist = self.history[key]
        # drop outdated
        hist[:] = [t for t in hist if now - t < self.period]
        if len(hist) >= self.calls:
            return False
        hist.append(now)
        return True 