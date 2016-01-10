import hashlib
from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap, QIcon, QBrush, QPixmapCache, QColor
from PyQt5.QtCore import pyqtSignal, QObject, QSize, Qt, QObject, QThread, QSettings

class BrowserList(QListWidget):
    resize_signal = pyqtSignal()
    operate = pyqtSignal()
    iconSizeChanged = pyqtSignal(QSize) # object has no attribute 'iconSizeChanged' on linux ?

    def __init__(self, parent=None):
        super().__init__()
        self.setIconSize(QSize(32, 32))
        self.current_container = None
        self.server = None
        self.thumb_thread = QThread()
        self.thumb_thread.start()

    def icon_size(self, x):
        self.setIconSize(QSize(x, x))

    def setIconSize(self, size):
        # reimplemented because linux was being weird
        super().setIconSize(size)
        self.iconSizeChanged.emit(size)

    def refresh_icons(self):
        self.operate.emit()

    def closeEvent(self, event):
        self.thumb_thread.quit()

    def resizeEvent(self, event):
        self.resize_signal.emit()

    def add_container(self, container):
        self.current_container = container
        self.server = container.server
        for media_object in container.children:
            self.addItem(BrowserListItem(media_object, parent=self))


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
            self.worker = ImgWorker(parent.server, self.media['thumb'], self)
            self.worker.signal.connect(self.update_img)
            self.worker.finished.connect(self._finished)
            self.worker.moveToThread(self.parent.thumb_thread)
            self.parent.operate.connect(self.worker.run)
        if self.media.get('type', None) == 'episode':
            if 'grandparentTitle' in self.media and 'parentIndex' in self.media:
                title = '{} - s{}e{} - {}'.format(self.media.get('grandparentTitle', ''), self.media['parentIndex'], self.media['index'], self.media['title'])
            else:
                try:
                    ep = 's{:02d}e{:02d}'.format(int(container['parentIndex']), int(self.media['index']))
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
        if 'viewOffset' not in self.media or 'duration' not in self.media:
            return
        try:
            x = int(int(self.media['viewOffset'] if offset is None else offset)/int(self.media['duration'])*100)
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

    def update_img(self, pixmap=None):
        if not pixmap.isNull():
            self.thumb = pixmap
            self.resize(self.parent.iconSize())

    def resize(self, size):
        if self.thumb is not None:
            self.setIcon(QIcon(self.thumb.scaled(size, Qt.KeepAspectRatio)))


class ImgWorker(QObject):
    signal = pyqtSignal(QPixmap)
    finished = pyqtSignal()

    def __init__(self, server, url, parent):
        super().__init__()
        self.server = server
        self.url = url
        self.parent = parent

    def run(self):
        img = QPixmapCache.find(self.url)
        if img is None:
            img_data = self.server.image(self.url, w=100, h=100)
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(hashlib.md5(str(self.server.client_identifier+self.url).encode('utf-8')).hexdigest(), img)

        if not img.isNull():
            self.signal.emit(img)

        self.finished.emit()
