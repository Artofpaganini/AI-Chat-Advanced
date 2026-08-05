"""Скользящее окно ограничения частоты запросов, ключ - IP клиента.

Один RateLimiter на процесс, общий для всех потоков ThreadingHTTPServer. Каждый IP хранит
метки времени своих запросов за последние WINDOW_SECONDS, старые метки вычищаются при
каждой проверке. Блокировка одним общим Lock: нагрузка локального шлюза не требует
шардирования по IP.
"""

import threading
import time
from collections import deque
from typing import Deque, Dict, Tuple

WINDOW_SECONDS = 60.0
MIN_RETRY_AFTER_SECONDS = 1


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self._lock = threading.Lock()
        self._hits: Dict[str, Deque[float]] = {}

    def check(self, client_ip: str) -> Tuple[bool, int, int]:
        now = time.time()
        with self._lock:
            bucket = self._hits.setdefault(client_ip, deque())
            self._evict(bucket, now)
            if len(bucket) >= self.limit_per_minute:
                return False, 0, self._retry_after(bucket, now)
            bucket.append(now)
            return True, self.limit_per_minute - len(bucket), 0

    def _evict(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - WINDOW_SECONDS
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _retry_after(self, bucket: Deque[float], now: float) -> int:
        if not bucket:
            return MIN_RETRY_AFTER_SECONDS
        remaining = WINDOW_SECONDS - (now - bucket[0])
        return max(MIN_RETRY_AFTER_SECONDS, int(remaining) + 1)
