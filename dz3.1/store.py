import time
import redis
import functools

from redis import ConnectionError, TimeoutError

MAX_TRIES = 3
TIMEOUT_RATE = 2
RETRY_EXCEPTIONS = (TimeoutError, ConnectionError)


def retry(exceptions=RETRY_EXCEPTIONS, tries=MAX_TRIES, rate=TIMEOUT_RATE):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(tries):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    delay = rate * (2 ** attempt)
                    time.sleep(delay)

        return wrapper

    return decorator


class StoreCacheError(Exception):
    pass


class RedisStore:
    def __init__(self, port=6379, timeout=10):
        self._cache = redis.StrictRedis(
            host='localhost',
            port=port,
            decode_responses=True,
            socket_timeout=timeout,
            socket_connect_timeout=timeout
        )

    def get(self, key):
        try:
            tmp = self._cache.get(key)
            return tmp
        except (ConnectionError, TimeoutError):
            raise StoreCacheError

    def set(self, key, value, expire=None):
        try:
            self._cache.set(key, value, expire)
        except (ConnectionError, TimeoutError):
            raise StoreCacheError
        return self


class Store:

    def __init__(self, storage):
        self._storage = storage

    def get(self, key):
        return self._storage.get(key)

    def set(self, key, value, expire=None):
        self._storage.set(key, value, expire)
        return self

    @retry()
    def cache_get(self, key):
        return self.get(key)

    @retry()
    def cache_set(self, key, value, expire=None):
        self.set(key, value, expire)
        return self
