import sqlite3
import hashlib
from PyQt5.QtCore import QObject

class ImageCache(QObject):

    def __init__(self, thumb=False, parent=None):
        super(ImageCache, self).__init__(parent)
        self.conn = sqlite3.connect('cache_{}.db'.format('thumb' if thumb else 'image'))
        self.c = self.conn.cursor()
        self.create()

    def __getitem__(self, key):
        khash = hashlib.md5(key.encode('utf-8')).hexdigest()
        self.c.execute('select value from cache where key = ?',
                       (khash,))
        r = self.c.fetchone()
        if r is not None:
            try:
                self.c.execute(('update cache set accessed = strftime("%s", "now") '
                                'where key = ?'), (khash,))
            except sqlite3.OperationalError as e:
                pass
            return r[0]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        try:
            self.c.execute(('insert into cache (key, value, added) values '
                            '(?, ?, strftime("%s","now"))'),
                           (hashlib.md5(key.encode('utf-8')).hexdigest(), value))
        except sqlite3.OperationalError as e:
            pass

    def __delitem__(self, key):
        try:
            self.c.execute('DELETE FROM cache WHERE key = ?',
                           (hashlib.md5(key.encode('utf-8')).hexdigest(),))
        except sqlite3.OperationalError as e:
            pass

    def __contains__(self, key):
        self.c.execute('select rowid from cache where key = ?',
                       (hashlib.md5(key.encode('utf-8')).hexdigest(),))
        return bool(self.c.fetchone())

    def save(self):
        self.conn.commit()
        self.conn.close()

    def create(self):
        self.c.execute(('CREATE TABLE IF NOT EXISTS cache '
                        '(key text UNIQUE, value blob, added INT, '
                        'accessed INT, PRIMARY KEY(key))'))
        self.c.execute('PRAGMA busy_timeout = 0;')

    def remove(self, n):
        self.c.execute('DELETE FROM cache WHERE key IN (SELECT key from cache ORDER BY accessed ASC LIMIT ?)', (n,))
