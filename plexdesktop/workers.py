import hashlib
import logging
from queue import Queue
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QModelIndex
from PyQt5.QtGui import QPixmap, QPixmapCache
from plexdesktop.sqlcache import DB_THUMB
import plexdevices
logger = logging.getLogger('plexdesktop')


class ContainerWorker(QObject):
    result_ready = pyqtSignal(plexdevices.media.MediaContainer)
    finished = pyqtSignal()

    def run(self, server, key, page=0, size=20, sort="", params={}):
        logger.debug(('BrowserList: fetching container: key={}, server={}, '
                      'page={}, size={}, sort={}, params={}').format(key, server, page,
                                                                     size, sort, params))
        p = {} if not sort else {'sort': sort}
        if params:
            p.update(params)
        try:
            data = server.container(key, page=page, size=size, params=p)
        except plexdevices.DeviceConnectionsError as e:
            logger.error('BrowserList: ' + str(e))
        else:
            logger.debug('BrowserList: url=' + server.active.url)
            container = plexdevices.media.MediaContainer(server, data)
            self.result_ready.emit(container)
        self.finished.emit()


class HubWorker(QObject):
    result_ready = pyqtSignal(plexdevices.hubs.HubsContainer)
    finished = pyqtSignal()

    def run(self, server, key, params={}):
        logger.debug(('BrowserList: fetching container: key={}'.format(key)))
        try:
            data = server.hub(key, params=params)
        except plexdevices.DeviceConnectionsError as e:
            logger.error('BrowserList: ' + str(e))
        else:
            logger.debug('BrowserList: url=' + server.active.url)
            self.result_ready.emit(data)
        self.finished.emit()


class ThumbWorker(QObject):
    result_ready = pyqtSignal(QPixmap, QModelIndex)
    finished = pyqtSignal()

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index

    def start(self):
        index = self.index
        media_object = index.data(role=Qt.UserRole)
        if media_object is None:
            self.finished.emit()
            return
        url = media_object.thumb
        if url is None or getattr(media_object, 'user_data', False):
            self.finished.emit()
            return
        key = media_object.container.server.client_identifier + url
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        img = QPixmapCache.find(key_hash)
        if img is None:
            img_data = DB_THUMB[url]
            if img_data is None:  # not in cache, fetch from server
                img_data = media_object.container.server.image(url, w=120, h=120)
                DB_THUMB[url] = img_data
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(key_hash, img)
        self.result_ready.emit(img, index)
        self.finished.emit()


class QueueThumbWorker(QObject):
    result_ready = pyqtSignal(QPixmap, QModelIndex)
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = Queue()

    def wakeup(self):
        while not self.queue.empty():
            self.process(self.queue.get())
        self.finished.emit()

    def add(self, index):
        self.queue.put(index)

    def add_many(self, indexes):
        for index in indexes:
            self.add(index)

    def process(self, index):
        media_object = index.data(role=Qt.UserRole)
        if media_object is None:
            return
        url = media_object.thumb
        if url is None or getattr(media_object, 'user_data', False):
            return
        key = media_object.container.server.client_identifier + url
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        img = QPixmapCache.find(key_hash)
        if img is None:
            img_data = DB_THUMB[url]
            if img_data is None:  # not in cache, fetch from server
                img_data = media_object.container.server.image(url, w=120, h=120)
                DB_THUMB[url] = img_data
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(key_hash, img)
        self.result_ready.emit(img, index)

