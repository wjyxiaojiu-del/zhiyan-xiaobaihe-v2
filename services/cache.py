"""内存缓存 - 带 TTL 的简单缓存，避免重复读取 Protocol 文件"""
import time
import threading


class TTLCache:
    def __init__(self, ttl_seconds=300):
        self._store = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._store:
                value, ts = self._store[key]
                if time.time() - ts < self._ttl:
                    return value
                del self._store[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._store[key] = (value, time.time())

    def clear(self):
        with self._lock:
            self._store.clear()


# 全局缓存实例：Protocol 文件缓存 5 分钟
protocol_cache = TTLCache(ttl_seconds=300)
# 搜索结果缓存 2 分钟
search_cache = TTLCache(ttl_seconds=120)
