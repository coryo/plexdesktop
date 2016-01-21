import logging
import sqlite3
import hashlib
logger = logging.getLogger('plexdesktop')


class CacheConnection(sqlite3.Connection):

    def __init__(self, *args):
        super().__init__(*args)
        self.createDB()

    def __delitem__(self, key):
        self.execute('DELETE FROM cache WHERE key = ?', (hashlib.md5(key.encode('utf-8')).hexdigest(),))
        self.commit()

    def __getitem__(self, key):
        khash = hashlib.md5(key.encode('utf-8')).hexdigest()
        data = self.execute('select value from cache where key = ?', (khash,))
        r = data.fetchone()
        return r[0] if r is not None else None

    def __setitem__(self, key, value):
        try:
            self.execute('INSERT INTO cache (key, value) VALUES (?, ?)',
                         (hashlib.md5(key.encode('utf-8')).hexdigest(), value))
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
            logger.error('SQLCache: sqlite3 error: ' + str(e))

    def createDB(self):
        self.executescript('CREATE TABLE IF NOT EXISTS cache '
                           '(key text UNIQUE, value blob, PRIMARY KEY(key)); '
                           'PRAGMA page_size = 1024;')
        self.commit()


class AccessCacheConnection(sqlite3.Connection):

    def __init__(self, *args):
        super().__init__(*args)
        self.createDB()

    def __delitem__(self, key):
        self.execute('DELETE FROM cache WHERE key = ?', (hashlib.md5(key.encode('utf-8')).hexdigest(),))
        self.commit()

    def __getitem__(self, key):
        khash = hashlib.md5(key.encode('utf-8')).hexdigest()
        data = self.execute('select value from cache where key = ?', (khash,))
        r = data.fetchone()
        if r is not None:
            self.execute('UPDATE cache SET accessed = strftime("%s", "now") WHERE key = ?', (khash,))
            return r[0]
        else:
            return None

    def __setitem__(self, key, value):
        try:
            self.execute('INSERT INTO cache (key, value, added) VALUES (?, ?, strftime("%s","now"))',
                         (hashlib.md5(key.encode('utf-8')).hexdigest(), value))
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
            logger.error('SQLCache: sqlite3 error: ' + str(e))

    def createDB(self):
        self.executescript('CREATE TABLE IF NOT EXISTS cache '
                           '(key text UNIQUE, value blob, added INT, accessed INT, PRIMARY KEY(key)); '
                           'PRAGMA page_size = 8192;')
        self.commit()

    def remove(self, n):
        self.execute('DELETE FROM cache WHERE key IN (SELECT key from cache ORDER BY accessed ASC LIMIT ?)', (n,))
        self.commit()


DB_THUMB = sqlite3.connect('cache_thumb.db', 5, 0, "DEFERRED", False, CacheConnection)
DB_IMAGE = sqlite3.connect('cache_image.db', 5, 0, "DEFERRED", False, AccessCacheConnection)
