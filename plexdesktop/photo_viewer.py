import logging
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QSize, QTimer
from plexdesktop.ui.photo_viewer_ui import Ui_PhotoViewer
from plexdesktop.settings import Settings
from plexdesktop.sqlcache import DB_IMAGE
from plexdesktop.style import STYLE
import plexdevices
logger = logging.getLogger('plexdesktop')


class ImgWorker(QObject):
    signal = pyqtSignal(bytes)
    finished = pyqtSignal()

    def run(self, photo_object):
        url = photo_object.media[0].parts[0].resolve_key()
        logger.info('PhotoViewer: ' + url)
        img_data = DB_IMAGE[url]
        if img_data is None:
            img_data = photo_object.container.server.image(url)
            DB_IMAGE[url] = img_data
        DB_IMAGE.commit()
        self.signal.emit(img_data)
        self.finished.emit()


class PhotoViewer(QMainWindow):
    operate = pyqtSignal(plexdevices.media.BaseObject)
    closed = pyqtSignal()
    prev_button = pyqtSignal()
    next_button = pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)
        self.ui = Ui_PhotoViewer()
        self.ui.setupUi(self)
        self.ui.image_label.resize(self.sizeHint())

        self.worker_thread = QThread()
        self.worker_thread.start()
        self.worker = ImgWorker()
        self.worker.signal.connect(self.update_img)
        self.worker.moveToThread(self.worker_thread)
        self.operate.connect(self.worker.run)

        self.drag_position = None
        self.cur_img_data = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.ui.image_label.refresh)

        self.ui.actionBack.triggered.connect(self.prev)
        self.ui.actionForward.triggered.connect(self.next)
        self.ui.actionRotateLeft.triggered.connect(self.ui.image_label.rotate_ccw)
        self.ui.actionRotateRight.triggered.connect(self.ui.image_label.rotate_cw)
        self.ui.actionRefresh.triggered.connect(self.ui.image_label.rotate_default)

        STYLE.widget.register(self.ui.actionBack, 'glyphicons-chevron-left')
        STYLE.widget.register(self.ui.actionForward, 'glyphicons-chevron-right')
        STYLE.widget.register(self.ui.actionRotateLeft, 'glyphicons-rotate-left')
        STYLE.widget.register(self.ui.actionRotateRight, 'glyphicons-rotate-right')
        STYLE.widget.register(self.ui.actionRefresh, 'glyphicons-refresh')
        STYLE.refresh()

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

    def load_image(self, photo_object):
        self.setWindowTitle(photo_object.title)
        self.operate.emit(photo_object)

    def update_img(self, img_data):
        self.ui.image_label.new_image(img_data)
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
            else:
                self.showNormal()

    def resizeEvent(self, event):
        self.timer.start()
