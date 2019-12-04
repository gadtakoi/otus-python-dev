import redis
import hashlib
import datetime
import unittest
import functools

import api

from store import Store, RedisStore, StoreCacheError


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)

        return wrapper

    return decorator


class TestStorageSuite(unittest.TestCase):
    def test_set_get_key(self):
        store = Store(RedisStore())
        store.set('key1', 'val1')
        self.assertEqual(store.cache_get("key1"), 'val1')

    def test_get_not_exists_key(self):
        store = Store(RedisStore())
        self.assertEqual(store.cache_get("key2"), None)

    def test_failed_store(self):
        store = Store(RedisStore(port=99999999))
        with self.assertRaises(StoreCacheError):
            store.get("key1")
