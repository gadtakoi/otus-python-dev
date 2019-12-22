import redis
import hashlib
import datetime
import unittest
import functools

import api

from store import Store, RedisStore, StoreCacheError


class TestStorageSuite(unittest.TestCase):
    def test_set_get_key(self):
        store = Store(RedisStore(), 3, 2, (TimeoutError, ConnectionError))
        store.set('key1', 'val1')
        self.assertEqual(store.cache_get("key1"), 'val1')

    def test_get_not_exists_key(self):
        store = Store(RedisStore(), 3, 2, (TimeoutError, ConnectionError))
        self.assertEqual(store.cache_get("key2"), None)

    def test_failed_store(self):
        store = Store(RedisStore(port=99999999), 3, 2, (TimeoutError, ConnectionError))
        with self.assertRaises(StoreCacheError):
            store.get("key1")
