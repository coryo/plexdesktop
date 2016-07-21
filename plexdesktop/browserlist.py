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
import PyQt5.QtGui
import PyQt5.QtCore

import plexdesktop.components
import plexdesktop.utils
import plexdesktop.workers
import plexdesktop.extra_widgets
import plexdesktop.delegates

logger = logging.getLogger('plexdesktop')
Qt = PyQt5.QtCore.Qt


class ListModel(PyQt5.QtCore.QAbstractListModel):
    work_container = PyQt5.QtCore.pyqtSignal(plexdevices.device.Device, str, int, int, str, dict)
    work_thumbs = PyQt5.QtCore.pyqtSignal(queue.Queue)

    new_item = PyQt5.QtCore.pyqtSignal(PyQt5.QtCore.QModelIndex)
    new_container_titles = PyQt5.QtCore.pyqtSignal(str, str)
    new_container = PyQt5.QtCore.pyqtSignal()
    new_page = PyQt5.QtCore.pyqtSignal()
    new_thumbs = PyQt5.QtCore.pyqtSignal()

    working = PyQt5.QtCore.pyqtSignal()
    done = PyQt5.QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None
        self.thumb_queue = queue.Queue()

        self.container_thread = PyQt5.QtCore.QThread(self)
        self.thumb_thread = PyQt5.QtCore.QThread(self)

        self.container_worker = plexdesktop.workers.ContainerWorker()
        self.thumb_worker = plexdesktop.workers.QueueThumbWorker()

        self.container_worker.moveToThread(self.container_thread)
        self.thumb_worker.moveToThread(self.thumb_thread)

        self.container_worker.result_ready.connect(self._add_container)
        self.container_worker.finished.connect(self._done)

        self.thumb_worker.result_ready.connect(self._update_thumb)
        # self.thumb_worker.finished.connect(DB_THUMB.commit)
        self.thumb_worker.result_ready.connect(self.new_thumbs.emit)

        self.work_container.connect(self.container_worker.run)
        self.work_container.connect(self.working.emit)

        self.work_thumbs.connect(self.thumb_worker.process)

        self.container_thread.start()
        self.thumb_thread.start()

    def quit(self):
        self.container_thread.quit()
        self.container_thread.wait()
        self.thumb_thread.quit()
        self.thumb_thread.wait()

    def clear(self):
        self.beginResetModel()
        self.container = None
        self.endResetModel()

    def _done(self):
        if self.container:
            t1, t2 = self.container.title1, self.container.title2
            self.new_container_titles.emit(t1, t2)
        self.done.emit()

    def _add_container(self, container, page):
        if page == 0:
            self.clear()
            self.beginInsertRows(PyQt5.QtCore.QModelIndex(), 0, len(container) - 1)
            self.container = container
            self.endInsertRows()
            self.page = page
            self.new_container.emit()
        else:
            self.beginInsertRows(PyQt5.QtCore.QModelIndex(), len(self.container),
                                 len(self.container) + len(container) - 1)
            self.container.children += container.children
            self.endInsertRows()
            self.page = page
            self.new_page.emit()

    def _update_thumb(self, img, index, media_item):
        if media_item != self.data(index, Qt.UserRole) or not index.isValid():
            # the list changed while we were getting the thumb, so don't set it.
            return
        self.setData(index, img, role=Qt.DecorationRole)

    def request_thumb(self, index):
        self.thumb_queue.put(index)
        self.work_thumbs.emit(self.thumb_queue)

    def request_thumbs(self, indexes):
        for index in indexes:
            self.thumb_queue.put(index)
        self.work_thumbs.emit(self.thumb_queue)

    def set_container(self, container):
        self.beginResetModel()
        self.container = container
        self.endResetModel()
        self.done.emit()

    def fetch_container(self, server, key, page=0, size=50, sort="", params={}):
        self.server = server
        self.key = key
        self.container_size = size
        self.sort = sort
        self.params = params
        self.work_container.emit(server, key, page, size, sort, params)

    def rowCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return 0 if self.container is None else len(self.container)

    def data(self, index, role=Qt.DisplayRole):
        if self.container is None:
            return PyQt5.QtCore.QVariant()
        if role == Qt.DisplayRole:
            try:
                return self.container.children[index.row()].title
            except (AttributeError, IndexError):
                return None
        elif role == Qt.UserRole:
            try:
                return self.container.children[index.row()]
            except IndexError:
                return None
        elif role == Qt.DecorationRole:
            try:
                img = self.container.children[index.row()].user_data
            except (AttributeError, IndexError):
                img = PyQt5.QtGui.QPixmap()
            return img

    def setData(self, index, value, role):
        if index.data(role=Qt.UserRole) is None:
            return False
        if role == Qt.DecorationRole:
            index.data(role=Qt.UserRole).user_data = value
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            return True
        elif role == Qt.UserRole:
            self.dataChanged.emit(index, index)
            return True

    def canFetchMore(self, index):
        return (False if self.container is None or not len(self.container) else
                len(self.container) < self.container.total_size)

    def fetchMore(self, parent):
        self.page += 1
        self.work_container.emit(self.server, self.key, self.page, self.container_size,
                                 self.sort, self.params)

    def has_thumb(self, index):
        try:
            return self.container.children[index.row()].user_data is not None
        except (AttributeError, IndexError):
            return False


class PlaylistView(PyQt5.QtWidgets.QListView):
    itemSelectionChanged = PyQt5.QtCore.pyqtSignal(list)
    request_thumb = PyQt5.QtCore.pyqtSignal(object)
    request_thumbs = PyQt5.QtCore.pyqtSignal(object)
    play = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    remove = PyQt5.QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ListModel(self)
        self.setModel(self._model)
        self.list_delegate = plexdesktop.delegates.ListDelegate(self)
        self.setItemDelegate(self.list_delegate)
        self.setSelectionMode(PyQt5.QtWidgets.QAbstractItemView.MultiSelection)
        self.setResizeMode(PyQt5.QtWidgets.QListView.Adjust)
        self.icon_size(32)
        self.setAlternatingRowColors(True)
        self.doubleClicked.connect(self.double_click)
        self.request_thumb.connect(self.model().request_thumb)
        self.request_thumbs.connect(self.model().request_thumbs)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def quit(self):
        self.model().quit()

    def set_container(self, container):
        self.model().set_container(container)
        indexes = (self.model().index(i) for i in range(self.model().rowCount()))
        self.request_thumbs.emit(indexes)

    def icon_size(self, x):
        self.last_icon_size = PyQt5.QtCore.QSize(x, x)
        self.setIconSize(self.last_icon_size)

    def currentItem(self):
        indexes = self.selectedIndexes()
        if indexes:
            return [indexes[0].data(role=Qt.UserRole)]

    def currentItems(self):
        indexes = self.selectedIndexes()
        return [index.data(role=Qt.UserRole) for index in indexes]
        if indexes:
            return [indexes[0].data(role=Qt.UserRole)]

    def double_click(self, index):
        self.play.emit(index.data(role=Qt.UserRole))

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        media = [index.data(role=Qt.UserRole) for index in selected.indexes()]
        self.itemSelectionChanged.emit(media)

    def context_menu(self, pos):
        items = self.currentItems()
        if not items:
            return
        menu = PyQt5.QtWidgets.QMenu(self)
        if len(items) == 1:
            play = PyQt5.QtWidgets.QAction('Play', menu)
            play.triggered.connect(self.cm_play_item)
            play.setData(items[0])
            menu.addAction(play)
        remove = PyQt5.QtWidgets.QAction('Remove', menu)
        remove.triggered.connect(self.cm_remove_item)
        remove.setData(items)
        menu.addAction(remove)
        if not menu.isEmpty():
            menu.exec_(PyQt5.QtGui.QCursor.pos())

    def cm_play_item(self):
        self.play.emit(self.sender().data())

    def cm_remove_item(self):
        self.remove.emit(self.sender().data())


class ListView(PyQt5.QtWidgets.QListView):
    viewModeChanged = PyQt5.QtCore.pyqtSignal()
    itemDoubleClicked = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    itemSelectionChanged = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    container_request = PyQt5.QtCore.pyqtSignal(plexdevices.device.Device, str, int, int, str, dict)
    request_thumb = PyQt5.QtCore.pyqtSignal(object)
    request_thumbs = PyQt5.QtCore.pyqtSignal(object)
    goto_location = PyQt5.QtCore.pyqtSignal(plexdesktop.utils.Location)
    queue = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    play = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    photo = PyQt5.QtCore.pyqtSignal(plexdevices.media.Photo)
    working = PyQt5.QtCore.pyqtSignal()
    finished = PyQt5.QtCore.pyqtSignal()
    image_selection = PyQt5.QtCore.pyqtSignal(plexdevices.media.Photo)
    metadata_selection = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject)
    new_titles = PyQt5.QtCore.pyqtSignal(str, str)
    download = PyQt5.QtCore.pyqtSignal(plexdevices.media.BaseObject, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ListModel(self)
        self.setModel(self._model)
        self._last_count = 0
        # self._player_state, self._photo_viewer_state = False, False
        self.list_delegate = plexdesktop.delegates.ListDelegate(self)
        self.tile_delegate = plexdesktop.delegates.TileDelegate(self)
        self.setItemDelegate(self.list_delegate)
        self.setSelectionMode(PyQt5.QtWidgets.QAbstractItemView.SingleSelection)
        self.setResizeMode(PyQt5.QtWidgets.QListView.Adjust)
        self.icon_size(32)
        self.setAlternatingRowColors(True)

        self.doubleClicked.connect(self.double_click)
        self.container_request.connect(self.model().fetch_container)
        self.verticalScrollBar().valueChanged.connect(self.visibleItemsChanged)
        self.request_thumb.connect(self.model().request_thumb)
        self.request_thumbs.connect(self.model().request_thumbs)
        self.customContextMenuRequested.connect(self.context_menu)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        self.itemSelectionChanged.connect(self.selection_changed)
        # Model signals
        self.model().done.connect(self.visibleItemsChanged)
        self.model().working.connect(self.working.emit)
        self.model().done.connect(self.finished.emit)
        self.model().new_container_titles.connect(self.new_titles.emit)
        self.model().new_thumbs.connect(self._resize)

        self.viewModeChanged.connect(self.visibleItemsChanged)

        self._resize_hack = True

    def quit(self):
        self.model().quit()

    def _resize(self):
        if self.viewMode() == PyQt5.QtWidgets.QListView.ListMode:
            return
        self.resize(self.width() + 1 if self._resize_hack else self.width() - 1, self.height())
        self._resize_hack = not self._resize_hack
        # self.updateGeometry()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        self.visible_items()
        return super().resizeEvent(event)

    def clear(self):
        self.model().clear()

    def toggle_view_mode(self):
        if self.viewMode() == PyQt5.QtWidgets.QListView.ListMode:
            self.setItemDelegate(self.tile_delegate)
            self.setViewMode(PyQt5.QtWidgets.QListView.IconMode)
            self.bg_vertical = True
            self.setSpacing(4)
        else:
            self.setItemDelegate(self.list_delegate)
            self.setViewMode(PyQt5.QtWidgets.QListView.ListMode)
            self.bg_vertical = False
            self.setSpacing(0)
        self.setAlternatingRowColors(not self.bg_vertical)
        self.viewModeChanged.emit()

    def icon_size(self, x):
        self.last_icon_size = PyQt5.QtCore.QSize(x, x)
        self.setIconSize(self.last_icon_size)
        self.visibleItemsChanged()

    def add_container(self, server, key, page=0, size=50, sort=None, params=None):
        self.container_request.emit(server, key, page, size,
                                    sort if sort is not None else '',
                                    params if params is not None else {})

    def double_click(self, index):
        self.itemDoubleClicked.emit(index.data(role=Qt.UserRole))

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        try:
            self.itemSelectionChanged.emit(selected.indexes()[0].data(role=Qt.UserRole))
        except IndexError:
            pass

    def currentItem(self):
        return self.currentIndex().data(role=Qt.UserRole)

    def moveCursor(self, cursorAction, modifiers):
        index = self.currentIndex()
        if cursorAction == PyQt5.QtWidgets.QAbstractItemView.MoveNext:
            i = self.model().index(index.row() + 1, index.column())
            return i if i.isValid() else self.model().index(0, 0)
        elif cursorAction == PyQt5.QtWidgets.QAbstractItemView.MovePrevious:
            i = self.model().index(index.row() - 1, index.column())
            return i if i.isValid() else self.model().index(0, 0)
        return super().moveCursor(cursorAction, modifiers)

    def next_item(self):
        index = self.moveCursor(PyQt5.QtWidgets.QAbstractItemView.MoveNext, Qt.NoModifier)
        self.setCurrentIndex(index)

    def prev_item(self):
        index = self.moveCursor(PyQt5.QtWidgets.QAbstractItemView.MovePrevious, Qt.NoModifier)
        self.setCurrentIndex(index)

    def visibleItemsChanged(self):
        self.visible_items()

    def visible_items(self):
        model = self.model()
        if not model.rowCount():
            return (0, [])

        rect = self.rect()
        visible = []

        start = self.indexAt(PyQt5.QtCore.QPoint(15, 15))
        for i in range(start.row() if start.isValid() else 0, model.rowCount()):
            index = model.index(i)
            if rect.intersects(self.visualRect(index)):
                visible.append(index)
            else:
                if visible:
                    break
        self.request_thumbs.emit(visible)

    def preferences_prompt(self, item):
        dialog = plexdesktop.extra_widgets.PreferencesObjectDialog(item, parent=self)

    def search_prompt(self, item):
        text, ok = PyQt5.QtWidgets.QInputDialog.getText(self, 'Search', 'query:')
        if ok:
            self.goto_location.emit(plexdesktop.utils.Location(item.key, params={'query': text}))

    def item_double_clicked(self, item):
        if isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.InputDirectory):
                self.search_prompt(item)
            elif isinstance(item, plexdevices.media.PreferencesDirectory):
                self.preferences_prompt(item)
            else:
                self.goto_location.emit(plexdesktop.utils.Location(item.key))
        elif isinstance(item, plexdevices.media.MediaItem):
            if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode,
                                 plexdevices.media.VideoClip, plexdevices.media.Track)):
                self.play.emit(item)
            elif isinstance(item, plexdevices.media.Photo):
                self.photo.emit(item)

    def selection_changed(self):
        m = self.currentItem()
        if m is None:
            return
        logger.debug(repr(m))
        if isinstance(m, (plexdevices.media.MediaItem, plexdevices.media.MediaDirectory)):
            if isinstance(m, plexdevices.media.Photo):
                self.image_selection.emit(m)
            self.metadata_selection.emit(m)

    def context_menu(self, pos):
        index = self.currentIndex()
        item = index.data(role=Qt.UserRole)
        if item is None:
            return
        data = (item, index)
        menu = PyQt5.QtWidgets.QMenu(self)
        actions = []
        if isinstance(item, plexdevices.media.MediaItem):
            if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode,
                                 plexdevices.media.VideoClip, plexdevices.media.Track)):
                main_action = PyQt5.QtWidgets.QAction('Play', menu)
                main_action.triggered.connect(self.cm_play)
                actions.append(main_action)
                if item.container.is_library:#plexdesktop.components.ComponentManager.Instance().exists('video_player') and item.container.is_library:
                    append_action = PyQt5.QtWidgets.QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)
            elif isinstance(item, plexdevices.media.Photo):
                main_action = PyQt5.QtWidgets.QAction('View Photo', menu)
                main_action.triggered.connect(self.cm_play_photo)
                actions.append(main_action)
            copy_action = PyQt5.QtWidgets.QAction('Copy url', menu)
            copy_action.triggered.connect(self.cm_copy)
            actions.append(copy_action)
            save_action = PyQt5.QtWidgets.QAction('Download', menu)
            save_action.triggered.connect(self.cm_save_item)
            actions.append(save_action)
        elif isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.PreferencesDirectory):
                main_action = PyQt5.QtWidgets.QAction('Open', menu)
                main_action.triggered.connect(self.cm_settings)
                actions.append(main_action)
            else:
                main_action = PyQt5.QtWidgets.QAction('Open', menu)
                main_action.triggered.connect(self.cm_open)
                actions.append(main_action)
            if isinstance(item, (plexdevices.media.Show, plexdevices.media.Season,
                                 plexdevices.media.Album, plexdevices.media.Artist)):
                action = PyQt5.QtWidgets.QAction('Play all', menu)
                action.triggered.connect(self.cm_play)
                actions.append(action)
                if item.container.is_library:# plexdesktop.components.ComponentManager.Instance().exists('video_player') and item.container.is_library:
                    append_action = PyQt5.QtWidgets.QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)

        if item.markable:
            mark_action = PyQt5.QtWidgets.QAction('Mark unwatched', menu)
            mark_action.triggered.connect(self.cm_mark_unwatched)
            mark_action2 = PyQt5.QtWidgets.QAction('Mark watched', menu)
            mark_action2.triggered.connect(self.cm_mark_watched)
            actions.append(mark_action)
            actions.append(mark_action2)

        if item.has_parent:
            open_action = PyQt5.QtWidgets.QAction('goto: ' + plexdevices.types.get_type_string(item.parent_type), menu)
            open_action.triggered.connect(self.cm_open_parent)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = PyQt5.QtWidgets.QAction('goto: ' + plexdevices.types.get_type_string(item.grandparent_type), menu)
            open_action.triggered.connect(self.cm_open_grandparent)
            actions.append(open_action)

        for action in actions:
            action.setData(data)
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(PyQt5.QtGui.QCursor.pos())

    def cm_queue(self):
        self.queue.emit(self.sender().data()[0])

    def cm_copy(self):
        url = self.sender().data()[0].resolve_url()
        PyQt5.QtWidgets.QApplication.clipboard().setText(url)

    def cm_settings(self):
        self.preferences_prompt(self.sender().data()[0])

    def cm_play(self):
        self.play.emit(self.sender().data()[0])

    def cm_play_photo(self):
        self.photo.emit(self.sender().data()[0])

    def cm_open(self):
        self.goto_location.emit(plexdesktop.utils.Location(self.sender().data()[0].key))

    def cm_open_parent(self):
        self.goto_location.emit(plexdesktop.utils.Location(self.sender().data()[0].parent_key + '/children'))

    def cm_open_grandparent(self):
        self.goto_location.emit(plexdesktop.utils.Location(self.sender().data()[0].grandparent_key + '/children'))

    def cm_mark_watched(self):
        item, index = self.sender().data()
        item.mark_watched()
        index.model().setData(index, None, Qt.UserRole)

    def cm_mark_unwatched(self):
        item, index = self.sender().data()
        item.mark_unwatched()
        index.model().setData(index, None, Qt.UserRole)

    def cm_save_item(self):
        item = self.sender().data()[0]
        save_dir = PyQt5.QtWidgets.QFileDialog.getExistingDirectory(self, 'Open Directory')
        if save_dir:
            self.download.emit(item, save_dir)

    # def player_state(self, state):
    #     self._player_state = state

    # def photo_viewer_state(self, state):
    #     self._photo_viewer_state = state
