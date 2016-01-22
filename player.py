import logging
from PyQt5.QtWidgets import QWidget, QInputDialog, QMainWindow
from PyQt5.QtCore import pyqtSignal, Qt, QThread, QPoint, QSize, QObject, QTimer
import player_ui
from settings import Settings
from browserlist import ListView
import utils
import mpv
import plexdevices
logger = logging.getLogger('plexdesktop')
mpv_logger = logging.getLogger('plexdesktop.mpv')


def mpv_to_py_logging(mpv_log_level):
    return {
        'fatal': 'critical',
        'error': 'error',
        'warn': 'warning',
        'info': 'info',
        'v': 'debug',
        'debug': 'debug',
        'trace': 'debug'
    }[mpv_log_level]


class MpvEventLoop(QObject):
    mpvevent = pyqtSignal(dict)

    def __init__(self, mpv_instance, parent=None):
        super(MpvEventLoop, self).__init__(parent)
        self.mpv = mpv_instance

    def run(self):
        for event in mpv._event_generator(self.mpv.handle):
            devent = event.as_dict()  # copy data from ctypes
            self.mpvevent.emit(devent)
            if devent['event_id'] == mpv.MpvEventID.SHUTDOWN:
                break


class TimelineUpdater(QObject):
    done = pyqtSignal()

    def update(self, play_queue, item, time, headers, state='playing'):
        if item is None or 'playQueueItemID' not in item:
            self.done.emit()
            return
        code, res = play_queue.server.request('/:/timeline', headers=headers, params={
            'state': state,
            'identifier': play_queue['identifier'],
            'playQueueItemID': item['playQueueItemID'],
            'ratingKey': item['ratingKey'],
            'duration': item['duration'],
            'time': min(time, item['duration'])
        })
        logger.debug('Player: TIMELINE {}/{} - {}'.format(utils.timestamp_from_ms(time),
                                                          utils.timestamp_from_ms(item['duration']),
                                                          code))
        self.done.emit()


class MPVPlayer(QWidget):
    player_stopped = pyqtSignal(int)
    playback_started = pyqtSignal()
    update_timeline = pyqtSignal(plexdevices.PlayQueue, plexdevices.MediaObject, int, dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = player_ui.Ui_Player()
        self.ui.setupUi(self)
        self.ui.player_widget.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.ui.player_widget.setAttribute(Qt.WA_NativeWindow)

        self.ui.playlist.hide()
        self.ui.playlist.setItemDelegate(self.ui.playlist.delegate_default)
        self.ui.playlist.itemDoubleClicked.connect(self.playlist_item_double_clicked)
        self.ui.btn_playlist.pressed.connect(self.toggle_playlist)

        self.setMinimumSize(self.minimumSizeHint())

        # MPV setup
        wid = int(self.ui.player_widget.winId())
        self.mpv = mpv.MPV(
            wid=wid,
            input_cursor='no',
            cache_backbuffer=10 * 1024,
            cache_default=25 * 1024,
            demuxer_max_bytes=50 * 1024 * 1024,
            hwdec='auto'
        )
        self.mpv.observe_property(0, 'pause', mpv.MpvFormat.FLAG)
        self.mpv.observe_property(0, 'unpause', mpv.MpvFormat.FLAG)
        self.mpv.observe_property(0, 'playback-time', mpv.MpvFormat.DOUBLE)
        self.mpv.observe_property(0, 'duration', mpv.MpvFormat.DOUBLE)
        self.mpv.observe_property(0, 'volume', mpv.MpvFormat.DOUBLE)
        self.mpv.request_log_messages('info')

        self._event_handlers = {
            mpv.MpvEventID.SHUTDOWN: self.do_shutdown,
            mpv.MpvEventID.END_FILE: self.do_end_file,
            mpv.MpvEventID.PAUSE: self.do_pause,
            mpv.MpvEventID.PROPERTY_CHANGE: self.do_property_change,
            mpv.MpvEventID.LOG_MESSAGE: self.do_log_message,
            mpv.MpvEventID.FILE_LOADED: self.do_file_loaded
        }
        # MPV event loop
        self._event_thread = QThread()
        self.event_loop = MpvEventLoop(self.mpv)
        self.event_loop.moveToThread(self._event_thread)
        self.event_loop.mpvevent.connect(self._event_handler)
        self._event_thread.started.connect(self.event_loop.run)
        self._event_thread.start()

        # Timeline updater thread setup
        self._timeline_thread = QThread()
        self.timeline_updater = TimelineUpdater()
        self.timeline_updater.moveToThread(self._timeline_thread)
        self.update_timeline.connect(self.timeline_updater.update, type=Qt.QueuedConnection)
        self._timeline_thread.start()

        # cursor hiding
        self.ui.player_widget.setMouseTracking(True)
        self.setMouseTracking(True)
        self.cursor_timer = QTimer()
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.setInterval(1000)
        self.cursor_timer.timeout.connect(self.hide_cursor)

        self.settings = Settings()
        self.last_volume = int(self.settings.value('last_volume', 0))
        self.drag_position = None
        self._playback_time_count = 0
        self.paused = False
        self.play_queue = None
        self.current_item = None
        self.resized = False
        self.current_time = 0

        self.mpv.add_volume(-100)
        self.mpv.add_volume(self.last_volume)

        self.ui.slider_progress.sliderReleased.connect(self.seek)
        self.ui.slider_progress.sliderMoved.connect(self.update_current_time)
        self.ui.slider_volume.valueChanged.connect(self.volume)
        self.ui.btn_play.clicked.connect(self.pause)

        self.ui.btn_prev.pressed.connect(self.playlist_prev)
        self.ui.btn_next.pressed.connect(self.playlist_next)

    @property
    def headers(self):
        return {'X-Plex-Client-Identifier': 'test1',
                'X-Plex-Device-Name': 'test1'}

    def minimumSizeHint(self):
        return QSize(320, 240)

    def toggle_playlist(self):
        self.ui.playlist.setVisible(not self.ui.playlist.isVisible())

    def playlist_prev(self):
        try:
            index = self.play_queue.children.index(self.current_item)
            if not index:
                return
            self.current_item = self.play_queue.children[self.play_queue.children.index(self.current_item) - 1]
            self.play_queue['playQueueSelectedItemID'] = self.current_item['playQueueItemID']
            url = self.current_item.resolve_url()
            logger.info('Player: prev url: ' + url)
            self.mpv.play(url)
        except Exception as e:
            logger.warning('Player: ' + str(e))

    def playlist_next(self):
        try:
            self.current_item = self.play_queue.children[self.play_queue.children.index(self.current_item) + 1]
            self.play_queue['playQueueSelectedItemID'] = self.current_item['playQueueItemID']
            url = self.current_item.resolve_url()
            logger.info('Player: next url: ' + url)
            self.mpv.play(url)
        except Exception as e:
            logger.warning('Player: ' + str(e))

    def playlist_item_double_clicked(self, item):
        logger.info('Player: playlist dbl click: {}'.format(item))
        self.do_timeline_update(state='paused')
        self.do_timeline_update(state='stopped')
        self.next_item = item
        try:
            self.current_item = item
            self.play_queue['playQueueSelectedItemID'] = self.current_item['playQueueItemID']
            url = self.current_item.resolve_url()
            logger.info('Player: next url: ' + url)
            self.mpv.play(url)
        except Exception as e:
            logger.warning('Player: ' + str(e))
            self.close()

    ############################################################################
    def _event_handler(self, devent):
        eventid = devent.get('event_id', None)
        event = devent.get('event', None)
        if eventid in self._event_handlers:
            self._event_handlers[eventid](event)

    def do_file_loaded(self, event):
        self.playback_started.emit()
        try:
            video_params = self.mpv.video_params
            if not self.resized:
                self.resized = True
                self.resize(QSize(video_params['w'], video_params['h'] + self.ui.control_bar.height()))
        except Exception:
            pass
        if 'viewOffset' in self.current_item:
            if self.current_item['viewOffset'] > 0:
                self.mpv.seek(self.current_item['viewOffset'] // 1000, 'absolute')

    def do_log_message(self, event):
        try:
            level = mpv_to_py_logging(event['level'].decode())
            msg = '{}: {}'.format(event['prefix'].decode(), event['text'].decode().rstrip('\n'))
            getattr(mpv_logger, level)(msg)
        except Exception:
            mpv_logger.warning('mpv log error: {}'.format(event))

    def do_shutdown(self, event):
        logger.info('Player: exiting mpv player')
        self.mpv.detach_destroy()
        self.mpv = None
        self.settings.setValue('last_volume', int(self.last_volume))
        self._event_thread.quit()
        self._event_thread.wait()
        self.player_stopped.emit(self.current_time)#self.ui.slider_progress.value())

    def do_end_file(self, event):
        self.do_timeline_update(state='paused')
        self.do_timeline_update(state='stopped')
        # try:
        #     self.current_item = self.play_queue.children[self.play_queue.children.index(self.current_item) + 1]
        #     self.play_queue['playQueueSelectedItemID'] = self.current_item['playQueueItemID']
        #     url = self.current_item.resolve_url()
        #     logger.info('Player: next url: ' + url)
        #     self.mpv.play(url)
        # except Exception as e:
        #     logger.warning('Player: ' + str(e))
        #     self.close()

    def do_pause(self, event):
        self.paused = True
        self.do_timeline_update(state='paused')

    def do_unpause(self, event):
        self.paused = False
        self.do_timeline_update(state='playing')

    def do_timeline_update(self, state):
        self.media_object['viewOffset'] = self.current_time#self.ui.slider_progress.value()
        self.update_timeline.emit(self.play_queue, self.current_item,
                                  self.current_time,#self.ui.slider_progress.value(),
                                  self.headers, state)

    def do_property_change(self, event):
        if event['data'] is None:
            return
        if event['name'] == 'duration':
            ms = event['data'] * 1000
            self.ui.slider_progress.setMaximum(ms)
            self.update_total_time(ms)
        elif event['name'] == 'volume':
            self.ui.slider_volume.setSliderPosition(event['data'])
            self.last_volume = event['data']
        elif event['name'] == 'playback-time':
            self._playback_time_count += 1
            ms = event['data'] * 1000
            self.current_time = ms
            if self._playback_time_count == 500:
                self.do_timeline_update('playing')
                self._playback_time_count = 0
            if not self.ui.slider_progress.isSliderDown():
                self.update_current_time(self.current_time)
                self.ui.slider_progress.setSliderPosition(self.current_time)

    ############################################################################

    def hide_cursor(self):
        if self.isFullScreen():
            self.setCursor(Qt.BlankCursor)

    def update_current_time(self, value):
        self.ui.lbl_current_time.setText(utils.timestamp_from_ms(milliseconds=value))

    def update_total_time(self, value):
        self.ui.lbl_total_time.setText(utils.timestamp_from_ms(milliseconds=value))

    def play(self, media_object):
        self.setWindowTitle(media_object['title'])

        self.media_object = media_object
        self.play_queue = media_object.parent.server.play_queue(self.headers, media_object)
        logger.info(self.play_queue.data)
        self.current_item = (self.play_queue.selected_item
                             if self.play_queue.selected_item is not None
                             else media_object)
        logger.info(self.current_item.data)

        self.ui.playlist.add_container2(self.play_queue)

        if 'duration' in self.current_item:
            self.update_total_time(int(self.current_item['duration']))
            self.ui.slider_progress.setMaximum(int(self.current_item['duration']))

        self.available_streams = self.current_item.get_all_keys()
        if len(self.available_streams) == 1:
            # theres only one item
            resolution, key = self.available_streams[0]
            url = self.current_item.resolve_key(key)
        else:
            # there are multiple items, prompt for a selection
            items = (x[0] for x in self.available_streams)
            choice, ok = QInputDialog.getItem(self, 'QInputDialog.getItem()', 'Stream:', items, 0, False)
            if ok:
                key = [x[1] for x in self.available_streams if x[0] == choice]
                url = self.current_item.resolve_key(key[0])
            else:
                self.close()
                return

        logger.info('Player: playing url: ' + url)
        self.mpv.play(url)

    def pause(self):
        self.mpv.command('cycle', 'pause')

    def seek(self):
        try:
            self.mpv.seek(self.ui.slider_progress.value() / 1000, 'absolute')
            self.do_timeline_update('playing')
        except Exception as e:
            logger.warning('Player: ' + str(e))

    def volume(self):
        delta = self.ui.slider_volume.value() - self.last_volume
        self.mpv.add_volume(int(delta))
        self.last_volume = self.ui.slider_volume.value()

    def toggle_control_bar(self):
        if self.ui.control_bar.isVisible():
            self.ui.control_bar.hide()
        else:
            self.ui.control_bar.show()

    # QT EVENTS ################################################################
    def closeEvent(self, event):
        self.do_timeline_update(state='stopped')
        self.mpv.quit()
        self._timeline_thread.quit()
        self._timeline_thread.wait()

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = int(degrees / 15)
        self.ui.slider_volume.setSliderPosition(self.ui.slider_volume.value() + steps)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  # window dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self.unsetCursor()
        self.cursor_timer.start()
        if event.buttons() & Qt.LeftButton:
            if not self.isFullScreen() and self.drag_position is not None:  # window dragging
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
