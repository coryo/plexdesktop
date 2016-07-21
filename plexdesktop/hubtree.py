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
import queue

import plexdevices

import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.QtGui

import plexdesktop.utils
import plexdesktop.workers
import plexdesktop.sqlcache
import plexdesktop.delegates

logger = logging.getLogger('plexdesktop')
Qt = PyQt5.QtCore.Qt


class TreeItem(object):

    def __init__(self, plex_item=None, parent=None):
        self.child_items = []
        self.parent = parent
        self.plex_item = plex_item
        self.thumb = None

    def appendChild(self, item):
        self.child_items.append(item)

    def child(self, row):
        return self.child_items[row]

    def childCount(self):
        return len(self.child_items)

    def columnCount(self):
        return 1

    def data(self, column):
        try:
            return [
                plexdesktop.utils.hub_title(self.plex_item),  # display title
            ][column]
        except Exception:
            return None

    def row(self):
        return self.parent.child_items.index(self) if self.parent is not None else 0

    def parentItem(self):
        return self.parent


class TreeModel(PyQt5.QtCore.QAbstractItemModel):
    work_thumbs = PyQt5.QtCore.pyqtSignal(queue.Queue)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.root_item = TreeItem()
        self.setupModelData(data, self.root_item)
        # self._thumb_queue = {}
        # self._parent = parent
        self._thumb_queue = queue.Queue()
        self._thumb_thread = PyQt5.QtCore.QThread(self)
        self._thumb_worker = plexdesktop.workers.QueueThumbWorker()
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_worker.result_ready.connect(self._update_thumb)
        self._thumb_worker.finished.connect(plexdesktop.sqlcache.DB_THUMB.commit)
        self.work_thumbs.connect(self._thumb_worker.process)
        self._thumb_thread.start()

    def quit(self):
        self._thumb_thread.quit()
        self._thumb_thread.wait()

    def clear(self):
        self.beginResetModel()
        self.root_item = TreeItem()
        self.endResetModel()

    def index(self, row, column, parent=PyQt5.QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return PyQt5.QtCore.QModelIndex()
        parent_item = (self.root_item if not parent.isValid() else
                       parent.internalPointer())
        child_item = parent_item.child(row)
        return self.createIndex(row, column, child_item) if child_item else PyQt5.QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return PyQt5.QtCore.QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parentItem()

        if parent_item == self.root_item:
            return PyQt5.QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=PyQt5.QtCore.QModelIndex()):
        if parent.column() > 0:
            return 0
        parent_item = (self.root_item if not parent.isValid() else
                       parent.internalPointer())
        return parent_item.childCount()

    def total_rows(self):
        count = self.rowCount()
        return count + sum((self.rowCount(self.index(i, 0)) for i in range(count)))

    def columnCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return (parent.internalPointer().columnCount() if parent.isValid() else
                self.root_item.columnCount())

    def data(self, index, role):
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        if role == Qt.UserRole:
            return index.internalPointer().plex_item
        elif role == Qt.DisplayRole:
            return index.internalPointer().data(index.column())
        elif role == Qt.DecorationRole:
            return index.internalPointer().thumb
        else:
            return PyQt5.QtCore.QVariant()

    def flags(self, index):
        return 0 if not index.isValid() else super().flags(index)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_item.data(section)
        return PyQt5.QtCore.QVariant()

    def setupModelData(self, data, parent):
        parents = [parent]
        for item in data.children:
            if isinstance(item, plexdevices.hubs.Hub):
                if not len(item.children):
                    continue
                hub = TreeItem(item, parents[-1])
                parents[-1].appendChild(hub)
                for child in item.children:
                    if child.has_reason:
                        if child.reason == 'actor':
                            reason = 'with {}'.format(child.reason_title)
                        elif child.reason == 'director':
                            reason = 'directed by {}'.format(child.reason_title)
                        else:
                            reason = ''
                    else:
                        reason = ''
                    hub.appendChild(TreeItem(child, hub))
            else:
                self.root_item.appendChild(TreeItem(item, self.root_item))

    def setData(self, index, value, role):
        if role == Qt.DecorationRole:
            index.internalPointer().thumb = value.scaledToWidth(super().parent().iconSize().width(), Qt.SmoothTransformation)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            return True
        else:
            return False

    def request_thumbs(self):
        root_indexes = [self.index(i, 0) for i in range(self.rowCount())]
        indexes = root_indexes
        for index in root_indexes:
            indexes += [self.index(x, 0, parent=index) for x in range(index.internalPointer().childCount())]

        queue = (i for i in indexes if not isinstance(i.data(role=Qt.UserRole), plexdevices.hubs.Hub))
        for index in queue:
            self._thumb_queue.put(index)
        self.work_thumbs.emit(self._thumb_queue)

    def _update_thumb(self, img, index, media_item):
        if media_item != self.data(index, Qt.UserRole) or not index.isValid():
            return
        self.setData(index, img, role=Qt.DecorationRole)

    def has_thumb(self, index):
        return index.internalPointer().thumb is not None


class TreeView(PyQt5.QtWidgets.QTreeView):
    request_container = PyQt5.QtCore.pyqtSignal(plexdevices.device.Device, str, dict)
    goto_location = PyQt5.QtCore.pyqtSignal(plexdesktop.utils.Location)
    goto_hub = PyQt5.QtCore.pyqtSignal(plexdevices.hubs.Hub)
    finished = PyQt5.QtCore.pyqtSignal()
    play = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    play_photo = PyQt5.QtCore.pyqtSignal(plexdevices.media.Photo)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.setItemsExpandable(False)
        self.doubleClicked.connect(self.double_click)
        self.setIconSize(PyQt5.QtCore.QSize(36, 36))
        self.setAlternatingRowColors(True)
        self.setIndentation(10)
        self._model = None

        self._worker_thread = PyQt5.QtCore.QThread(self)
        self._worker = plexdesktop.workers.HubWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker.result_ready.connect(self._add_container)
        self.request_container.connect(self._worker.run)
        self._worker_thread.start()
        self.delegate = plexdesktop.delegates.ListDelegate(self)
        self.setItemDelegate(self.delegate)
        self.goto_hub.connect(self.load_hub)

    def quit(self):
        if self.model() is not None:
            self.model().quit()
        self._worker_thread.quit()
        self._worker_thread.wait()

    def clear(self):
        if self.model():
            self.model().clear()

    def current_item(self):
        indexes = self.selectedIndexes()
        if indexes:
            return indexes[0].data(role=Qt.UserRole)

    def double_click(self, index):
        item = index.data(role=Qt.UserRole)
        if isinstance(item, plexdevices.hubs.Hub):
            logger.debug('goto hub')
            self.goto_hub.emit(item)
            return
        if not hasattr(item, 'key'):
            return
        if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode, plexdevices.media.Track)):
            self.play.emit(item)
        elif isinstance(item, plexdevices.media.Photo):
            self.play_photo.emit(item)
        else:
            loc = plexdesktop.utils.Location(item.key)
            self.goto_location.emit(loc)

    def context_menu(self, pos):
        item = self.current_item()
        logger.debug(item)

        if isinstance(item, plexdevices.hubs.Hub):
            return

        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if isinstance(item, plexdevices.media.MediaItem):
            action = PyQt5.QtWidgets.QAction('play', menu)
            action.setData(item)
            if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode, plexdevices.media.Track)):
                action.triggered.connect(self.cm_play)
            elif isinstance(item, plexdevices.media.Photo):
                action.triggered.connect(self.cm_play_photo)
            actions.append(action)
        elif isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.Album):
                action = PyQt5.QtWidgets.QAction('play all', menu)
                action.setData(item)
                action.triggered.connect(self.cm_play)
                actions.append(action)

            if hasattr(item, 'key'):
                action = PyQt5.QtWidgets.QAction('go', menu)
                action.triggered.connect(self.cm_goto)
                action.setData(plexdesktop.utils.Location(item.key))
                actions.append(action)

        if not isinstance(item, plexdevices.media.Photo):
            if hasattr(item, 'parent_key'):
                action = PyQt5.QtWidgets.QAction('goto: ' + plexdevices.types.get_type_string(item.parent_type), menu)
                action.triggered.connect(self.cm_goto)
                action.setData(plexdesktop.utils.Location(item.parent_key + '/children'))
                actions.append(action)
            if hasattr(item, 'grandparent_key'):
                action = PyQt5.QtWidgets.QAction('goto: ' + plexdevices.types.get_type_string(item.grandparent_type), menu)
                action.triggered.connect(self.cm_goto)
                action.setData(plexdesktop.utils.Location(item.grandparent_key + '/children'))
                actions.append(action)

        for action in actions:
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(PyQt5.QtGui.QCursor.pos())

    @PyQt5.QtCore.pyqtSlot()
    def cm_play(self):
        self.play.emit(self.sender().data())

    @PyQt5.QtCore.pyqtSlot()
    def cm_play_photo(self):
        self.play_photo.emit(self.sender().data())

    @PyQt5.QtCore.pyqtSlot(bool)
    def cm_goto(self, state):
        loc = self.sender().data()
        self.goto_location.emit(loc)

    @PyQt5.QtCore.pyqtSlot(plexdevices.device.Server, str)
    def search(self, server, query):
        self.request_container.emit(server, '/hubs/search', {'query': query})
        self.setWindowTitle('Search Results: {}'.format(query))

    @PyQt5.QtCore.pyqtSlot(plexdevices.hubs.Hub)
    def load_hub(self, hub):
        self.goto(hub.container.server, hub.key)

    @PyQt5.QtCore.pyqtSlot(plexdevices.device.Server, str, dict)
    def goto(self, server, key, params=None):
        logger.debug('{} {}'.format(server, key))
        if key:
            self.request_container.emit(server, key, {})

    @PyQt5.QtCore.pyqtSlot(plexdevices.hubs.HubsContainer)
    def _add_container(self, container):
        self._model = TreeModel(container, self)
        self.setModel(self._model)
        self.header().hide()
        self.expandAll()

        rows = self._model.total_rows()
        logger.debug('Hub tree items: {}'.format(rows))
        if rows:
            self.model().request_thumbs()
        self.finished.emit()
