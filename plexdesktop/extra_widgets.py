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

import queue

import PyQt5.QtWidgets
import PyQt5.QtCore

import plexdesktop.components
import plexdesktop.style

import plexdesktop.settings
import plexdesktop.utils
import plexdesktop.workers
import plexdesktop.ui.downloadwindow_ui
import plexdesktop.ui.login_ui

Qt = PyQt5.QtCore.Qt


class DownloadManager(plexdesktop.components.ComponentWindow):
    download = PyQt5.QtCore.pyqtSignal(queue.Queue)

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.downloadwindow_ui.Ui_DownloadWindow()
        self.ui.setupUi(self)

        self.mutex = PyQt5.QtCore.QMutex()

        self.setWindowTitle('Downloads')
        self.setWindowFlags(Qt.Window)
        self.spacer = PyQt5.QtWidgets.QSpacerItem(1, 1, PyQt5.QtWidgets.QSizePolicy.Expanding, PyQt5.QtWidgets.QSizePolicy.Expanding)
        self.ui.layout.insertItem(-1, self.spacer)
        self.jobs = {}
        self.queue = queue.Queue()

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def add(self, item, destination):
        job = plexdesktop.workers.DownloadJob(self.mutex, item, destination)
        job.worker.progress.connect(self.progress)
        self.download.connect(job.worker.download_file)
        job.worker.complete.connect(self.complete)
        job.worker.canceled.connect(self.cancel)

        self.queue.put(job)
        dialog = FileDownload("Downloading. {}".format(plexdesktop.utils.title(item)), "Cancel",
                              0, 100, title=item.title)
        self.jobs[job.id] = (job, dialog)
        dialog.canceled.connect(job.cancel)
        dialog.paused.connect(job.toggle_pause)
        dialog.update_progress(job, 0, 0)
        self.ui.layout.insertWidget(self.ui.layout.count() - 1, dialog)
        self.download.emit(self.queue)
        self.show()

    def complete(self, job):
        job, dialog = self.jobs[job.id]
        job.quit()
        self.ui.layout.removeWidget(dialog)
        dialog.close()
        del self.jobs[job.id]

    def cancel(self, job):
        self.complete(job)

    def progress(self, job, val, rate):
        job, dialog = self.jobs[job.id]
        dialog.update_progress(job, val, rate)


class FileDownload(PyQt5.QtWidgets.QProgressDialog):
    update = PyQt5.QtCore.pyqtSignal(float)
    paused = PyQt5.QtCore.pyqtSignal()

    def __init__(self, *args, title='file', parent=None, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.update.connect(self.setValue)
        self.setWindowFlags(Qt.Widget)

        self.pause = PyQt5.QtWidgets.QPushButton(self)
        self.label = PyQt5.QtWidgets.QLabel(self)
        self.pause.pressed.connect(self.paused.emit)
        self.setLabel(self.label)
        self.setSizePolicy(PyQt5.QtWidgets.QSizePolicy.Preferred, PyQt5.QtWidgets.QSizePolicy.Minimum)
        self.setMaximumHeight(100)
        self.setMinimumHeight(100)

    def update_progress(self, job, val, rate):
        self.update.emit(val)
        self.label.setText('{} {:,.1f} kbps'.format(job.item.title, rate / 1024))


class HubSearch(PyQt5.QtWidgets.QLineEdit):
    focus_in = PyQt5.QtCore.pyqtSignal()
    hide_results = PyQt5.QtCore.pyqtSignal()
    cancel = PyQt5.QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        """style is relying on object names so make sure they are set
           before registering widgets"""
        self.setObjectName('HubSearch')

        search_action = PyQt5.QtWidgets.QAction(self)
        search_action.setObjectName('search_action')
        close_action = PyQt5.QtWidgets.QAction(self)
        close_action.setObjectName('close_action')
        close_action.triggered.connect(self.cancel.emit)
        close_action.triggered.connect(self.clear)

        self.addAction(search_action, PyQt5.QtWidgets.QLineEdit.LeadingPosition)
        self.addAction(close_action, PyQt5.QtWidgets.QLineEdit.TrailingPosition)

        plexdesktop.style.Style.Instance().widget.register(search_action, 'glyphicons-search')
        plexdesktop.style.Style.Instance().widget.register(close_action, 'cancel')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear()
            self.cancel.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class TrackSelector(PyQt5.QtWidgets.QComboBox):
    trackChanged = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []
        self.currentIndexChanged.connect(self.track_changed)

    def set_type(self, ttype):
        self.ttype = ttype

    def update_tracks(self, tracks):
        self.tracks = [t for t in tracks if t['type'] == self.ttype]
        old_state = self.blockSignals(True)
        self.clear()
        if self.ttype == 'sub':
            self.addItem('None', '-1')
        for track in self.tracks:
            tid = track['id']
            display_name = (track.get('lang', track.get('title', '')) + ' ({})'.format(track['codec'])).strip()
            self.addItem(display_name, str(tid))
        self.setVisible(self.count() > 1)
        self.blockSignals(old_state)

    def track_changed(self, index):
        tid = self.itemData(index)
        self.trackChanged.emit(tid)


class GraphicsView(PyQt5.QtWidgets.QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag = False

    def wheelEvent(self, event):
        # ignore modified scroll events so the parent can use them
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        # "any mouse or key events are ignored" http://doc.qt.io/qt-5/PyQt5.QtWidgets.qgraphicsview.html#interactive-prop
        if self.isInteractive():
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.isInteractive():
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        event.ignore()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.setDragMode(PyQt5.QtWidgets.QGraphicsView.NoDrag)
            self.setInteractive(False)
        elif event.key() == Qt.Key_Control:
            self.setInteractive(False)
        else:
            super().keyReleaseEvent(event)


class ManualServerDialog(PyQt5.QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Manual Add Server')
        self.form = PyQt5.QtWidgets.QFormLayout(self)
        self.secure = PyQt5.QtWidgets.QCheckBox()
        self.address = PyQt5.QtWidgets.QLineEdit()
        self.port = PyQt5.QtWidgets.QLineEdit('32400')
        self.token = PyQt5.QtWidgets.QLineEdit()
        self.form.addRow(PyQt5.QtWidgets.QLabel('HTTPS?'), self.secure)
        self.form.addRow(PyQt5.QtWidgets.QLabel('Address'), self.address)
        self.form.addRow(PyQt5.QtWidgets.QLabel('Port'), self.port)
        self.form.addRow(PyQt5.QtWidgets.QLabel('Access Token (optional)'), self.token)
        self.buttons = PyQt5.QtWidgets.QDialogButtonBox(
            PyQt5.QtWidgets.QDialogButtonBox.Ok | PyQt5.QtWidgets.QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

    def data(self):
        return ('https' if self.secure.checkState() == Qt.Checked else 'http', self.address.text(), self.port.text(), self.token.text())


class PreferencesObjectDialog(PyQt5.QtWidgets.QDialog):

    def __init__(self, media_object, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Preferences')
        self.form = PyQt5.QtWidgets.QFormLayout(self)
        server = media_object.container.server
        settings = server.container(media_object.key)
        self.ids = []
        for item in settings['_children']:
            itype = item['type']
            if itype == 'bool':
                input_widget = PyQt5.QtWidgets.QCheckBox()
                input_widget.setCheckState(Qt.Checked if item['value'] == 'true' else Qt.Unchecked)
            elif itype == 'enum':
                input_widget = PyQt5.QtWidgets.QComboBox()
                input_widget.addItems(item['values'].split('|'))
                input_widget.setCurrentIndex(int(item['value']))
            elif itype == 'text':
                input_widget = PyQt5.QtWidgets.QLineEdit(item['value'])
                if item['secure'] == 'true':
                    input_widget.setEchoMode(PyQt5.QtWidgets.QLineEdit.PasswordEchoOnEdit)
            else:
                input_widget = PyQt5.QtWidgets.QLabel('...')
            self.form.addRow(PyQt5.QtWidgets.QLabel(item['label']), input_widget)
            self.ids.append((item['id'], input_widget))

        self.buttons = PyQt5.QtWidgets.QDialogButtonBox(
            PyQt5.QtWidgets.QDialogButtonBox.Ok | PyQt5.QtWidgets.QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        if self.exec_() == PyQt5.QtWidgets.QDialog.Accepted:
            media_object.container.server.request(media_object.key + '/set', params=self.extract_values())

    def extract_values(self):
        values = {}
        for pid, widget in self.ids:
            if isinstance(widget, PyQt5.QtWidgets.QLineEdit):
                values[pid] = widget.text()
            elif isinstance(widget, PyQt5.QtWidgets.QComboBox):
                values[pid] = widget.currentIndex()
            elif isinstance(widget, PyQt5.QtWidgets.QCheckBox):
                values[pid] = 'true' if widget.checkState() == Qt.Checked else 'false'
        return values


class LoginDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.ui = plexdesktop.ui.login_ui.Ui_Login()
        self.ui.setupUi(self)
        if session is not None:
            self.ui.username.setText(session.user)

    def data(self):
        return (self.ui.username.text(), self.ui.password.text())


class SettingsDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = plexdesktop.settings.Settings()
        self.setWindowTitle('Preferences')
        self.form = PyQt5.QtWidgets.QFormLayout(self)

        i = PyQt5.QtWidgets.QComboBox()
        i.addItems(plexdesktop.style.Style.Instance().themes)
        i.setCurrentIndex(i.findText(s.value('theme')))
        self.form.addRow(PyQt5.QtWidgets.QLabel('theme'), i)

        bf = PyQt5.QtWidgets.QSpinBox()
        bf.setValue(int(s.value('browser_font', 9)))
        self.form.addRow(PyQt5.QtWidgets.QLabel('browser font size'), bf)

        icon_size = PyQt5.QtWidgets.QLineEdit(str(s.value('thumb_size', 240)))
        icon_size.setValidator(PyQt5.QtGui.QIntValidator(0, 300))
        self.form.addRow(PyQt5.QtWidgets.QLabel('thumbnail size'), icon_size)

        widget_player = PyQt5.QtWidgets.QCheckBox()
        widget_player.setCheckState(Qt.Checked if bool(int(s.value('widget_player', 0))) else Qt.Unchecked)
        self.form.addRow(PyQt5.QtWidgets.QLabel('use widget player'), widget_player)

        self.buttons = PyQt5.QtWidgets.QDialogButtonBox(
            PyQt5.QtWidgets.QDialogButtonBox.Ok | PyQt5.QtWidgets.QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

        if self.exec_() == PyQt5.QtWidgets.QDialog.Accepted:
            # s = Settings()
            theme = i.currentText()
            s.setValue('theme', theme)
            plexdesktop.style.Style.Instance().theme(theme)

            s.setValue('browser_font', bf.value())

            s.setValue('thumb_size', int(icon_size.text()))

            s.setValue('widget_player', 1 if widget_player.checkState() == Qt.Checked else 0)
