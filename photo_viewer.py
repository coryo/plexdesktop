from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QScrollArea
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QPoint, QSize, QBuffer, QIODevice, QTimer
from PyQt5.QtGui import QPalette, QPixmap, QGuiApplication, QImageReader
from photo_viewer_ui import Ui_PhotoViewer
from settings import Settings
from sqlcache import SqlCache


class ImgWorker(QObject):
    signal = pyqtSignal(bytes)
    finished = pyqtSignal()

    def __init__(self, media_object):
        super(ImgWorker, self).__init__()
        self.media_object = media_object

    def run(self):
        url = self.media_object.resolve_url()
        print(url)
        cache = SqlCache('image', access=True)
        cache.open()
        if url in cache:
            img_data = cache[url]
        else:
            img_data = self.media_object.parent.server.image(url)
            cache[url] = img_data
        cache.save()

        self.signal.emit(img_data)
        self.finished.emit()


class PhotoViewer(QWidget):
    operate = pyqtSignal()
    closed = pyqtSignal()
    prev_button = pyqtSignal()
    next_button = pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)
        self.ui = Ui_PhotoViewer()
        self.ui.setupUi(self)
        self.ui.indicator.hide()
        self.ui.image_label.resize(self.sizeHint())

        self.worker_thread = QThread()
        self.worker_thread.start()
        self.worker = None

        self.drag_position = None
        self.cur_img_data = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.ui.image_label.refresh)

        self.ui.btn_prev.pressed.connect(self.prev)
        self.ui.btn_next.pressed.connect(self.next)
        self.ui.btn_refresh.pressed.connect(self.ui.image_label.refresh)

    def sizeHint(self):
        return QSize(1280, 720)

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.closed.emit()

    def next(self):
        self.next_button.emit()

    def prev(self):
        self.prev_button.emit()

    def load_image(self, media_object):
        self.setWindowTitle(media_object['title'])
        self.worker = ImgWorker(media_object)
        self.worker.signal.connect(self.update_img)
        self.worker.finished.connect(self.ui.indicator.hide)
        self.worker.moveToThread(self.worker_thread)
        self.operate.connect(self.worker.run)
        self.operate.connect(self.ui.indicator.show)
        self.operate.emit()

    def update_img(self, img_data):
        self.ui.image_label.set_pixmap_from_data(img_data)
        self.ui.image_label.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  # window dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.BackButton:
            self.prev()
        elif event.button() == Qt.ForwardButton:
            self.next()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if not self.isFullScreen() and self.drag_position is not None:  # window dragging
                self.move(event.globalPos() - self.drag_position)
                event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.isFullScreen():
                self.showFullScreen()
                self.ui.control_bar.hide()
            else:
                self.showNormal()
                self.ui.control_bar.show()

    def resizeEvent(self, event):
        self.timer.start()
