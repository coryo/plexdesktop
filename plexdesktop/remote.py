import logging
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QSettings, QThread
from PyQt5.QtGui import QPixmap
import plexdevices
from plexdesktop.ui.remote_ui import Ui_Remote
from plexdesktop.settings import Settings
logger = logging.getLogger('plexdesktop')


class PlexRemote(QObject, plexdevices.Remote):
    """subclass plexdevices.Remote and QObject to add signal"""
    timeline_signal = pyqtSignal(str)

    def __init__(self, **kwds):
        super().__init__(**kwds)

    def timeline_post(self, data):
        self.timeline_signal.emit(str(data))


class Remote(QWidget, Ui_Remote):

    def __init__(self, session, player, port, name='testremotegui', parent=None):
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)

        logger.info('Remote: Creating remote `{}` on port {} for player {}'.format(name, port, str(player)))
        self.remote = PlexRemote(parent=self, player=player, name=name, port=port)
        self.remote.timeline_subscribe()
        self.session = session
        self.port = port
        self.remote.timeline_signal.connect(self.tl_handler)
        self.key = None
        self.picture = QPixmap()

        self.btn_up.clicked.connect(self.remote.up)
        self.btn_down.clicked.connect(self.remote.down)
        self.btn_left.clicked.connect(self.remote.left)
        self.btn_right.clicked.connect(self.remote.right)
        self.btn_select.clicked.connect(self.remote.select)
        self.btn_back.clicked.connect(self.remote.back)
        self.btn_home.clicked.connect(self.remote.home)
        self.btn_play.clicked.connect(self.remote.play)
        self.btn_pause.clicked.connect(self.remote.pause)
        self.btn_skip_next.clicked.connect(self.remote.skip_next)
        self.btn_skip_prev.clicked.connect(self.remote.skip_previous)
        self.btn_stop.clicked.connect(self.remote.stop)
        self.progress.sliderReleased.connect(self.seek)
        self.show()

    def closeEvent(self, event):
        self.remote.timeline_unsubscribe()

    def seek(self):
        self.remote.seek(self.progress.value() * 1000)

    def tl_handler(self, data):
        try:
            t = self.remote.timeline_active()
            if t is None:
                return
            self.lbl_timeline.setText(str(t))
            tlmax = int(t.get('duration', 1000)) // 1000
            if self.progress.maximum() != tlmax:
                self.progress.setMaximum(tlmax)
            self.progress.setSliderPosition(int(t.get('time', 0)) // 1000)

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
            self.lbl_title.setText(data.get('title', ''))
            self.lbl_summary.setText(data.get('summary', ''))
            self.updateImage(server.image(data['thumb']))

    def updateImage(self, data=None):
        if data is not None:
            self.picture.loadFromData(data)
        w, h = self.lbl_image.width(), self.lbl_image.height()
        self.lbl_image.setPixmap(self.picture.scaled(w, h, Qt.KeepAspectRatio))
