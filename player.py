from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QPoint
import player_ui
from settings import Settings
import mpv
import plexdevices

class MPVPlayer(QWidget):
    player_stopped = pyqtSignal(int)
    playback_started = pyqtSignal()

    def __init__(self, parent=None):
        super(MPVPlayer, self).__init__(parent)
        self.ui = player_ui.Ui_Player()
        self.ui.setupUi(self)

        self._event_handlers = {
            mpv.MpvEventID.NONE:                  self.do_nothing,
            mpv.MpvEventID.SHUTDOWN:              self.do_nothing,
            mpv.MpvEventID.LOG_MESSAGE:           self.do_nothing,
            mpv.MpvEventID.GET_PROPERTY_REPLY:    self.do_nothing,
            mpv.MpvEventID.SET_PROPERTY_REPLY:    self.do_nothing,
            mpv.MpvEventID.COMMAND_REPLY:         self.do_nothing,
            mpv.MpvEventID.START_FILE:            self.do_nothing,
            mpv.MpvEventID.END_FILE:              self.do_nothing,
            mpv.MpvEventID.FILE_LOADED:           self.do_nothing,
            mpv.MpvEventID.TRACKS_CHANGED:        self.do_nothing,
            mpv.MpvEventID.TRACK_SWITCHED:        self.do_nothing,
            mpv.MpvEventID.IDLE:                  self.do_nothing,
            mpv.MpvEventID.PAUSE:                 self.do_pause,
            mpv.MpvEventID.UNPAUSE:               self.do_unpause,
            mpv.MpvEventID.TICK:                  self.do_nothing,
            mpv.MpvEventID.SCRIPT_INPUT_DISPATCH: self.do_nothing,
            mpv.MpvEventID.CLIENT_MESSAGE:        self.do_nothing,
            mpv.MpvEventID.VIDEO_RECONFIG:        self.do_nothing,
            mpv.MpvEventID.AUDIO_RECONFIG:        self.do_nothing,
            mpv.MpvEventID.METADATA_UPDATE:       self.do_nothing,
            mpv.MpvEventID.SEEK:                  self.do_nothing,
            mpv.MpvEventID.PLAYBACK_RESTART:      self.do_playback_restart, #
            mpv.MpvEventID.PROPERTY_CHANGE:       self.do_property_change,  #
            mpv.MpvEventID.CHAPTER_CHANGE:        self.do_nothing
        }

        wid = int(self.ui.player_widget.winId())
        self.mpv = mpv.MPV(
            cb=self,
            wid=wid,
            input_cursor='no',
            cursor_autohide='no',
            cache_backbuffer=10*1024,
            cache_default=10*1024,
            demuxer_max_bytes=50*1024*1024
        )

        mpv._mpv_observe_property(self.mpv.handle, 0, b"pause", mpv.MpvFormat.FLAG)
        mpv._mpv_observe_property(self.mpv.handle, 0, b"unpause", mpv.MpvFormat.FLAG)
        mpv._mpv_observe_property(self.mpv.handle, 0, b'playback-time', mpv.MpvFormat.DOUBLE)
        mpv._mpv_observe_property(self.mpv.handle, 0, b'duration', mpv.MpvFormat.DOUBLE)
        mpv._mpv_observe_property(self.mpv.handle, 0, b'volume', mpv.MpvFormat.DOUBLE)

        self.settings = Settings()
        self.last_volume = int(self.settings.value('last_volume', 0))
        self.mpv.add_volume(-100)
        self.mpv.add_volume(self.last_volume)
        self.media_object = None
        self.drag_position = None

        self.ui.slider_progress.sliderReleased.connect(self.seek)
        self.ui.slider_progress.sliderMoved.connect(self.update_current_time)
        self.ui.slider_volume.valueChanged.connect(self.volume)
        self.ui.btn_play.clicked.connect(self.pause)

        self.show()

    @property
    def headers(self):
        return {'X-Plex-Client-Identifier': "test1",
                'X-Plex-Device-Name': "test1"}

    # MPV event callback
    def call(self, devent):
        eventid = devent.get('event_id', None)
        event = devent.get('event', None)
        if eventid in self._event_handlers:
            self._event_handlers[eventid](event)

    def do_nothing(self, event):
        pass

    def do_pause(self, event):
        self.update_timeline(state='paused')

    def do_unpause(self, event):
        self.update_timeline(state='playing')

    def do_playback_restart(self, event):
        self.playback_started.emit()
        if self.media_object['viewOffset'] > 0:
            self.mpv.seek(self.media_object['viewOffset']//1000, 'absolute')
            self.media_object['viewOffset'] = 0

    def do_property_change(self, event):
        if event['data'] is None:
            return
        if event['name'] == 'duration':
            ms = event['data']*1000
            self.ui.slider_progress.setMaximum(ms)
            self.update_total_time(ms)
        elif event['name'] == 'volume':
            self.ui.slider_volume.setSliderPosition(event['data'])
            self.last_volume = event['data']
        elif event['name'] == 'playback-time':
            if not self.ui.slider_progress.isSliderDown():
                ms = event['data']*1000
                self.update_current_time(ms)
                self.ui.slider_progress.setSliderPosition(ms)

    def update_current_time(self, value):
        self.ui.lbl_current_time.setText(self.timestamp_from_ms(milliseconds=value))

    def update_total_time(self, value):
        self.ui.lbl_total_time.setText(self.timestamp_from_ms(milliseconds=value))

    def timestamp_from_ms(self, milliseconds):
        m, s = divmod(milliseconds/1000, 60)
        h, m = divmod(m, 60)
        return "{:.0f}:{:02.0f}:{:02.0f}".format(h, m, s)

    def play(self, media_object):
        url = media_object.resolve_url()
        self.setWindowTitle(media_object['title'])

        self.play_queue = media_object.parent.server.play_queue(self.headers, media_object)
        for item in self.play_queue.children:
            print(item.data)

        self.media_object = media_object
        if 'viewOffset' not in self.media_object:
            self.media_object['viewOffset'] = 0
        self.ui.slider_progress.setMaximum(media_object.get('duration', 1000))
        self.mpv.play(url)

    def pause(self):
        self.mpv.command('cycle', 'pause')

    def seek(self):
        self.mpv.seek(self.ui.slider_progress.value()/1000, 'absolute')

    def volume(self):
        delta = self.ui.slider_volume.value() - self.last_volume
        self.mpv.add_volume(int(delta))
        self.last_volume = self.ui.slider_volume.value()

    def toggle_control_bar(self):
        if self.ui.control_bar.isVisible():
            self.ui.control_bar.hide()
        else:
            self.ui.control_bar.show()

    def update_timeline(self, state='playing'):
        try:
            active_item = self.play_queue.children[0]
        except Exception:
            return
        headers = self.headers
        headers.update(self.play_queue.server.headers)
        code, res = self.play_queue.server.request('/:/timeline', headers=headers, params={
            'state': state,
            'identifier': self.play_queue['identifier'],
            'playQueueItemID': active_item['playQueueItemID'],
            'ratingKey': active_item['ratingKey'],
            'duration':active_item['duration'],
            'time': self.ui.slider_progress.value()
        })
        print('TIMELINE - {}'.format(code))

    # QT EVENTS ################################################################
    def closeEvent(self, event):
        print(self.ui.slider_progress.value())
        self.mpv.quit()
        self.mpv.terminate_destroy()

        self.update_timeline(state='stopped')

        self.settings.setValue('last_volume', int(self.last_volume))
        self.player_stopped.emit(self.ui.slider_progress.value())

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = int(degrees / 15)
        self.ui.slider_volume.setSliderPosition(self.ui.slider_volume.value()+steps)
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

    def mouseDoubleClickEvent(self, event):
        if not self.isFullScreen():
            self.showFullScreen()
            self.ui.control_bar.hide()
        else:
            self.showNormal()
            self.ui.control_bar.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.pause()
        elif event.key() == Qt.Key_QuoteLeft:
            self.toggle_control_bar()
