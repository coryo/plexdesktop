import sqlite3
import hashlib
from PyQt5.QtCore import QObject, pyqtSignal


class SqlCache(QObject):

    def __init__(self, name, access=True, parent=None):
        super(SqlCache, self).__init__(parent)
        self.name = name
        self.page_size = 1024 if name == 'thumb' else 8192
        self.conn = None
        self.access = access

    def open(self):
        self.conn = sqlite3.connect('cache_{}.db'.format(self.name))
        self.create()

    def __getitem__(self, key):
        c = self.conn.cursor()
        khash = hashlib.md5(key.encode('utf-8')).hexdigest()
        c.execute('select value from cache where key = ?', (khash,))
        r = c.fetchone()
        if r is not None:
            if self.access:
                c.execute('UPDATE cache SET accessed = strftime("%s", "now") WHERE key = ?', (khash,))
            return r[0]
        else:
            return None

    def __setitem__(self, key, value):
        c = self.conn.cursor()
        try:
            if self.access:
                q = 'INSERT INTO cache (key, value, added) VALUES (?, ?, strftime("%s","now"))'
            else:
                q = 'INSERT INTO cache (key, value) VALUES (?, ?)'
            c.execute(q, (hashlib.md5(key.encode('utf-8')).hexdigest(), value))
        except (sqlite3.IntegrityError, sqlite3.OperationalError):
            pass

    def __delitem__(self, key):
        c = self.conn.cursor()
        c.execute('DELETE FROM cache WHERE key = ?', (hashlib.md5(key.encode('utf-8')).hexdigest(),))

    def __contains__(self, key):
        c = self.conn.cursor()
        c.execute('select rowid from cache where key = ?',
                  (hashlib.md5(key.encode('utf-8')).hexdigest(),))
        return bool(c.fetchone())

    def save(self):
        self.conn.commit()

    def create(self):
        c = self.conn.cursor()
        c.execute('PRAGMA busy_timeout = 0;')
        c.execute("PRAGMA page_size = {};".format(self.page_size))
        if self.access:
            q = ('CREATE TABLE IF NOT EXISTS cache '
                 '(key text UNIQUE, value blob, added INT, accessed INT, PRIMARY KEY(key))')
        else:
            q = ('CREATE TABLE IF NOT EXISTS cache '
                 '(key text UNIQUE, value blob, PRIMARY KEY(key))')
        c.execute(q)

    def remove(self, n):
        c = self.conn.cursor()
        c.execute('DELETE FROM cache WHERE key IN (SELECT key from cache ORDER BY accessed ASC LIMIT ?)', (n,))
