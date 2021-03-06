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

import mpv
import mpv.templates
import plexdevices

from PyQt5 import QtCore, QtWidgets

from plexdesktop import __title__
import plexdesktop.ui.player_ui
import plexdesktop.style
import plexdesktop.settings
import plexdesktop.browserlist
import plexdesktop.utils
import plexdesktop.components

logger = logging.getLogger('plexdesktop')
mpv_logger = logging.getLogger('plexdesktop.mpv')


def mpv_to_logging(mpv_level_string):
    return {
        'fatal': logging.CRITICAL,
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'info': logging.INFO,
        'v': 15,
        'debug': logging.DEBUG,
        'trace': 5
    }.get(mpv_level_string, logging.WARNING)


class PlexMpv(mpv.templates.MpvTemplatePyQt):
    prop_duration = QtCore.pyqtSignal(float)
    prop_volume = QtCore.pyqtSignal(float)
    prop_playback_time = QtCore.pyqtSignal(float)
    prop_track_list = QtCore.pyqtSignal(list)
    prop_video_params = QtCore.pyqtSignal(dict)
    next_item = QtCore.pyqtSignal(plexdevices.media.MediaItem)
    update_timeline = QtCore.pyqtSignal(plexdevices.media.PlayQueue,
                                              plexdevices.media.MediaItem,
                                              float, dict, str)
    play_queue_updated = QtCore.pyqtSignal(plexdevices.media.PlayQueue)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeline_thread = QtCore.QThread(self)
        self._timeline_updater = TimelineUpdater()
        self._timeline_updater.moveToThread(self._timeline_thread)
        self.update_timeline.connect(self._timeline_updater.update)
        self._timeline_thread.start()

        self.plex_play_queue = None
        self.plex_current_item = None
        self.plex_next_item = None

        self.timeline_timer = QtCore.QElapsedTimer()

    @property
    def headers(self):
        return {'X-Plex-Client-Identifier': 'test1',
                'X-Plex-Device-Name': 'plexdesktop player'}

    def create_play_queue(self, media_object):
        self.plex_play_queue = plexdevices.media.PlayQueue.create(media_object,
                                                                  self.headers)
        selected = self.plex_play_queue.selected_item
        self.plex_current_item = selected if selected else media_object
        self.play_queue_updated.emit(self.plex_play_queue)

    def quit(self):
        self._timeline_thread.quit()
        self._timeline_thread.wait()
        super().quit()

    def on_log_message(self, event):
        msg = '{e.prefix}: {e.text}'.format(e=event)
        self.log_handler.log(mpv_to_logging(event.level), msg)

    def on_start_file(self):
        self.timeline_timer.restart()

    def on_end_file(self, event):
        self.log_handler.debug('Player: do_end_file')
        item = (self.plex_play_queue.get_next() if self.plex_next_item is None else
                self.plex_play_queue.select(self.plex_next_item))
        if item:
            self.plex_current_item = item
            self.plex_next_item = None
            self.next_item.emit(item)

    def on_property_change(self, event):
        if event.data is None:
            self.log_handler.debug('property change with no data: event={}'.format(event))
            return
        if event.name == 'pause':
            try:
                cur_time = self.playback_time
            except mpv.MpvError as e:
                assert e.error_code == mpv.ErrorCode.PROPERTY_UNAVAILABLE
                return
            state = 'paused' if event.data else 'playing'
            self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                      cur_time, self.headers, state)
        elif event.name == 'duration':
            self.prop_duration.emit(event.data)
        elif event.name == 'volume':
            self.prop_volume.emit(event.data)
        elif event.name == 'playback-time':
            self.prop_playback_time.emit(event.data)
            if self.timeline_timer.elapsed() > 15000:
                self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                          event.data, self.headers, 'playing')
                self.timeline_timer.restart()
        elif event.name == 'track-list':
            self.prop_track_list.emit(event.data)
        elif event.name == 'video-params':
            self.prop_video_params.emit(event.data)
        elif event.name == 'video-out-params':
            self.log_handler.debug('video-out-params: {}'.format(event.data))
        elif event.name == 'metadata':
            self.log_handler.debug('metadata: {}'.format(event.data))
        elif event.name == 'chapter-metadata':
            self.log_handler.debug('chapter-metadata: {}'.format(event.data))

    def play(self, url, args):
        self.command_node('loadfile', url, 'replace', args)

    @QtCore.pyqtSlot(str)
    def change_audio_track(self, tid):
        logger.debug('changing audio track: {}'.format(tid))
        self.aid = tid

    @QtCore.pyqtSlot(str)
    def change_video_track(self, tid):
        logger.debug('changing video track: {}'.format(tid))
        self.vid = tid

    @QtCore.pyqtSlot(str)
    def change_sub_track(self, tid):
        logger.debug('changing sub tid: {}'.format(tid))
        if tid == '-1':
            self.sub_visibility = False
        else:
            self.sid = tid
            self.sub_visibility = True

    @QtCore.pyqtSlot()
    def playlist_prev(self):
        self.playlist_play_item(self.plex_play_queue.get_prev())

    @QtCore.pyqtSlot()
    def playlist_next(self):
        self.playlist_play_item(self.plex_play_queue.get_next())

    @QtCore.pyqtSlot(plexdevices.media.MediaItem)
    def playlist_play_item(self, item):
        self.plex_next_item = item
        self.command('stop')  # trigger an end_file

    @QtCore.pyqtSlot(plexdevices.media.MediaItem)
    def playlist_skip_to(self, item):
        self.playlist_play_item(self.plex_play_queue.select(item))

    def playlist_queue_item(self, item):
        if self.plex_play_queue is not None:
            self.plex_play_queue.add_item(item, self.headers)
            self.play_queue_updated.emit(self.plex_play_queue)

    def playlist_remove_item(self, items):
        if self.plex_play_queue is not None:
            for item in items:
                self.plex_play_queue.remove_item(item)
            self.play_queue_updated.emit(self.plex_play_queue)


class TimelineUpdater(QtCore.QObject):
    finished = QtCore.pyqtSignal()

    def update(self, play_queue, item, time, headers, state='playing'):
        play_queue.timeline_update(item, int(time * 1000), headers, state)
        self.finished.emit()


class PlayerUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = plexdesktop.ui.player_ui.Ui_Player()
        self.ui.setupUi(self)
        self.ui.player_widget.setAttribute(QtCore.Qt.WA_DontCreateNativeAncestors)
        self.ui.player_widget.setAttribute(QtCore.Qt.WA_NativeWindow)
        self.ui.player_widget.setMouseTracking(True)
        self.ui.slider_volume.setMaximum(100)
        self.ui.audio_tracks.set_type('audio')
        self.ui.sub_tracks.set_type('sub')
        self.ui.video_tracks.set_type('video')
        # for convenience
        self.controls = self.ui
        self.player = self.ui.player_widget
        self.control_bar = self.ui.control_bar

        style = plexdesktop.style.Style.Instance()
        style.widget.register(self.ui.btn_play, 'glyphicons-pause', 'glyphicons-play')
        style.widget.register(self.ui.btn_prev, 'glyphicons-chevron-left')
        style.widget.register(self.ui.btn_next, 'glyphicons-chevron-right')
        style.refresh()

    @QtCore.pyqtSlot(float)
    def update_seek_slider_position(self, val):
        if not self.ui.slider_progress.isSliderDown():
            self.ui.slider_progress.setSliderPosition(val * 1000)

    @QtCore.pyqtSlot(float)
    def update_seek_slider_maximum(self, val):
        self.ui.slider_progress.setMaximum(val * 1000)

    @QtCore.pyqtSlot(float)
    def update_lbl_total_time(self, val):
        self.ui.lbl_total_time.setText(
            plexdesktop.utils.timestamp_from_ms(milliseconds=val * 1000.0))

    @QtCore.pyqtSlot(float)
    def update_lbl_current_time(self, val):
        self.ui.lbl_current_time.setText(
            plexdesktop.utils.timestamp_from_ms(milliseconds=val * 1000.0))


class MPVPlayer(plexdesktop.components.ComponentWindow):
    player_stopped = QtCore.pyqtSignal()
    mouse_moved = QtCore.pyqtSignal()

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = PlayerUI(self)
        self.setCentralWidget(self.ui)

        menu = self.menuBar().addMenu('&File')
        on_quit = QtWidgets.QAction('&Quit', self)
        on_quit.triggered.connect(self.on_quit)
        menu.addAction(on_quit)

        menu_view = self.menuBar().addMenu('&View')
        on_playlist = QtWidgets.QAction('&Playlist', self)
        on_playlist.triggered.connect(self.on_playlist)
        menu_view.addAction(on_playlist)

        # cursor hiding
        self.ui.setMouseTracking(True)
        self.cursor_timer = QtCore.QTimer(self)
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.setInterval(1000)
        self.cursor_timer.timeout.connect(self.hide_cursor)
        self.mouse_moved.connect(self.cursor_timer.start)

        self.settings = plexdesktop.settings.Settings()
        self.drag_position = None
        self.resized = False
        self.has_border = True
        self.flags = self.windowFlags()

        # Playlist
        self.playlist = plexdesktop.browserlist.PlaylistView(self)
        self.playlist.setWindowFlags(QtCore.Qt.Window)
        self.playlist.setWindowTitle('Playlist')

        # MPV setup
        wid = int(self.ui.player.winId())
        self.mpv = PlexMpv(parent=self,
                           log_handler=mpv_logger, log_level=mpv.LogLevel.INFO,
                           options={'wid': wid,
                                    'title': __title__,
                                    'cursor-autohide': 1000,
                                    'input-cursor': 'no',
                                    'input-vo-keyboard': 'no',
                                    'cache-backbuffer': 10 * 1024,
                                    'cache-default': 10 * 1024,
                                    'demuxer-max-bytes': 25 * 1024 * 1024,
                                    'hwdec': 'auto'},
                           observe=['pause', 'playback-time', 'duration',
                                    'track-list', 'video-params',
                                    'video-out-params', 'metadata',
                                    'chapter-metadata'])

        # Restore saved volume
        try:
            last_vol = self.settings.value('last_volume', 0.0)
            self.slider_volume(int(last_vol))
            self.ui.controls.slider_volume.setValue(int(last_vol))
        except Exception as e:
            logger.error('restore volume: {}'.format(e))

        self.mpv.next_item.connect(self.play)

        # observed properties
        self.mpv.prop_video_params.connect(self.resize_to_vid)
        self.mpv.prop_duration.connect(self.ui.update_seek_slider_maximum)
        self.mpv.prop_duration.connect(self.ui.update_lbl_total_time)
        self.mpv.prop_playback_time.connect(self.ui.update_seek_slider_position)
        self.mpv.prop_playback_time.connect(self.ui.update_lbl_current_time)
        self.mpv.prop_track_list.connect(self.ui.controls.audio_tracks.update_tracks)
        self.mpv.prop_track_list.connect(self.ui.controls.video_tracks.update_tracks)
        self.mpv.prop_track_list.connect(self.ui.controls.sub_tracks.update_tracks)
        # buttons
        self.ui.controls.btn_prev.pressed.connect(self.mpv.playlist_prev)
        self.ui.controls.btn_next.pressed.connect(self.mpv.playlist_next)
        self.ui.controls.btn_play.clicked.connect(self.pause)
        # track selector combo boxes
        self.ui.controls.audio_tracks.trackChanged.connect(self.mpv.change_audio_track)
        self.ui.controls.sub_tracks.trackChanged.connect(self.mpv.change_sub_track)
        self.ui.controls.video_tracks.trackChanged.connect(self.mpv.change_video_track)
        # sliders
        self.ui.controls.slider_volume.valueChanged.connect(self.slider_volume)
        self.ui.controls.slider_progress.sliderReleased.connect(self.slider_seek)
        # playlist
        self.playlist.play.connect(self.mpv.playlist_skip_to)
        self.playlist.remove.connect(self.mpv.playlist_remove_item)
        self.mpv.play_queue_updated.connect(self.playlist.set_container)

    @QtCore.pyqtSlot()
    def on_quit(self):
        self.close()

    @QtCore.pyqtSlot()
    def on_playlist(self):
        self.playlist.setVisible(not self.playlist.isVisible())

    @QtCore.pyqtSlot(int)
    def slider_volume(self, val, f=10):
        slider_max = self.ui.controls.slider_volume.maximum()
        self.mpv.set_volume(100.0 * (f**(val / slider_max) - 1) / (f - 1))

    @QtCore.pyqtSlot()
    def slider_seek(self):
        self.mpv.seek_absolute(self.ui.controls.slider_progress.value())

    @QtCore.pyqtSlot(dict)
    def resize_to_vid(self, video_params):
        if not self.resized:
            if 'w' not in video_params and 'h' not in video_params:
                return
            self.resized = True
            height = (video_params['h'] + self.ui.control_bar.height() +
                      self.menuBar().height())
            self.resize(QtCore.QSize(
                video_params['w'], height))

    @QtCore.pyqtSlot()
    def hide_cursor(self):
        if self.isFullScreen():
            self.setCursor(QtCore.Qt.BlankCursor)

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def queue(self, media_object):
        self.mpv.playlist_queue_item(media_object)

    def pause(self):
        if self.mpv.handle:
            self.mpv.pause = not self.mpv.pause

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def play(self, media_object):
        if not self.mpv:
            return
        # if self.mpv.plex_play_queue is None:
        self.mpv.create_play_queue(media_object)
        logger.info('Player: playQueueID={}'.format(self.mpv.plex_play_queue.id))

        self.setWindowTitle(plexdesktop.utils.title(self.mpv.plex_current_item))

        if len(self.mpv.plex_current_item.media) == 1:
            url = self.mpv.plex_current_item.media[0].parts[0].resolve_key()
        else:
            options = [str(x.height) for x in self.mpv.plex_current_item.media]
            choice, ok = QtWidgets.QInputDialog.getItem(
                self, 'QtWidgets.QInputDialog.getItem()',
                'Stream:', options, 0, False
            )
            if ok:
                index = options.index(choice)
                url = self.mpv.plex_current_item.media[index].parts[0].resolve_key()
            else:
                self.close()
                return

        logger.info('Player: playing url: ' + url)

        args = {'sid': 'no'}
        if self.mpv.plex_current_item.view_offset:
            args['start'] = '+{}'.format(self.mpv.plex_current_item.view_offset / 1000.0)
        if isinstance(self.mpv.plex_current_item, plexdevices.media.Track):
            args['vid'] = 'no'

        self.mpv.play(url, args)

    def toggle_control_bar(self):
        self.ui.control_bar.setVisible(not self.ui.control_bar.isVisible())
        self.menuBar().setVisible(not self.menuBar().isVisible())

    def toggle_frame(self):
        if self.has_border:
            self.setWindowFlags(self.flags | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.flags)
        self.has_border = not self.has_border

    # QT EVENTS ################################################################
    def closeEvent(self, event):
        self.settings.setValue('last_volume', self.ui.controls.slider_volume.value())
        self.playlist.quit()
        if self.mpv:
            self.mpv.quit()
            self.mpv = None
        self.closed.emit(self.name)

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = int(degrees / 15)
        self.ui.controls.slider_volume.setSliderPosition(self.ui.controls.slider_volume.value() + steps)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:  # window dragging
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self.unsetCursor()
        if self.isFullScreen():
            self.mouse_moved.emit()
        if event.buttons() & QtCore.Qt.LeftButton:
            if not self.isFullScreen() and self.drag_position is not None:  # window dragging
                self.move(event.globalPos() - self.drag_position)
                event.accept()

    def mouseDoubleClickEvent(self, event):
        if not self.isFullScreen():
            self.showFullScreen()
        else:
            self.showNormal()
        self.ui.control_bar.setVisible(not self.isFullScreen())
        self.menuBar().setVisible(not self.isFullScreen())

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.pause()
        elif event.key() == QtCore.Qt.Key_QuoteLeft:
            self.toggle_control_bar()
        elif event.key() == QtCore.Qt.Key_1:
            self.toggle_frame()
            self.show()
            event.accept()
