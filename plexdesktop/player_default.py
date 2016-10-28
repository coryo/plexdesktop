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

from PyQt5 import QtCore

from plexdesktop import __title__
import plexdesktop.utils
import plexdesktop.components
import plexdesktop.settings

import plexdevices

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


class PlayQueueManager(QtCore.QObject):
    working = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    new_queue = QtCore.pyqtSignal(plexdevices.media.PlayQueue)
    new_item = QtCore.pyqtSignal(plexdevices.media.MediaItem)
    updated_queue = QtCore.pyqtSignal(plexdevices.media.PlayQueue)
    new_selection = QtCore.pyqtSignal(plexdevices.media.MediaItem)
    removed_index = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.play_queue = None
        self.current_item = None
        self.headers = {
            'X-Plex-Client-Identifier': uuid.uuid4().hex,
            'X-Plex-Device-Name': 'plexdesktop player'
        }

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def create(self, item):
        if not item.container.is_library:
            return self.new_item.emit(item)
        self.working.emit()
        self.play_queue = plexdevices.media.PlayQueue.create(item, self.headers)
        selected = self.play_queue.selected_item
        self.current_item = selected if selected else item
        logger.info('Player: playQueueID={}'.format(self.play_queue.id))
        self.new_queue.emit(self.play_queue)
        self.finished.emit()

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def enqueue(self, item):
        if not self.play_queue:
            return self.new_item.emit(item)
        self.working.emit()
        self.play_queue.add_item(item, self.headers)
        self.updated_queue.emit(self.play_queue)
        self.finished.emit()

    @QtCore.pyqtSlot(int)
    def dequeue(self, index):
        if not self.play_queue:
            return
        self.working.emit()
        item = self.play_queue.children[index]
        self.play_queue.remove_item(item)
        self.removed_index.emit(int)
        self.finished.emit()

    @QtCore.pyqtSlot(float, str)
    def update(self, time, state='playing'):
        if self.play_queue and self.current_item:
            self.play_queue.timeline_update(
                self.current_item, int(time * 1000), self.headers, state)

    @QtCore.pyqtSlot(int)
    def select(self, index):
        if not self.play_queue:
            return
        self.working.emit()
        item = self.play_queue.children[index]
        if item != self.current_item:
            self.play_queue.select(item)
            self.current_item = item
        self.update(0, 'playing')
        self.new_selection.emit(item)
        self.finished.emit()


class PlexMpv(mpv.templates.MpvTemplatePyQt):
    update_timeline = QtCore.pyqtSignal(float, str)
    create_play_queue = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    enqueue = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    dequeue = QtCore.pyqtSignal(int)
    select = QtCore.pyqtSignal(int)

    shutdown_complete = QtCore.pyqtSignal()
    working = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._play_queue_thread = QtCore.QThread(self)
        self.play_queue = PlayQueueManager()
        self.play_queue.moveToThread(self._play_queue_thread)
        self.update_timeline.connect(self.play_queue.update)
        self._play_queue_thread.start()

        self.timeline_timer = QtCore.QElapsedTimer()

        self.last_playback_time = 0

        self.play_queue.new_item.connect(self.append_item)
        self.play_queue.new_selection.connect(self._new_active_item)
        self.play_queue.new_queue.connect(self._replace_playlist)
        self.play_queue.updated_queue.connect(self._consolidate_playlist)
        self.play_queue.removed_index.connect(self._remove_item)
        self.play_queue.working.connect(self.working)
        self.play_queue.finished.connect(self.finished)

        self.enqueue.connect(self.play_queue.enqueue)
        self.create_play_queue.connect(self.play_queue.create)
        self.select.connect(self.play_queue.select)

    def on_shutdown(self):
        # save the volume level
        s = plexdesktop.settings.Settings()
        s.setValue('last_volume', self.volume)
        # tell the server where we stopped
        self.update_timeline.emit(self.last_playback_time, 'stopped')
        # cleanup
        self._play_queue_thread.quit()
        self._play_queue_thread.wait()
        if self.handle:
            self._event_thread.quit()  # end the event thread
            self._event_thread.wait()
            self.detach_destroy()  # destroy mpv
        self.shutdown_complete.emit()

    @QtCore.pyqtSlot(plexdevices.media.MediaItem)
    def _new_active_item(self, item):
        self.set_option('title', plexdesktop.utils.title(item))

    @QtCore.pyqtSlot(plexdevices.media.PlayQueue)
    def _replace_playlist(self, play_queue):
        self.command('playlist-clear')
        for i, item in enumerate(play_queue.children):
            self.append_item(item)

    @QtCore.pyqtSlot(plexdevices.media.PlayQueue)
    def _consolidate_playlist(self, play_queue):
        mpv_playlist_size = self.playlist_count
        for i in range(mpv_playlist_size, len(play_queue.children)):
            item = play_queue.children[i]
            self.append_item(item)

    @QtCore.pyqtSlot(int)
    def _remove_item(self, index):
        self.command_node('playlist-remove', index)

    def append_item(self, item):
        """append a media item to the mpv playlist, with a standard set of
        options."""
        url = item.media[0].parts[0].resolve_key()
        args = {'sid': 'no'}
        if item.view_offset:
            args['start'] = '+{}'.format(item.view_offset / 1000.0)
        if isinstance(item, plexdevices.media.Track):
            args['external-file'] = item.resolve_thumb_url()
        self.command_node('loadfile', url, 'append-play', args)

    def on_log_message(self, event):
        msg = '{e.prefix}: {e.text}'.format(e=event)
        self.log_handler.log(mpv_to_logging(event.level), msg)

    def on_start_file(self):
        self.timeline_timer.restart()

    def on_seek(self):
        self.update_timeline.emit(self.playback_time, 'playing')

    def on_property_change(self, event):
        if event.name == 'pause':
            try:
                cur_time = self.playback_time
            except mpv.MpvError as e:
                return
            state = 'paused' if event.data else 'playing'
            self.update_timeline.emit(cur_time, state)
        elif event.name == 'playback-time':
            self.last_playback_time = event.data
            if self.timeline_timer.elapsed() > 15000:
                self.update_timeline.emit(event.data, 'playing')
                self.timeline_timer.restart()
        elif event.name == 'playlist':
            pass
        elif event.name == 'playlist-pos':
            self.select.emit(event.data)

    def play(self, item):
        if item.container.is_library:
            self.create_play_queue.emit(item)
        else:
            self.append_item(item)

    def playqueue_add(self, item):
        self.enqueue.emit(item)

    def playqueue_remove(self, index):
        self.dequeue.emit(index)


class MPVPlayer(plexdesktop.components.ComponentObject):
    working = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    play_item = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    add_item = QtCore.pyqtSignal(plexdevices.media.BaseObject)

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        s = plexdesktop.settings.Settings()

        self.title = 'mpvplayer'
        # MPV setup
        self.mpv = PlexMpv(
            parent=self,
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
                # 'script-opts': 'osc-hidetimeout=5000,osc-fadeduration=400,'
                #                'osc-seekbarstyle=bar,osc-vidscale=no',
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
                # 'cache-backbuffer': 10 * 1024,
                # 'cache-default': 10 * 1024,
                # 'demuxer-max-bytes': 25 * 1024 * 1024,
                # hardware decoding
                # 'hwdec': 'auto',
                'volume': float(s.value('last_volume', 0.0))
            },
            observe=[
                'pause',  # for timeline updates
                'playback-time',  # for timeline updates
                'playlist',
                'playlist-pos'  # for syncing the playqueue with mpv playlist
            ]
        )

        # Restore saved volume
        last_vol = float(s.value('last_volume', 0.0))
        # self.volume = last_vol

        self.mpv.shutdown_complete.connect(self._shutdown)
        self.mpv.working.connect(self.working)
        self.mpv.finished.connect(self.finished)
        self.play_item.connect(self.mpv.play)
        self.add_item.connect(self.mpv.playqueue_add)

    def play(self, media_object):
        self.title = plexdesktop.utils.title(media_object)
        self.play_item.emit(media_object)

    def queue(self, media_object):
        self.add_item.emit(media_object)
