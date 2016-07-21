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
import hashlib
import logging
import time

import requests
import plexdevices

import PyQt5.QtCore
import PyQt5.QtGui

import plexdesktop.sqlcache
from plexdesktop.settings import Settings

logger = logging.getLogger('plexdesktop')
Qt = PyQt5.QtCore.Qt


class ContainerWorker(PyQt5.QtCore.QObject):
    result_ready = PyQt5.QtCore.pyqtSignal(plexdevices.media.MediaContainer, int)
    finished = PyQt5.QtCore.pyqtSignal()

    def run(self, server, key, page=0, size=20, sort="", params={}):
        logger.debug(('BrowserList: fetching container: key={}, server={}, '
                      'page={}, size={}, sort={}, params={}').format(key, server, page,
                                                                     size, sort, params))
        p = {} if not sort else {'sort': sort}
        if params:
            p.update(params)
        try:
            data = server.container(key, page=page, size=size, params=p)
        except plexdevices.DeviceConnectionsError as e:
            logger.error('BrowserList: ' + str(e))
        else:
            logger.debug('BrowserList: url=' + server.active.url)
            container = plexdevices.media.MediaContainer(server, data)
            self.result_ready.emit(container, page)
        self.finished.emit()


class HubWorker(PyQt5.QtCore.QObject):
    result_ready = PyQt5.QtCore.pyqtSignal(plexdevices.hubs.HubsContainer)
    finished = PyQt5.QtCore.pyqtSignal()

    def run(self, server, key, params={}):
        logger.debug(('BrowserList: fetching container: key={}'.format(key)))
        try:
            data = server.hub(key, params=params)
        except plexdevices.DeviceConnectionsError as e:
            logger.error('BrowserList: ' + str(e))
        else:
            logger.debug('BrowserList: url=' + server.active.url)
            self.result_ready.emit(data)
        self.finished.emit()


class ImageWorker(PyQt5.QtCore.QObject):
    signal = PyQt5.QtCore.pyqtSignal(bytes)

    def run(self, photo_object):
        url = photo_object.media[0].parts[0].resolve_key()
        logger.info('ImageWorker: ' + url)
        img_data = plexdesktop.sqlcache.DB_IMAGE[url]
        if img_data is None:
            img_data = photo_object.container.server.image(url)
            plexdesktop.sqlcache.DB_IMAGE[url] = img_data
        plexdesktop.sqlcache.DB_IMAGE.commit()
        self.signal.emit(img_data)


class ThumbWorker(PyQt5.QtCore.QObject):
    result_ready = PyQt5.QtCore.pyqtSignal(PyQt5.QtGui.QPixmap, PyQt5.QtCore.QModelIndex)
    finished = PyQt5.QtCore.pyqtSignal()

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index

    def start(self):
        index = self.index
        media_object = index.data(role=Qt.UserRole)
        if media_object is None:
            self.finished.emit()
            return
        url = media_object.thumb
        if url is None or getattr(media_object, 'user_data', False):
            self.finished.emit()
            return
        # key = media_object.container.server.client_identifier + url
        # key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        img = PyQt5.QtGui.QPixmapCache.find(media_object.key)
        if img is None:
            img_data = plexdesktop.sqlcache.DB_THUMB[url]
            if img_data is None:  # not in cache, fetch from server
                img_data = media_object.container.server.image(url, w=240, h=240)
                plexdesktop.sqlcache.DB_THUMB[url] = img_data
            img = PyQt5.QtGui.QPixmap()
            img.loadFromData(img_data)
            PyQt5.QtGui.QPixmapCache.insert(media_object.key, img)
        self.result_ready.emit(img, index)
        self.finished.emit()


class QueueThumbWorker(PyQt5.QtCore.QObject):
    result_ready = PyQt5.QtCore.pyqtSignal(
        PyQt5.QtGui.QPixmap, PyQt5.QtCore.QModelIndex, plexdevices.media.BaseObject)
    finished = PyQt5.QtCore.pyqtSignal()

    def process(self, queue):
        s = Settings()
        thumb_size = s.value('thumb_size', 240)
        while not queue.empty():
            index = queue.get()
            media_object = index.data(role=Qt.UserRole)
            if media_object is None:
                continue
            url = media_object.thumb
            if url is None or getattr(media_object, 'user_data', False):
                continue
            key = media_object.container.server.client_identifier + url
            key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
            img = PyQt5.QtGui.QPixmapCache.find(key_hash)
            if img is None:
                img_data = plexdesktop.sqlcache.DB_THUMB[url]
                if img_data is None:  # not in cache, fetch from server
                    img_data = media_object.container.server.image(url, w=thumb_size, h=thumb_size)
                    plexdesktop.sqlcache.DB_THUMB[url] = img_data
                img = PyQt5.QtGui.QPixmap()
                img.loadFromData(img_data)
                PyQt5.QtGui.QPixmapCache.insert(key_hash, img)
            queue.task_done()
            self.result_ready.emit(img, index, media_object)
        plexdesktop.sqlcache.DB_THUMB.commit()


class DownloadJob(PyQt5.QtCore.QObject):
    def __init__(self, mutex, item, destination, parent=None):
        super().__init__(parent)
        self.id = hash(item)
        self.item = item
        self.destination = destination
        self.cancelled = False
        self.paused = False
        self._pause = PyQt5.QtCore.QWaitCondition()

        self.thread = PyQt5.QtCore.QThread()
        self.worker = DownloadWorker(mutex)
        self.worker.moveToThread(self.thread)
        self.thread.start()

    def quit(self):
        self.thread.quit()

    def cancel(self):
        self.cancelled = True
        self.resume()

    def pause(self):
        self.paused = True

    def toggle_pause(self):
        if self.paused:
            self.resume()
        else:
            self.paused = True

    def resume(self):
        self.paused = False
        self._pause.wakeAll()


class DownloadWorker(PyQt5.QtCore.QObject):
    progress = PyQt5.QtCore.pyqtSignal(DownloadJob, int, int)
    canceled = PyQt5.QtCore.pyqtSignal(DownloadJob)
    complete = PyQt5.QtCore.pyqtSignal(DownloadJob)
    paused = PyQt5.QtCore.pyqtSignal(DownloadJob)

    def __init__(self, mutex, parent=None):
        super().__init__(parent)
        self.mutex = mutex

    def download_file(self, queue, block_size=8192):
        locker = PyQt5.QtCore.QMutexLocker(self.mutex)
        while not queue.empty():
            job = queue.get()
            url = job.item.resolve_url()
            file_name = job.item.media[0].parts[0].file_name
            full_path = os.path.join(job.destination, file_name)
            if job.paused:
                self.paused.emit(job)
                job._pause.wait(self.mutex)
            if job.cancelled:
                self.canceled.emit(job)
                return
            with open(full_path, 'wb') as f:
                response = requests.get(url, stream=True)
                if not response.ok:
                    return
                file_size = int(response.headers['content-length'])
                start_time = time.clock()
                timer = start_time
                downloaded = 0
                rate = 0
                for block in response.iter_content(block_size):
                    f.write(block)
                    downloaded += len(block)
                    now = time.clock()
                    if now - timer > 0.1:
                        timer = now
                        self.progress.emit(job, downloaded * 100.0 / file_size,
                                           downloaded // (now - start_time))
                        if job.paused:
                            self.paused.emit(job)
                            job._pause.wait(self.mutex)
                        if job.cancelled:
                            self.canceled.emit(job)
                            return
            self.complete.emit(job)
