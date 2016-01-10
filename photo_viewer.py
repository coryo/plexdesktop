from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QScrollArea
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QPoint, QSize
from PyQt5.QtGui import QPalette, QPixmap, QPixmapCache
import photo_viewer_ui
from settings import Settings

class ImgWorker(QObject):
    signal = pyqtSignal(QPixmap)
    finished = pyqtSignal()

    def __init__(self, media_object):
        super().__init__()
        self.media_object = media_object

    def run(self):
        url = self.media_object.resolve_url()
        img = QPixmapCache.find(url)
        if img is None:
            img_data = self.media_object.parent.server.image(url)
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(url, img)
        if not img.isNull():
            self.signal.emit(img)
        self.finished.emit()


class PhotoViewer(QWidget):
    operate = pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoViewer, self).__init__(parent)
        self.ui = photo_viewer_ui.Ui_PhotoViewer()
        self.ui.setupUi(self)
        self.ui.indicator.hide()

        self.worker_thread = QThread()
        self.worker_thread.start()
        self.worker = None

        self.scale_factor = 1.0
        self.drag_position = None
        self.album = None
        self.cur_image = None

        self.image_label = QLabel()
        self.image_label.setBackgroundRole(QPalette.Base)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)

        self.scroll_area = Viewer()
        self.scroll_area.setBackgroundRole(QPalette.Dark)
        self.scroll_area.setWidget(self.image_label)

        self.ui.viewer.addWidget(self.scroll_area)

        self.ui.btn_prev.pressed.connect(self.prev)
        self.ui.btn_next.pressed.connect(self.next)
        self.show()

    def closeEvent(self, event):
        self.worker_thread.quit()

    def next(self):
        if self.album is None or self.cur_image is None:
            return
        i = self.album.children.index(self.cur_image) + 1
        if i >= len(self.album.children) - 1:
            i = 0
        try:
            self.load_image(self.album.children[i])
            self.cur_image = self.album.children[i]
        except Exception:
            pass

    def prev(self):
        if self.album is None or self.cur_image is None:
            return
        i = self.album.children.index(self.cur_image) - 1
        try:
            self.load_image(self.album.children[i])
            self.cur_image = self.album.children[i]
        except Exception:
            pass            

    def load_image(self, media_object):
        self.setWindowTitle(media_object['title'])
        self.worker = ImgWorker(media_object)
        self.worker.signal.connect(self.update_img)
        self.worker.finished.connect(self.ui.indicator.hide)
        self.worker.moveToThread(self.worker_thread)
        self.operate.connect(self.worker.run)
        self.operate.connect(self.ui.indicator.show)
        self.operate.emit()

    def load_gallery(self, media_object):
        self.album = media_object.parent.server.media_container(media_object['key'])
        self.cur_image = self.album.children[0]
        self.load_image(self.cur_image)

    def update_img(self, img):
        print('update image')
        self.image_label.setPixmap(img)
        self.scale_factor = 1.0
        # self.scroll_area.setWidgetResizable(True)
        self.image_label.adjustSize()
        # self.zoom(-50)
        self.resize(QSize(800, 600))
        self.center()

    def scale_image(self, factor):
        self.scale_factor *= factor
        print(self.scale_factor)
        self.image_label.resize(self.scale_factor * self.image_label.pixmap().size())

        hscroll = self.scroll_area.horizontalScrollBar()
        vscroll = self.scroll_area.verticalScrollBar()
        hfactor = int(factor * hscroll.value() + ((factor - 1) * hscroll.pageStep()/2))
        vfactor = int(factor * vscroll.value()+ ((factor -1) * vscroll.pageStep()/2))
        hscroll.setValue(hfactor)
        vscroll.setValue(vfactor)

    def normal_size(self):
        self.image_label.adjustSize()
        self.scale_factor = 1.0

    def center(self):
        hscroll = self.scroll_area.horizontalScrollBar()
        vscroll = self.scroll_area.verticalScrollBar()
        hscroll.setValue(hscroll.maximum()/2)
        vscroll.setValue(vscroll.maximum()/2)

    def zoom(self, perc):
        change = 1.0 + perc/100
        if 0.01 < self.scale_factor*change < 2:
            self.scale_image(change)

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = int(degrees / 15)
        if event.modifiers() & Qt.ShiftModifier:
            amount = steps * 10
            self.zoom(amount)
            event.accept()
        elif event.modifiers() & Qt.ControlModifier:
            amount = steps * 20
            hscroll = self.scroll_area.horizontalScrollBar()
            hscroll.setValue(hscroll.value() - amount)
            event.accept()
        else:
            amount = steps * 20
            vscroll = self.scroll_area.verticalScrollBar()
            vscroll.setValue(vscroll.value() - amount)
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: # window dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if not self.isFullScreen() and self.drag_position is not None: # window dragging
                self.move(event.globalPos() - self.drag_position)
                event.accept()


class Viewer(QScrollArea):

    def __init__(self, parent=None):
        super(Viewer, self).__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        event.ignore()
