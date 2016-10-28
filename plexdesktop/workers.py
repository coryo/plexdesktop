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
import time

import requests
import plexdevices

from PyQt5 import QtCore, QtGui

import plexdesktop.sqlcache
from plexdesktop.settings import Settings

logger = logging.getLogger('plexdesktop')


class ContainerWorker(QtCore.QObject):
    result_ready = QtCore.pyqtSignal(plexdevices.media.MediaContainer)
    container_updated = QtCore.pyqtSignal(plexdevices.media.MediaContainer, int)
    finished = QtCore.pyqtSignal()

    def run(self, server, key, page=0, size=20, sort="", params={}):
        logger.debug(('ContainerWorker: fetching container: key={}, server={}, '
                      'page={}, size={}, sort={}, params={}').format(key, server, page,
                                                                     size, sort, params))
        p = {} if not sort else {'sort': sort}
        if params:
            p.update(params)
        try:
            container = server.media_container(key, size, page, p, timeout=5)
        except (ConnectionError, requests.exceptions.RequestException) as e:
            logger.error('ContainerWorker: {}, {}'.format(repr(e), e))
        else:
            self.result_ready.emit(container)
        self.finished.emit()

    def fetch_more(self, container):
        start_len = len(container)
        try:
            container.fetch_more()
        except (ConnectionError, requests.exceptions.RequestException) as e:
            logger.error('ContainerWorker: fetch_more(): {}'.format(e))
        else:
            self.container_updated.emit(container, len(container) - start_len)
        self.finished.emit()

    # def fetch_next_page_object(self, container):
    #     start_len = len(container)
    #     try:
    #         container.fetch_next_page_object()
    #     except (ConnectionError, requests.exceptions.RequestException) as e:
    #         logger.error('ContainerWorker: fetch_more(): {}'.format(e))
    #     else:
    #         self.container_updated.emit(container, len(container) - start_len)
    #     self.finished.emit()


class HubWorker(QtCore.QObject):
    result_ready = QtCore.pyqtSignal(plexdevices.hubs.HubsContainer)
    finished = QtCore.pyqtSignal()

    def run(self, server, key, params={}):
        logger.debug(('HubWorker: fetching container: key={}'.format(key)))
        try:
            hub = server.hub(key, params=params)
        except (ConnectionError, requests.exceptions.RequestException) as e:
            logger.error('HubWorker: ' + str(e))
        else:
            logger.debug('HubWorker: url=' + server.active.url)
            self.result_ready.emit(hub)
        self.finished.emit()


class ImageWorker(QtCore.QObject):
    signal = QtCore.pyqtSignal(QtCore.QByteArray)

    def run(self, photo_object):
        url = photo_object.media[0].parts[0].resolve_key()
        logger.info('ImageWorker: ' + url)
        with plexdesktop.sqlcache.db_image() as cache:
            if url in cache:
                img_data = cache[url]
            else:
                try:
                    res = photo_object.container.server.image(url)
                except (ConnectionError, requests.exceptions.RequestException) as e:
                    logger.error('ImageWorker: {}'.format(e))
                    return
                else:
                    img_data = res.content
                    cache[url] = img_data
        self.signal.emit(QtCore.QByteArray(img_data))


# class ThumbTask(QtCore.QRunnable):

#     def __init__(self, receiver, item, row):
#         super().__init__()
#         self.receiver = receiver
#         self.item = item
#         self.row = row
#         self.setAutoDelete(True)
#         self.thumb_size = 240

#     def run(self):
#         if not self.item:
#             return
#         url = self.item.thumb
#         if not url:
#             return
#         img = QtGui.QPixmapCache.find(url)
#         if img:
#             return
#         with plexdesktop.sqlcache.db_thumb() as cache:
#             if url in cache:
#                 img_data = cache[url]
#             else:  # not in cache, fetch from server
#                 try:
#                     if self.item.container.is_library:
#                         res = self.item.container.server.image(
#                             url, self.thumb_size, self.thumb_size, timeout=5)
#                     else:
#                         res = self.item.container.server.image(url, timeout=5)
#                 except (ConnectionError, requests.exceptions.RequestException) as e:
#                     logger.error('QueueThumbWorker: {}'.format(e))
#                     return
#                 else:
#                     img_data = res.content
#                     cache[url] = img_data
#             img = QtGui.QPixmap()
#             img.loadFromData(img_data)
#             QtGui.QPixmapCache.insert(url, img)
#             QtCore.QMetaObject.invokeMethod(
#                 self.receiver,
#                 "_update_thumb",
#                 QtCore.Qt.QueuedConnection,
#                 QtCore.Q_ARG(int, self.row),
#                 QtCore.Q_ARG(object, self.item)
#             )


class QueueThumbWorker(QtCore.QObject):
    result_ready = QtCore.pyqtSignal(int, plexdevices.media.BaseObject)
    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        s = Settings()
        self.thumb_size = int(s.value('thumb_size', 240))

    def get_thumb(self, item, row):
        if not item:
            return
        url = item.thumb
        if not url:
            return
        img = QtGui.QPixmapCache.find(url)
        if img:
            return
        with plexdesktop.sqlcache.db_thumb() as cache:
            if url in cache:
                img_data = cache[url]
            else:  # not in cache, fetch from server
                try:
                    if item.container.is_library:
                        res = item.container.server.image(
                            url, self.thumb_size, self.thumb_size, timeout=5)
                    else:
                        res = item.container.server.image(url, timeout=5)
                except (ConnectionError, requests.exceptions.RequestException) as e:
                    logger.error('QueueThumbWorker: {}'.format(e))
                    return
                else:
                    img_data = res.content
                    cache[url] = img_data

            img = QtGui.QPixmap()
            img.loadFromData(img_data)
            QtGui.QPixmapCache.insert(url, img)
            self.result_ready.emit(row, item)

    def process(self, queue):
        """Load images into the QPixmapCache"""
        s = Settings()
        thumb_size = int(s.value('thumb_size', 200))
        cache = plexdesktop.sqlcache.db_thumb()
        # while True:
        for (media_object, row) in iter(queue.get, None):
            if not media_object:
                continue
            url = media_object.thumb
            if not url:
                continue
            if url in cache:
                img_data = cache[url]
            else:  # not in cache, fetch from server
                try:
                    if media_object.container.is_library:
                        res = media_object.container.server.image(
                            url, thumb_size, thumb_size, timeout=5)
                    else:
                        res = media_object.container.server.image(url, timeout=5)
                except (ConnectionError, requests.exceptions.RequestException) as e:
                    logger.error('QueueThumbWorker: {}'.format(e))
                    cache.close()
                    continue
                else:
                    img_data = res.content
                    cache[url] = img_data

            img = QtGui.QPixmap()
            img.loadFromData(img_data)
            QtGui.QPixmapCache.insert(url, img)
            self.result_ready.emit(row, media_object)
        # cache.close()


class DownloadJob(QtCore.QObject):
    def __init__(self, mutex, item, destination, parent=None):
        super().__init__(parent)
        self.id = hash(item)
        self.item = item
        self.destination = destination
        self.cancelled = False
        self.paused = False
        self._pause = QtCore.QWaitCondition()

        self.thread = QtCore.QThread()
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


class DownloadWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(DownloadJob, int, int)
    canceled = QtCore.pyqtSignal(DownloadJob)
    complete = QtCore.pyqtSignal(DownloadJob)
    paused = QtCore.pyqtSignal(DownloadJob)

    def __init__(self, mutex, parent=None):
        super().__init__(parent)
        self.mutex = mutex

    def download_file(self, queue, block_size=8192):
        locker = QtCore.QMutexLocker(self.mutex)
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
