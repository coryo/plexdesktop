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

import plexdevices

from PyQt5 import QtCore, QtWidgets, QtGui

import plexdesktop.ui.photo_viewer_ui
import plexdesktop.style
import plexdesktop.workers
import plexdesktop.components

logger = logging.getLogger('plexdesktop')
Qt = QtCore.Qt


class PhotoViewer(plexdesktop.components.ComponentWindow):
    operate = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    prev_button = QtCore.pyqtSignal()
    next_button = QtCore.pyqtSignal()

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.photo_viewer_ui.Ui_PhotoViewer()
        self.ui.setupUi(self)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.ui.view.setScene(self.scene)
        self.resize(self.sizeHint())

        self.pixmap = QtGui.QPixmap()
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self.draw_timer = QtCore.QTimer()
        self.draw_timer.setSingleShot(True)
        self.draw_timer.setInterval(200)
        self.draw_timer.timeout.connect(self.scale_pixmap)

        self.worker_thread = QtCore.QThread(self)
        self.worker_thread.start()
        self.worker = plexdesktop.workers.ImageWorker()
        self.worker.signal.connect(self.update_img)
        self.worker.moveToThread(self.worker_thread)
        self.operate.connect(self.worker.run)
        self.operate.connect(self.show_indicator)
        self.worker.signal.connect(self.hide_indicator)
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
        return QtCore.QSize(960, 720)

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait()
        self._shutdown()
        super().closeEvent(event)

    def show_indicator(self):
        self.indicator = self.scene.addText(
            'Loading', QtGui.QFont('Helvetica', 16, 1))
        self.indicator.setDefaultTextColor(QtGui.QColor('red'))
        viwport_center = self.ui.view.mapToScene(
            self.ui.view.viewport().geometry().center())
        self.indicator.setPos(viwport_center - self.indicator.boundingRect().center())

    def hide_indicator(self):
        self.scene.removeItem(self.indicator)

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

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def load_image(self, photo_object):
        self.setWindowTitle(photo_object.title)
        self.operate.emit(photo_object)

    @QtCore.pyqtSlot(QtCore.QByteArray)
    def update_img(self, img_data):
        reader = QtGui.QImageReader()
        buf = QtCore.QBuffer()
        buf.setData(img_data)
        reader.setDevice(buf)
        new_image = reader.read()
        # scale to window size
        prev_size = (self.size() if self.pixmap_item.pixmap().isNull() else
                     self.ui.view.viewport().geometry().size())
        # store the full pixmap
        self.pixmap = QtGui.QPixmap.fromImage(new_image)
        # do the scaling
        self.scale_pixmap(prev_size)
        if not self.pixmap_item.scene():
            self.scene.addItem(self.pixmap_item)

    def scale_pixmap(self, size=None, fast=False):
        if self.pixmap.isNull():
            return
        if size is None:
            size = self.pixmap_item.boundingRect().size().toSize()
        self.pixmap_item.setPixmap(
            self.pixmap.scaled(size, QtCore.Qt.KeepAspectRatio,
                               QtCore.Qt.FastTransformation if fast else QtCore.Qt.SmoothTransformation))
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:  # window dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == QtCore.Qt.BackButton:
            self.prev()
        elif event.button() == QtCore.Qt.ForwardButton:
            self.next()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            if not self.isFullScreen() and self.drag_position is not None:  # window dragging
                self.move(event.globalPos() - self.drag_position)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not self.isFullScreen():
                self.showFullScreen()
                size = self.ui.view.viewport().geometry().size()
                self.scale_pixmap(size)
            else:
                self.showNormal()
                size = self.ui.view.viewport().geometry().size()
                self.scale_pixmap(size)

    def resizeEvent(self, event):
        # fit contents only when scrollbars go away.
        if (not self.ui.view.verticalScrollBar().isVisible() and
                not self.ui.view.horizontalScrollBar().isVisible()):
            size = self.ui.view.viewport().geometry().size()
            # use fast transforms on resize, do a smooth one after a timer
            self.scale_pixmap(size, fast=True)
            self.draw_timer.start()

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            degrees = event.angleDelta().y() / 8
            steps = int(degrees / 15)
            amount = 1 + (0.1 * steps)

            size = QtCore.QSize(
                self.scene.sceneRect().width() * amount,
                self.scene.sceneRect().height() * amount
            )
            self.scale_pixmap(size)

            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
            self.ui.view.setInteractive(True)
            self.ui.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        elif event.key() == QtCore.Qt.Key_Control:
            self.ui.view.setInteractive(True)
        else:
            super().keyPressEvent(event)
