import time
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, Qt, QThread, QPoint, QSize, QObject, QTimer
import player_ui
from settings import Settings
import utils
import mpv

class MpvEventLoop(QObject):
    mpvevent = pyqtSignal(dict)
    shutdown_event = pyqtSignal(dict)

    def __init__(self, mpv_instance, parent=None):
        super(MpvEventLoop, self).__init__(parent)
        self.mpv = mpv_instance

    def run(self):
        for event in mpv._event_generator(self.mpv.handle):
            devent = event.as_dict() # copy data from ctypes
            self.mpvevent.emit(devent)
            if devent['event_id'] == mpv.MpvEventID.SHUTDOWN:
                self.shutdown_event.emit(devent)
                break


class MPVPlayer(QWidget):
    player_stopped = pyqtSignal(int)
    playback_started = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = player_ui.Ui_Player()
        self.ui.setupUi(self)

        self.ui.player_widget.setMouseTracking(True)
        self.setMouseTracking(True)
        self.cursor_timer = QTimer()
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.setInterval(1000)
        self.cursor_timer.timeout.connect(self.hide_cursor)

        self._event_handlers = {
            mpv.MpvEventID.NONE:                  self.do_nothing,
            mpv.MpvEventID.SHUTDOWN:              self.do_nothing,
            mpv.MpvEventID.LOG_MESSAGE:           self.do_nothing,
            mpv.MpvEventID.GET_PROPERTY_REPLY:    self.do_nothing,
            mpv.MpvEventID.SET_PROPERTY_REPLY:    self.do_nothing,
            mpv.MpvEventID.COMMAND_REPLY:         self.do_nothing,
            mpv.MpvEventID.START_FILE:            self.do_nothing,
            mpv.MpvEventID.END_FILE:              self.do_end_file, #
            mpv.MpvEventID.FILE_LOADED:           self.do_nothing,
            mpv.MpvEventID.TRACKS_CHANGED:        self.do_nothing,
            mpv.MpvEventID.TRACK_SWITCHED:        self.do_nothing,
            mpv.MpvEventID.IDLE:                  self.do_nothing,
            mpv.MpvEventID.PAUSE:                 self.do_pause,    #
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
            wid=wid,
            input_cursor='no',
            cursor_autohide='no',
            cache_backbuffer=10*1024,
            cache_default=10*1024,
            demuxer_max_bytes=50*1024*1024
        )

        self.mpv.observe_property(0, "pause", mpv.MpvFormat.FLAG)
        self.mpv.observe_property(0, "unpause", mpv.MpvFormat.FLAG)
        self.mpv.observe_property(0, 'playback-time', mpv.MpvFormat.DOUBLE)
        self.mpv.observe_property(0, 'duration', mpv.MpvFormat.DOUBLE)
        self.mpv.observe_property(0, 'volume', mpv.MpvFormat.DOUBLE)

        #########
        self._event_thread = QThread()
        self.event_loop = MpvEventLoop(self.mpv)
        self.event_loop.moveToThread(self._event_thread)
        self.event_loop.mpvevent.connect(self._event_handler)
        self.event_loop.shutdown_event.connect(self.do_shutdown)
        self._event_thread.started.connect(self.event_loop.run)
        self._event_thread.start()
        ########

        self.settings = Settings()
        self.last_volume = int(self.settings.value('last_volume', 0))
        self.mpv.add_volume(-100)
        self.mpv.add_volume(self.last_volume)
        self.drag_position = None
        self._playback_time_count = 0
        self.paused = False

        self.play_queue = None
        self.current_item = None
        self.resized = False

        self.ui.slider_progress.sliderReleased.connect(self.seek)
        self.ui.slider_progress.sliderMoved.connect(self.update_current_time)
        self.ui.slider_volume.valueChanged.connect(self.volume)
        self.ui.btn_play.clicked.connect(self.pause)

        self.hide()

    @property
    def headers(self):
        return {'X-Plex-Client-Identifier': "test1",
                'X-Plex-Device-Name': "test1"}

    ############################################################################
    def _event_handler(self, devent):
        eventid = devent.get('event_id', None)
        event = devent.get('event', None)
        if eventid in self._event_handlers:
            self._event_handlers[eventid](event)


    def do_nothing(self, event):
        pass

    def do_shutdown(self):
        print('do_shutdown')
        self.mpv.detach_destroy()
        self.mpv = None
        self.settings.setValue('last_volume', int(self.last_volume))
        self._event_thread.quit()
        self._event_thread.wait()
        self.player_stopped.emit(self.ui.slider_progress.value())

    def do_end_file(self, event):
        print('end file')
        self.update_timeline(state='paused')
        self.update_timeline(state='stopped')

    def do_pause(self, event):
        self.paused = True
        self.update_timeline(state='paused')

    def do_unpause(self, event):
        self.paused = False
        self.update_timeline(state='playing')

    def do_playback_restart(self, event):
        self.show()
        try:
            video_params = self.mpv.video_params
            if not self.resized:
                self.resized = True
                self.resize(QSize(video_params['w'], video_params['h']+self.ui.control_bar.height()))
        except Exception:
            pass
        if self.current_item['viewOffset'] > 0:
            self.mpv.seek(self.current_item['viewOffset']//1000, 'absolute')
            self.current_item['viewOffset'] = 0
        self.playback_started.emit()

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
            self._playback_time_count += 1
            if self._playback_time_count == 500:
                self.update_timeline('playing')
                self._playback_time_count = 0
            if not self.ui.slider_progress.isSliderDown():
                ms = event['data']*1000
                self.update_current_time(ms)
                self.ui.slider_progress.setSliderPosition(ms)
    ############################################################################

    def hide_cursor(self):
        self.setCursor(Qt.BlankCursor)

    def update_current_time(self, value):
        self.ui.lbl_current_time.setText(utils.timestamp_from_ms(milliseconds=value))

    def update_total_time(self, value):
        self.ui.lbl_total_time.setText(utils.timestamp_from_ms(milliseconds=value))

    def play(self, media_object):
        self.setWindowTitle(media_object['title'])

        self.play_queue = media_object.parent.server.play_queue(self.headers, media_object)
        self.current_item = (self.play_queue.selected_item
                             if self.play_queue.selected_item is not None
                             else media_object)

        if 'duration' in self.current_item:
            self.update_total_time(int(self.current_item['duration']))
            self.ui.slider_progress.setMaximum(int(self.current_item['duration']))
        if 'viewOffset' not in self.current_item:
            self.current_item['viewOffset'] = 0

        url = self.current_item.resolve_url()
        self.mpv.play(url)

    def pause(self):
        self.mpv.command('cycle', 'pause')

    def seek(self):
        self.mpv.seek(self.ui.slider_progress.value()/1000, 'absolute')
        self.update_timeline('playing')

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
        if self.current_item is None or 'playQueueItemID' not in self.current_item:
            return
        code, res = self.play_queue.server.request('/:/timeline', headers=self.headers, params={
            'state': state,
            'identifier': self.play_queue['identifier'],
            'playQueueItemID': self.current_item['playQueueItemID'],
            'ratingKey': self.current_item['ratingKey'],
            'duration': self.current_item['duration'],
            'time': min(self.ui.slider_progress.value(), self.current_item['duration'])
        })
        print('TIMELINE {}/{} - {}'.format(utils.timestamp_from_ms(self.ui.slider_progress.value()),
                                           utils.timestamp_from_ms(self.current_item['duration']),
                                           code))

    # QT EVENTS ################################################################
    def closeEvent(self, event):
        self.update_timeline(state='stopped')
        self.mpv.quit()

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
        self.unsetCursor()
        self.cursor_timer.start()
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
