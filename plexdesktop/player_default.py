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

import os
import logging
import uuid

import mpv
import mpv.templates

import PyQt5.QtCore

from plexdesktop import __title__
import plexdesktop.utils
import plexdesktop.components
import plexdesktop.settings

import plexdevices

logger = logging.getLogger('plexdesktop')
mpv_logger = logging.getLogger('plexdesktop.mpv')
Qt = PyQt5.QtCore.Qt


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


class TimelineUpdater(PyQt5.QtCore.QObject):
    def update(self, play_queue, item, time, headers, state='playing'):
        play_queue.timeline_update(item, int(time * 1000), headers, state)


class PlexMpv(mpv.templates.MpvTemplatePyQt):
    next_item = PyQt5.QtCore.pyqtSignal(plexdevices.media.MediaItem)
    update_timeline = PyQt5.QtCore.pyqtSignal(plexdevices.media.PlayQueue,
                                              plexdevices.media.MediaItem,
                                              float, dict, str)
    play_queue_updated = PyQt5.QtCore.pyqtSignal(plexdevices.media.PlayQueue)
    finished = PyQt5.QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeline_thread = PyQt5.QtCore.QThread(self)
        self._timeline_updater = TimelineUpdater()
        self._timeline_updater.moveToThread(self._timeline_thread)
        self.update_timeline.connect(self._timeline_updater.update)
        self._timeline_thread.start()
        self.plex_play_queue = None
        self.plex_current_item = None
        self.timeline_timer = PyQt5.QtCore.QElapsedTimer()

        self.last_playback_time = 0

        self.headers = {
            'X-Plex-Client-Identifier': uuid.uuid4().hex,
            'X-Plex-Device-Name': 'plexdesktop player'
        }

    def on_shutdown(self):
        # save the volume level
        s = plexdesktop.settings.Settings()
        s.setValue('last_volume', self.volume)
        # tell the server where we stopped
        self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                  self.last_playback_time, self.headers, 'stopped')
        # cleanup
        self._timeline_thread.quit()
        self._timeline_thread.wait()
        if self.handle:
            self._event_thread.quit()  # end the event thread
            self._event_thread.wait()
            self.terminate_destroy()  # destroy mpv
        self.finished.emit()

    def create_play_queue(self, media_object):
        self.plex_play_queue = plexdevices.media.PlayQueue.create(media_object,
                                                                  self.headers)
        selected = self.plex_play_queue.selected_item
        self.plex_current_item = selected if selected else media_object

        for i, item in enumerate(self.plex_play_queue.children):
            self.append_item(item)
        self.play_queue_updated.emit(self.plex_play_queue)

    def on_log_message(self, event):
        msg = '{e.prefix}: {e.text}'.format(e=event)
        self.log_handler.log(mpv_to_logging(event.level), msg)

    def on_start_file(self):
        self.timeline_timer.restart()

    def on_seek(self):
        self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                  self.playback_time, self.headers, 'playing')

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
        elif event.name == 'playback-time':
            self.last_playback_time = event.data
            if self.timeline_timer.elapsed() > 15000:
                self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                          event.data, self.headers, 'playing')
                self.timeline_timer.restart()

        elif event.name == 'playlist':
            pass
        elif event.name == 'playlist-pos':
            pos = event.data
            item = self.plex_play_queue.children[pos]
            if item != self.plex_current_item:
                self.plex_play_queue.select(item)
                self.plex_current_item = item
            self.update_timeline.emit(self.plex_play_queue, self.plex_current_item,
                                      0, self.headers, 'playing')

    def append_item(self, item):
        url = item.media[0].parts[0].resolve_key()
        args = {'sid': 'no'}
        if item.view_offset:
            args['start'] = '+{}'.format(item.view_offset / 1000.0)
        if isinstance(item, plexdevices.media.Track):
            args['external-file'] = item.resolve_thumb_url()
        self.command_node('loadfile', url, 'append-play', args)

    def playlist_queue_item(self, item):
        if not self.plex_play_queue:
            return
        mpv_playlist_size = self.playlist_count
        self.plex_play_queue.add_item(item, self.headers)
        assert len(self.plex_play_queue.children) > mpv_playlist_size
        for i in range(mpv_playlist_size, len(self.plex_play_queue.children)):
            item = self.plex_play_queue.children[i]
            self.append_item(item)
        self.play_queue_updated.emit(self.plex_play_queue)

    # def playlist_remove_item(self, items):
    #     if self.plex_play_queue:
    #         for item in items:
    #             self.plex_play_queue.remove_item(item)
    #         self.play_queue_updated.emit(self.plex_play_queue)


class MPVPlayer(plexdesktop.components.ComponentObject):

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        # MPV setup
        self.mpv = PlexMpv(
            log_handler=mpv_logger, log_level=mpv.LogLevel.INFO,
            options={
                # the initial title of the mpv window
                'title': __title__ + ' player',
                # don't close the window at the end of playback.
                'keep-open': 'yes',
                # use black bars when resizing window
                'keepaspect-window': False,
                # use the on screen controls and set some options
                'osc': True,
                'script-opts': 'osc-hidetimeout=5000,osc-fadeduration=400,osc-seekbarstyle=bar,osc-vidscale=no',
                'input-cursor': True,
                # use a custom config dir
                'config': True,
                'config-dir': os.path.join(os.getcwd(), 'mpv'),
                # hide the cursor
                'cursor-autohide': 1000,
                # use our own key bindings. see `mpv/input.conf`
                'input-default-bindings': False,
                'input-vo-keyboard': True,
                # cache sizes
                'cache-backbuffer': 10 * 1024,
                'cache-default': 10 * 1024,
                'demuxer-max-bytes': 25 * 1024 * 1024,
                # hardware decoding
                'hwdec': 'auto'
            },
            observe=[
                'pause',  # for timeline updates
                'playback-time',  # for timeline updates
                'playlist',
                'playlist-pos'  # for syncing the playqueue with mpv playlist
            ])

        s = plexdesktop.settings.Settings()
        # Restore saved volume
        last_vol = float(s.value('last_volume', 0.0))
        self.volume = last_vol

        self.mpv.finished.connect(self._shutdown)

    def play(self, media_object):
        if not self.mpv:
            return
        self.mpv.set_option('title', plexdesktop.utils.title(media_object))
        self.mpv.create_play_queue(media_object)
        logger.info('Player: playQueueID={}'.format(self.mpv.plex_play_queue.id))

    def queue(self, media_object):
        self.mpv.playlist_queue_item(media_object)
