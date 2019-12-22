import time
import redis
import functools

from redis import ConnectionError, TimeoutError


# MAX_TRIES = 3
# TIMEOUT_RATE = 2
# RETRY_EXCEPTIONS = (TimeoutError, ConnectionError)


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    raise Exception("{}. CASE: {}".format(str(e), c))

        return wrapper

    return decorator


def retry(exceptions, tries, rate):
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
            return self._cache.get(key)
        except (ConnectionError, TimeoutError):
            raise StoreCacheError

    def set(self, key, value, expire=None):
        try:
            return self._cache.set(key, value, expire)
        except (ConnectionError, TimeoutError):
            raise StoreCacheError


class Store:

    def __init__(self, storage, exceptions, tries, rate):
        self._storage = storage
        self.exceptions = exceptions
        self.tries = tries
        self.rate = rate

    def get(self, key):
        return self._storage.get(key)

    def set(self, key, value, expire=None):
        self._storage.set(key, value, expire)
        return self

    def cache_get(self, key):
        @retry(self.exceptions, self.tries, self.rate)
        def _cache_get():
            return self.get(key)

        return _cache_get()

    def cache_set(self, key, value, expire=None):
        @retry(self.exceptions, self.tries, self.rate)
        def _cache_set():
            self.set(key, value, expire)
            return self

        return _cache_set()
