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


class BrowserListItem(QListWidgetItem):

    def __init__(self, server, container, item, parent=None):
        super(BrowserListItem, self).__init__(parent)
        self.server = server
        self.data = item
        self.thumb = None
        self.parent = parent
        self.parent.iconSizeChanged.connect(self.resize)
        self.parent.resize_signal.connect(self.update_bg)
        if item.get('thumb', False):
            self.worker = ImgWorker(server, item['thumb'], self)
            self.worker.signal.connect(self.update_img)
            self.worker.finished.connect(self._finished)
            self.worker.moveToThread(self.parent.thumb_thread)
            self.parent.operate.connect(self.worker.run)
        if item.get('type', None) == 'episode':
            if 'grandparentTitle' in item and 'parentIndex' in item:
                title = '{} - s{}e{} - {}'.format(item.get('grandparentTitle', ''), item['parentIndex'], item['index'], item['title'])
            else:
                try:
                    ep = 's{:02d}e{:02d}'.format(int(container['parentIndex']), int(item['index']))
                    title = ep + ' - ' + item['title']
                except Exception:
                    title = item['title']
        else:
            title = item['title']
        self.setText(title)
        self.update_bg()

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        try:
            return self.data[key]
        except Exception:
            return default

    def _finished(self):
        del self.worker

    def update_bg(self, offset=None):
        if 'viewOffset' not in self.data or 'duration' not in self.data:
            return
        try:
            x = int(int(self.data['viewOffset'] if offset is None else offset)/int(self.data['duration'])*100)
            xpm = ["100 1 2 1", # 100x1 image
                   "a c #EEEEEE", # dark color
                   "b c #FFFFFF", # light color
                   "a"*x + "b"*(100-x)
                  ]
            self.setBackground(QBrush(QPixmap(xpm).scaled(self.parent.width(), 1)))
        except Exception as e:
            print(str(e))

    def update_offset(self, offset):
        self.data['viewOffset'] = offset
        self.update_bg(offset=offset)

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
