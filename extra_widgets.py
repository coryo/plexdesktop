from PyQt5.QtWidgets import (QLabel, QDialog, QDialogButtonBox, QFormLayout,
                             QCheckBox, QComboBox, QLineEdit)
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
        return (original_size.height() / original_size.width()) * new_width

    def refresh(self):
        if self.img_data is not None:
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
        if self.pix.isNull():
            return
        super().setPixmap(self.pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class ManualServerDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Manual Add Server')
        self.form = QFormLayout(self)
        self.secure = QCheckBox()
        self.address = QLineEdit()
        self.port = QLineEdit('32400')
        self.token = QLineEdit()
        self.form.addRow(QLabel('HTTPS?'), self.secure)
        self.form.addRow(QLabel('Address'), self.address)
        self.form.addRow(QLabel('Port'), self.port)
        self.form.addRow(QLabel('Access Token (optional)'), self.token)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

    def data(self):
        return ('https' if self.secure.checkState() == Qt.Checked else 'http', self.address.text(), self.port.text(), self.token.text())


class PreferencesObjectDialog(QDialog):

    def __init__(self, media_object, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Preferences')
        self.form = QFormLayout(self)
        # settings = media_object.follow_key()
        server = media_object.container.server
        settings = server.container(media_object.key)
        self.ids = []
        for item in settings['_children']:
            itype = item['type']
            if itype == 'bool':
                input_widget = QCheckBox()
                input_widget.setCheckState(Qt.Checked if item['value'] == 'true' else Qt.Unchecked)
            elif itype == 'enum':
                input_widget = QComboBox()
                input_widget.addItems(item['values'].split('|'))
                input_widget.setCurrentIndex(int(item['value']))
            elif itype == 'text':
                input_widget = QLineEdit(item['value'])
                if item['secure'] == 'true':
                    input_widget.setEchoMode(QLineEdit.PasswordEchoOnEdit)
            else:
                input_widget = QLabel('...')
            self.form.addRow(QLabel(item['label']), input_widget)
            self.ids.append((item['id'], input_widget))

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        if self.exec_() == QDialog.Accepted:
            media_object.container.server.request(media_object.key + '/set', params=self.extract_values())

    def extract_values(self):
        values = {}
        for pid, widget in self.ids:
            if isinstance(widget, QLineEdit):
                values[pid] = widget.text()
            elif isinstance(widget, QComboBox):
                values[pid] = widget.currentIndex()
            elif isinstance(widget, QCheckBox):
                values[pid] = 'true' if widget.checkState() == Qt.Checked else 'false'
        return values
