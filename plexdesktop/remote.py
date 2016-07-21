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

import PyQt5.QtCore
import PyQt5.QtGui

import plexdesktop.ui.remote_ui
import plexdesktop.components

logger = logging.getLogger('plexdesktop')
Qt = PyQt5.QtCore.Qt


class PlexRemote(PyQt5.QtCore.QObject, plexdevices.remote.Remote):
    """subclass plexdevices.Remote and PyQt5.QtCore.QObject to add signal"""
    timeline_signal = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def timeline_post(self, data):
        self.timeline_signal.emit(str(data))


class Remote(plexdesktop.components.ComponentWindow):

    def __init__(self, session, player, port, name='testremotegui', parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.remote_ui.Ui_Remote()
        self.ui.setupUi(self)

        logger.info('Remote: Creating remote `{}` on port {} for player {}'.format(name, port, str(player)))

        try:
            self.remote = PlexRemote(parent=self, player=player, name=name, port=port)
            self.remote.timeline_subscribe()
        except plexdevices.DeviceConnectionsError as e:
            self.closed.emit(self.name)
            raise

        self.session = session
        self.port = port
        self.remote.timeline_signal.connect(self.tl_handler)
        self.key = None
        self.name = name
        self.picture = PyQt5.QtGui.QPixmap()

        self.setWindowTitle('{} - remote'.format(player.name))

        self.ui.btn_up.clicked.connect(self.remote.up)
        self.ui.btn_down.clicked.connect(self.remote.down)
        self.ui.btn_left.clicked.connect(self.remote.left)
        self.ui.btn_right.clicked.connect(self.remote.right)
        self.ui.btn_select.clicked.connect(self.remote.select)
        self.ui.btn_back.clicked.connect(self.remote.back)
        self.ui.btn_home.clicked.connect(self.remote.home)
        self.ui.btn_play.clicked.connect(self.remote.play)
        self.ui.btn_pause.clicked.connect(self.remote.pause)
        self.ui.btn_skip_next.clicked.connect(self.remote.skip_next)
        self.ui.btn_skip_prev.clicked.connect(self.remote.skip_previous)
        self.ui.btn_stop.clicked.connect(self.remote.stop)
        self.ui.progress.sliderReleased.connect(self.seek)
        self.show()

    def closeEvent(self, event):
        self.remote.timeline_unsubscribe()
        self.closed.emit(self.name)

    def seek(self):
        self.remote.seek('', self.ui.progress.value() * 1000)

    def tl_handler(self, data):
        try:
            t = self.remote.timeline_active()
            if t is None:
                return
            self.ui.lbl_timeline.setText(str(t))
            tlmax = int(t.get('duration', 1000)) // 1000
            if self.ui.progress.maximum() != tlmax:
                self.ui.progress.setMaximum(tlmax)
            self.ui.progress.setSliderPosition(int(t.get('time', 0)) // 1000)

            if 'key' not in t or 'machineIdentifier' not in t:
                return
            key, mid = t['key'], t['machineIdentifier']
            if self.key != key:
                try:
                    server = [s for s in self.session.servers if s.client_identifier == mid][0]
                    self.updateData(server, key)
                except Exception as e:
                    logger.error('Remote: metadata {}'.format(str(e)))
        except Exception as e:
            logger.error('Remote: {}'.format(str(e)))

    def updateData(self, server, key):
        self.key = key
        try:
            data = server.container(key)['_children'][0]
        except Exception as e:
            logger.error('Remote: updateData: {}'.format(str(e)))
        else:
            self.ui.lbl_title.setText(data.get('title', ''))
            self.ui.lbl_summary.setText(data.get('summary', ''))
            self.updateImage(server.image(data['thumb']))

    def updateImage(self, data=None):
        if data is not None:
            self.picture.loadFromData(data)
        w, h = self.ui.lbl_image.width(), self.ui.lbl_image.height()
        self.ui.lbl_image.setPixmap(self.picture.scaled(w, h, Qt.KeepAspectRatio))
