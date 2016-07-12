import logging

import plexdevices

import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.QtGui

import plexdesktop.ui.photo_viewer_ui
import plexdesktop.style
import plexdesktop.workers
import plexdesktop.components

logger = logging.getLogger('plexdesktop')
Qt = PyQt5.QtCore.Qt


class PhotoViewer(plexdesktop.components.ComponentWindow):
    operate = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    # closed = PyQt5.QtCore.pyqtSignal()
    prev_button = PyQt5.QtCore.pyqtSignal()
    next_button = PyQt5.QtCore.pyqtSignal()

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.photo_viewer_ui.Ui_PhotoViewer()
        self.ui.setupUi(self)

        self.scene = PyQt5.QtWidgets.QGraphicsScene(self)
        self.ui.view.setScene(self.scene)
        self.resize(self.sizeHint())

        self.worker_thread = PyQt5.QtCore.QThread(self)
        self.worker_thread.start()
        self.worker = plexdesktop.workers.ImageWorker()
        self.worker.signal.connect(self.update_img)
        self.worker.moveToThread(self.worker_thread)
        self.operate.connect(self.worker.run)
        self.operate.connect(self.show_indicator)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.worker.deleteLater)

        self.rotation = 0
        self.drag_position = None

        self.ui.actionBack.triggered.connect(self.prev)
        self.ui.actionForward.triggered.connect(self.next)
        self.ui.actionRotateLeft.triggered.connect(self.rotate_ccw)
        self.ui.actionRotateRight.triggered.connect(self.rotate_cw)
        self.ui.actionRefresh.triggered.connect(self.rotate_default)

        style = plexdesktop.style.Style.Instance()
        style.widget.register(self.ui.actionBack, 'glyphicons-chevron-left')
        style.widget.register(self.ui.actionForward, 'glyphicons-chevron-right')
        style.widget.register(self.ui.actionRotateLeft, 'glyphicons-rotate-left')
        style.widget.register(self.ui.actionRotateRight, 'glyphicons-rotate-right')
        style.widget.register(self.ui.actionRefresh, 'glyphicons-refresh')
        style.refresh()

    def sizeHint(self):
        return PyQt5.QtCore.QSize(960, 720)

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait()
        self._shutdown()
        super().closeEvent(event)

    def show_indicator(self):
        self.scene.addWidget(PyQt5.QtWidgets.QProgressBar())

    def rotate_cw(self):
        self.ui.view.rotate(90)
        self.rotation += 90

    def rotate_ccw(self):
        self.ui.view.rotate(-90)
        self.rotation -= 90

    def rotate_default(self):
        self.ui.view.rotate(-self.rotation)
        self.rotation = 0

    def next(self):
        self.next_button.emit()

    def prev(self):
        self.prev_button.emit()

    @PyQt5.QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def load_image(self, photo_object):
        self.setWindowTitle(photo_object.title)
        self.operate.emit(photo_object)

    def update_img(self, img_data):
        reader = PyQt5.QtGui.QImageReader()
        buf = PyQt5.QtCore.QBuffer()
        buf.setData(img_data)
        reader.setDevice(buf)
        new_image = reader.read()
        self.scene.clear()  # clear scene
        item = self.scene.addPixmap(PyQt5.QtGui.QPixmap.fromImage(new_image))  # add new image
        item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(item.boundingRect())  # reset the scene rect
        self.ui.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)  # fit to size

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

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.isFullScreen():
                self.showFullScreen()
            else:
                self.showNormal()

    def resizeEvent(self, event):
        # fit contents only when scrollbars go away.
        if (not self.ui.view.verticalScrollBar().isVisible() and
                not self.ui.view.horizontalScrollBar().isVisible()):
            self.ui.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            degrees = event.angleDelta().y() / 8
            steps = int(degrees / 15)
            amount = 1 + (0.1 * steps)
            self.ui.view.scale(amount, amount)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.ui.view.setInteractive(True)
            self.ui.view.setDragMode(PyQt5.QtWidgets.QGraphicsView.ScrollHandDrag)
        elif event.key() == Qt.Key_Control:
            self.ui.view.setInteractive(True)
        else:
            super().keyPressEvent(event)
