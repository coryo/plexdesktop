from datetime import timedelta
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, Qt, QThread, QPoint
import player_ui
from settings import Settings
import mpv

class MPVPlayer(QWidget, player_ui.Ui_Player, mpv.MPV):
    player_stopped = pyqtSignal(int)

    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)
        self.offset = 0
        self.options = {
            mpv.MpvEventID.NONE: self.do_nothing,
            mpv.MpvEventID.SHUTDOWN: self.do_nothing,
            mpv.MpvEventID.LOG_MESSAGE: self.do_nothing,
            mpv.MpvEventID.GET_PROPERTY_REPLY: self.do_nothing,
            mpv.MpvEventID.SET_PROPERTY_REPLY: self.do_nothing,
            mpv.MpvEventID.COMMAND_REPLY: self.do_nothing,
            mpv.MpvEventID.START_FILE: self.do_nothing,
            mpv.MpvEventID.END_FILE: self.do_nothing,
            mpv.MpvEventID.FILE_LOADED: self.do_nothing,
            mpv.MpvEventID.TRACKS_CHANGED: self.do_nothing,
            mpv.MpvEventID.TRACK_SWITCHED: self.do_nothing,
            mpv.MpvEventID.IDLE: self.do_nothing,
            mpv.MpvEventID.PAUSE: self.do_nothing,
            mpv.MpvEventID.UNPAUSE: self.do_nothing,
            mpv.MpvEventID.TICK: self.do_nothing,
            mpv.MpvEventID.SCRIPT_INPUT_DISPATCH: self.do_nothing,
            mpv.MpvEventID.CLIENT_MESSAGE: self.do_nothing,
            mpv.MpvEventID.VIDEO_RECONFIG: self.do_nothing,
            mpv.MpvEventID.AUDIO_RECONFIG: self.do_nothing,
            mpv.MpvEventID.METADATA_UPDATE: self.do_nothing,
            mpv.MpvEventID.SEEK: self.do_nothing,
            mpv.MpvEventID.PLAYBACK_RESTART: self.do_playback_restart, #
            mpv.MpvEventID.PROPERTY_CHANGE: self.do_property_change,   #
            mpv.MpvEventID.CHAPTER_CHANGE: self.do_nothing
        }

        wid = int(self.player_widget.winId())
        mpv.MPV.__init__(self, self,
                         wid=wid,
                         input_cursor='no',
                         cursor_autohide='no',
                         cache_backbuffer=10*1024,
                         cache_default=10*1024,
                         demuxer_max_bytes=50*1024*1024)

        mpv._mpv_observe_property(self.handle, 0, b"pause", mpv.MpvFormat.FLAG)
        mpv._mpv_observe_property(self.handle, 0, b'playback-time', mpv.MpvFormat.DOUBLE)
        mpv._mpv_observe_property(self.handle, 0, b'duration', mpv.MpvFormat.DOUBLE)
        mpv._mpv_observe_property(self.handle, 0, b'volume', mpv.MpvFormat.DOUBLE)
        
        self.settings = Settings()
        self.last_volume = self.settings.value('last_volume', 0)
        self.add_volume(-100)
        self.add_volume(self.last_volume)
        self.key = None
        
        self.pos_offset = QPoint(0, 0)

        self.slider_progress.sliderReleased.connect(self._seek)
        self.slider_progress.sliderMoved.connect(self.update_time)
        self.slider_volume.valueChanged.connect(self._volume)
        self.btn_play.clicked.connect(self._pause)

        self.show()

    # MPV event callback
    def call(self, devent):
        eventid = devent.get('event_id', None)
        event = devent.get('event', None)
        if eventid in self.options:
            self.options[eventid](event)

    def do_nothing(self, event):
        pass

    def do_playback_restart(self, event):
        print(self.track_list)
        if self.offset > 0:
            self.seek(self.offset/1000, 'absolute')
            self.offset = 0
    def do_property_change(self, event):
        if event['name'] == 'duration':
            self.slider_progress.setMaximum(int(event['data']*1000))
            self.lbl_total_time.setText(str(timedelta(seconds=int(event['data']))))
        elif event['name'] == 'volume':
            self.slider_volume.setSliderPosition(int(event['data']))
            self.last_volume = int(event['data'])
        elif event['name'] == 'playback-time':
            if not self.slider_progress.isSliderDown():
                self.lbl_current_time.setText(str(timedelta(seconds=int(event['data']))))
                self.slider_progress.setSliderPosition(int(event['data']*1000))

    def update_time(self, value):
        self.lbl_current_time.setText(str(timedelta(milliseconds=value)))

    def _play(self, url, item):
        self.setWindowTitle(item['title'])
        self.key = item['key']
        self.offset = item.get('viewOffset', 0)
        self.slider_progress.setMaximum(item.get('duration', 1000))
        self.show()
        # self.key = key
        # self.offset = offset
        self.play(url)

    def _pause(self):
        self.command('cycle', 'pause')

    def _seek(self):
        self.seek(self.slider_progress.value()/1000, 'absolute')

    def _volume(self):
        delta = int(self.slider_volume.value()) - self.last_volume
        self.add_volume(delta)
        self.last_volume = int(self.slider_volume.value())

    def toggle_control_bar(self):
        if self.control_bar.isVisible():
            self.control_bar.hide()
        else:
            self.control_bar.show()

    # QT EVENTS ################################################################
    def closeEvent(self, event):
        print(self.slider_progress.value())
        self.quit()
        mpv._mpv_terminate_destroy(self.handle)
        self.settings.setValue('last_volume', self.last_volume)
        self.player_stopped.emit(self.slider_progress.value())

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = int(degrees / 15)
        self.slider_volume.setSliderPosition(self.slider_volume.value()+steps)
        event.accept()

    # def mousePressEvent(self, event):
    #     self.pos_offset = event.pos()

    # def mouseMoveEvent(self, event):
    #     if not self.isFullScreen() and event.buttons() == Qt.LeftButton:
    #         self.move(self.mapToGlobal(event.pos() - self.pos_offset))

    def mouseDoubleClickEvent(self, event):
        #print(self.windowHandle().screen())
        if not self.isFullScreen():
            self.windowHandle().setScreen(self.windowHandle().screen())
            self.showFullScreen()
            self.control_bar.hide()
        else:
            self.showNormal()
            self.control_bar.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._pause()
        elif event.key() == Qt.Key_QuoteLeft:
            self.toggle_control_bar()

