# plexdesktop
# Copyright (c) 2016 Cory Parsons <parsons.cory@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
        try:
            data = self.execute('select value from cache where key = ?', (khash,))
        except sqlite3.InterfaceError:
            return None
        r = data.fetchone()
        try:
            return r[0]
        except (IndexError, TypeError):
            return None

    def __len__(self):
        n = self.execute('SELECT Count(*) from cache')
        try:
            return n.fetchone()[0]
        except IndexError:
            return 0

    def __setitem__(self, key, value):
        try:
            self.execute('INSERT INTO cache (key, value) VALUES (?, ?)',
                         (hashlib.md5(key.encode('utf-8')).hexdigest(), value))
        except (sqlite3.IntegrityError, sqlite3.OperationalError, sqlite3.InterfaceError) as e:
            logger.error('SQLCache: sqlite3 error: ' + str(e))

    def createDB(self):
        self.executescript('CREATE TABLE IF NOT EXISTS cache '
                           '(key text UNIQUE, value blob, PRIMARY KEY(key)); '
                           'PRAGMA page_size = 1024;')
        self.commit()

    def remove(self, n=None):
        if n is None:
            n = int(len(self) * 0.10)
        logger.info('cache: removing {} items.'.format(n))
        self.execute('DELETE FROM cache WHERE key IN (SELECT key from cache ORDER BY random() LIMIT ?)', (n,))
        self.commit()
        self.execute('VACUUM')


class AccessCacheConnection(sqlite3.Connection):

    def __init__(self, *args):
        super().__init__(*args)
        self.createDB()

    def __len__(self):
        n = self.execute('SELECT Count(*) from cache')
        try:
            return int(n.fetchone()[0])
        except IndexError:
            return 0

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
                           'PRAGMA page_size = 8192; PRAGMA auto_vacuum=FULL;')
        self.commit()

    def remove(self, n=None):
        if n is None:
            n = int(len(self) * 0.10)
        logger.info('cache: removing {} items.'.format(n))
        self.execute('DELETE FROM cache WHERE key IN (SELECT key from cache ORDER BY accessed ASC LIMIT ?)', (n,))
        self.commit()


DB_THUMB = sqlite3.connect('cache_thumb.db', 5, 0, "DEFERRED", False, CacheConnection)
DB_IMAGE = sqlite3.connect('cache_image.db', 5, 0, "DEFERRED", False, AccessCacheConnection)
