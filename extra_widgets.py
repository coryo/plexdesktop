from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QSize, QBuffer
from PyQt5.QtGui import QPixmap, QImageReader

class AspectRatioLabel(QLabel):
    
    def __init__(self, parent=None):
        super().__init__()
        self.setMinimumSize(1, 1)
        self.pix = QPixmap()
        self.img_data = None
        self.reader = QImageReader()

    def set_pixmap_from_data(self, data):
        self.img_data = data
        buf = QBuffer()
        buf.setData(data)
        self.reader.setDevice(buf)
        self.update_image()

    def update_image(self):
        self.reader.setScaledSize(self.reader.size().scaled(self.size(), Qt.KeepAspectRatio))
        self.setPixmap(QPixmap.fromImage(self.reader.read()))

    def new_height(self, original_size, new_width):
        return (original_size.height()/original_size.width()) * new_width

    def refresh(self):
        self.set_pixmap_from_data(self.img_data)

    def setPixmap(self, pixmap):
        self.pix = pixmap
        super().setPixmap(pixmap)

    def heightForWidth(self, width):
        return (self.pix.height() * width) / max(1, self.pix.width())

    def sizeHint(self):
        w = self.width()
        return QSize(w, self.heightForWidth(w))

    def resizeEvent(self, event):
        super().setPixmap(self.pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
