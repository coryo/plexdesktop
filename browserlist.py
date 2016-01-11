import hashlib
from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap, QIcon, QBrush, QPixmapCache, QColor
from PyQt5.QtCore import pyqtSignal, QObject, QSize, Qt, QObject, QThread, QSettings
from image_cache import ImageCache

class BrowserList(QListWidget):
    resize_signal = pyqtSignal()
    iconSizeChanged = pyqtSignal(QSize) # object has no attribute 'iconSizeChanged' on linux ?

    def __init__(self, parent=None):
        super().__init__()
        self.setIconSize(QSize(32, 32))
        self.current_container = None
        self.server = None
        self.thumb_controller = Controller(thumb=True, parent=self)

    def icon_size(self, x):
        self.setIconSize(QSize(x, x))

    def setIconSize(self, size):
        # reimplemented because linux was being weird
        super().setIconSize(size)
        self.iconSizeChanged.emit(size)

    def closeEvent(self, event):
        del self.thumb_controller

    def resizeEvent(self, event):
        self.resize_signal.emit()

    def add_container(self, container):
        self.thumb_controller.start()
        self.current_container = container
        self.server = container.server
        for media_object in container.children:
            self.addItem(BrowserListItem(media_object, parent=self))
        self.thumb_controller.save()


class BrowserListItem(QListWidgetItem):

    def __init__(self, media_object, parent=None):
        super(BrowserListItem, self).__init__(parent)
        self.media = media_object

        self.thumb = None
        self.parent = parent
        self.worker = None
        self.parent.iconSizeChanged.connect(self.resize)
        self.parent.resize_signal.connect(self.update_bg)

        if self.media.get('thumb', False):
            self.parent.thumb_controller.get_item(self)
        if self.media.get('type', None) == 'episode':
            if 'grandparentTitle' in self.media and 'parentIndex' in self.media:
                title = '{} - s{:02d}e{:02d} - {}'.format(self.media['grandparentTitle'],
                                                          int(self.media['parentIndex']),
                                                          int(self.media['index']),
                                                          self.media['title'])
            else:
                try:
                    ep = 's{:02d}e{:02d}'.format(int(self.media.parent['parentIndex']),
                                                 int(self.media['index']))
                    title = ep + ' - ' + self.media['title']
                except Exception:
                    title = self.media['title']
        else:
            title = self.media['title']
        self.setText(title)
        self.update_bg()

    def _finished(self):
        try:
            del self.worker
        except Exception:
            pass

    def update_bg(self, offset=None):
        if (('viewOffset' not in self.media) or
                ('duration' not in self.media) or
                (self.media['viewOffset'] == 0)):
            return
        try:
            vo = int(self.media['viewOffset']) if offset is None else offset
            x = int(vo / int(self.media['duration']) * 100)
            xpm = ["100 1 2 1",   # 100x1 image
                   "a c #EEEEEE", # dark color
                   "b c #FFFFFF", # light color
                   "a"*x + "b"*(100-x)
                  ]
            self.setBackground(QBrush(QPixmap(xpm).scaled(self.parent.width(), 1)))
        except Exception as e:
            print(str(e))

    def update_offset(self, offset):
        self.media['viewOffset'] = offset
        self.update_bg(offset)

    def clear_bg(self):
        self.setBackground(QBrush(QColor(255, 255, 255)))

    def update_img(self, pixmap):
        if not pixmap.isNull():
            self.thumb = pixmap
            self.resize(self.parent.iconSize())

    def resize(self, size):
        if self.thumb is not None:
            self.setIcon(QIcon(self.thumb.scaled(size, Qt.KeepAspectRatio)))


class Controller(QObject):
    operate = pyqtSignal(BrowserListItem)
    start_cache = pyqtSignal()
    close_cache = pyqtSignal()

    def __init__(self, thumb=False, parent=None):
        super().__init__()
        self.worker_thread = QThread()
        self.worker = ImgWorker(thumb)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.start_cache.connect(self.worker.create_cache)
        self.close_cache.connect(self.worker.save_cache)
        self.operate.connect(self.worker.do_work)
        self.worker.result_ready.connect(self.handle_results)
        self.worker_thread.start()

    def start(self):
        self.start_cache.emit()

    def save(self):
        self.close_cache.emit()

    def __del__(self):
        self.worker_thread.quit()
        self.worker_thread.wait()

    def get_item(self, item):
        self.operate.emit(item)

    def handle_results(self, item, data):
        item.update_img(data)


class ImgWorker(QObject):
    result_ready = pyqtSignal(BrowserListItem, QPixmap)

    def __init__(self, thumb=False, parent=None):
        super().__init__()
        self.thumb = thumb

    def create_cache(self):
        self.cache = ImageCache(thumb=self.thumb)

    def save_cache(self):
        self.cache.save()

    def do_work(self, item):
        url = item.media['thumb'] if self.thumb else item.media.resolve_url()
        key = hashlib.md5((item.parent.server.client_identifier+url).encode('utf-8')).hexdigest()
        img = QPixmapCache.find(key)
        if img is None:
            if url in self.cache:
                img_data = self.cache[url]
            else:
                img_data = item.parent.server.image(url, w=100, h=100)
                self.cache[url] = img_data

            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(key, img)

        self.result_ready.emit(item, img)
