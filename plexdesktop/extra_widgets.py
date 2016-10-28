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

from PyQt5 import QtWidgets, QtCore, QtGui

import plexdesktop.components
import plexdesktop.style

import plexdesktop.settings
import plexdesktop.utils
import plexdesktop.workers
import plexdesktop.ui.downloadwindow_ui
import plexdesktop.ui.login_ui


class DownloadManager(plexdesktop.components.ComponentWindow):
    download = QtCore.pyqtSignal(queue.Queue)

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.downloadwindow_ui.Ui_DownloadWindow()
        self.ui.setupUi(self)

        self.mutex = QtCore.QMutex()

        self.setWindowTitle('Downloads')
        self.setWindowFlags(QtCore.Qt.Window)
        self.spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
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


class FileDownload(QtWidgets.QProgressDialog):
    update = QtCore.pyqtSignal(float)
    paused = QtCore.pyqtSignal()

    def __init__(self, *args, title='file', parent=None, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.update.connect(self.setValue)
        self.setWindowFlags(QtCore.Qt.Widget)

        self.pause = QtWidgets.QPushButton(self)
        self.label = QtWidgets.QLabel(self)
        self.pause.pressed.connect(self.paused.emit)
        self.setLabel(self.label)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.setMaximumHeight(100)
        self.setMinimumHeight(100)

    def update_progress(self, job, val, rate):
        self.update.emit(val)
        self.label.setText('{} {:,.1f} kbps'.format(job.item.title, rate / 1024))


class HubSearch(QtWidgets.QLineEdit):
    focus_in = QtCore.pyqtSignal()
    hide_results = QtCore.pyqtSignal()
    cancel = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        """style is relying on object names so make sure they are set
           before registering widgets"""
        self.setObjectName('HubSearch')

        search_action = QtWidgets.QAction(self)
        search_action.setObjectName('search_action')
        close_action = QtWidgets.QAction(self)
        close_action.setObjectName('close_action')
        close_action.triggered.connect(self.cancel.emit)
        close_action.triggered.connect(self.clear)

        self.addAction(search_action, QtWidgets.QLineEdit.LeadingPosition)
        self.addAction(close_action, QtWidgets.QLineEdit.TrailingPosition)

        plexdesktop.style.Style.Instance().widget.register(search_action, 'glyphicons-search')
        plexdesktop.style.Style.Instance().widget.register(close_action, 'cancel')

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.clear()
            self.cancel.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class TrackSelector(QtWidgets.QComboBox):
    trackChanged = QtCore.pyqtSignal(str)

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


class GraphicsView(QtWidgets.QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag = False

    def wheelEvent(self, event):
        # ignore modified scroll events so the parent can use them
        if event.modifiers() & QtCore.Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        # "any mouse or key events are ignored" http://doc.qt.io/qt-5/QtWidgets.qgraphicsview.html#interactive-prop
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
        if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.setInteractive(False)
        elif event.key() == QtCore.Qt.Key_Control:
            self.setInteractive(False)
        else:
            super().keyReleaseEvent(event)


class ManualServerDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Manual Add Server')
        self.form = QtWidgets.QFormLayout(self)
        self.secure = QtWidgets.QCheckBox()
        self.address = QtWidgets.QLineEdit()
        self.port = QtWidgets.QLineEdit('32400')
        self.token = QtWidgets.QLineEdit()
        self.form.addRow(QtWidgets.QLabel('HTTPS?'), self.secure)
        self.form.addRow(QtWidgets.QLabel('Address'), self.address)
        self.form.addRow(QtWidgets.QLabel('Port'), self.port)
        self.form.addRow(QtWidgets.QLabel('Access Token (optional)'), self.token)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

    def data(self):
        return ('https' if self.secure.checkState() == QtCore.Qt.Checked else 'http', self.address.text(), self.port.text(), self.token.text())


class PreferencesObjectDialog(QtWidgets.QDialog):

    def __init__(self, media_object, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Preferences')
        self.form = QtWidgets.QFormLayout(self)
        server = media_object.container.server
        settings = server.container(media_object.key)
        self.ids = []
        for item in settings['_children']:
            itype = item['type']
            if itype == 'bool':
                input_widget = QtWidgets.QCheckBox()
                input_widget.setCheckState(QtCore.Qt.Checked if item['value'] == 'true' else QtCore.Qt.Unchecked)
            elif itype == 'enum':
                input_widget = QtWidgets.QComboBox()
                input_widget.addItems(item['values'].split('|'))
                input_widget.setCurrentIndex(int(item['value']))
            elif itype == 'text':
                input_widget = QtWidgets.QLineEdit(item['value'])
                if item['secure'] == 'true':
                    input_widget.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
            else:
                input_widget = QtWidgets.QLabel('...')
            self.form.addRow(QtWidgets.QLabel(item['label']), input_widget)
            self.ids.append((item['id'], input_widget))

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        if self.exec_() == QtWidgets.QDialog.Accepted:
            media_object.container.server.request(media_object.key + '/set', params=self.extract_values())

    def extract_values(self):
        values = {}
        for pid, widget in self.ids:
            if isinstance(widget, QtWidgets.QLineEdit):
                values[pid] = widget.text()
            elif isinstance(widget, QtWidgets.QComboBox):
                values[pid] = widget.currentIndex()
            elif isinstance(widget, QtWidgets.QCheckBox):
                values[pid] = 'true' if widget.checkState() == QtCore.Qt.Checked else 'false'
        return values


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.ui = plexdesktop.ui.login_ui.Ui_Login()
        self.ui.setupUi(self)
        if session is not None:
            self.ui.username.setText(session.user)

    def data(self):
        return (self.ui.username.text(), self.ui.password.text())


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = plexdesktop.settings.Settings()
        self.setWindowTitle('Preferences')
        self.form = QtWidgets.QFormLayout(self)

        i = QtWidgets.QComboBox()
        i.addItems(plexdesktop.style.Style.Instance().themes)
        i.setCurrentIndex(i.findText(s.value('theme')))
        self.form.addRow(QtWidgets.QLabel('theme'), i)

        bf = QtWidgets.QSpinBox()
        bf.setValue(int(s.value('browser_font', 9)))
        self.form.addRow(QtWidgets.QLabel('browser font size'), bf)

        icon_size = QtWidgets.QLineEdit(str(s.value('thumb_size', 240)))
        icon_size.setValidator(QtGui.QIntValidator(0, 300))
        self.form.addRow(QtWidgets.QLabel('thumbnail size'), icon_size)

        widget_player = QtWidgets.QCheckBox()
        widget_player.setCheckState(QtCore.Qt.Checked if bool(int(s.value('widget_player', 0))) else QtCore.Qt.Unchecked)
        self.form.addRow(QtWidgets.QLabel('use widget player'), widget_player)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        self.form.addRow(self.buttons)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)

        if self.exec_() == QtWidgets.QDialog.Accepted:
            # s = Settings()
            theme = i.currentText()
            s.setValue('theme', theme)
            plexdesktop.style.Style.Instance().theme(theme)

            s.setValue('browser_font', bf.value())

            s.setValue('thumb_size', int(icon_size.text()))

            s.setValue('widget_player', 1 if widget_player.checkState() == QtCore.Qt.Checked else 0)
