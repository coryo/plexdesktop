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

import plexdevices

from PyQt5 import QtWidgets, QtCore, QtGui

import plexdesktop.components
import plexdesktop.utils
import plexdesktop.workers
import plexdesktop.extra_widgets
import plexdesktop.delegates

logger = logging.getLogger('plexdesktop')


class ListModel(QtCore.QAbstractListModel):
    work_container = QtCore.pyqtSignal(plexdevices.device.Device,
                                       str, int, int, str, dict)
    work_container_fetch_more = QtCore.pyqtSignal(plexdevices.media.MediaContainer)
    work_container_fetch_next_page = QtCore.pyqtSignal(plexdevices.media.MediaContainer)
    work_thumb = QtCore.pyqtSignal(plexdevices.media.BaseObject, int)
    work_thumbs = QtCore.pyqtSignal(plexdesktop.utils.Queue)

    # new_item = QtCore.pyqtSignal(QtCore.QModelIndex)
    new_container_titles = QtCore.pyqtSignal(str, str)
    new_container = QtCore.pyqtSignal()
    new_page = QtCore.pyqtSignal()

    working = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None

        self.container_thread = QtCore.QThread()
        self.thumb_thread = QtCore.QThread()
        self.container_worker = plexdesktop.workers.ContainerWorker()
        self.thumb_worker = plexdesktop.workers.QueueThumbWorker()
        self.container_worker.moveToThread(self.container_thread)
        self.thumb_worker.moveToThread(self.thumb_thread)

        self.container_worker.result_ready.connect(self._add_container)
        self.container_worker.container_updated.connect(self._update_container)
        self.container_worker.finished.connect(self._done)

        self.thumb_worker.result_ready.connect(self._update_thumb)

        self.work_container.connect(self.container_worker.run)
        self.work_container.connect(self.working.emit)
        self.work_container_fetch_more.connect(self.container_worker.fetch_more)
        self.work_container_fetch_more.connect(self.working.emit)
        # self.work_container_fetch_next_page.connect(self.container_worker.fetch_next_page_object)
        # self.work_container_fetch_next_page.connect(self.working.emit)

        # self.work_thumb.connect(self.thumb_worker.get_thumb)
        self.work_thumbs.connect(self.thumb_worker.process)

        self.thumb_queue = plexdesktop.utils.Queue()

        self.container_thread.start()
        self.thumb_thread.start()
        self.work_thumbs.emit(self.thumb_queue)

    def quit(self):
        self.thumb_queue.clear()
        self.thumb_queue.put(None)

        self.container_thread.quit()
        self.container_thread.wait()
        self.thumb_thread.quit()
        self.thumb_thread.wait()

        self.container_worker.deleteLater()
        self.thumb_worker.deleteLater()
        self.container_thread.deleteLater()
        self.thumb_thread.deleteLater()

    def _done(self):
        if self.container:
            t1, t2 = self.container.title1, self.container.title2
            self.new_container_titles.emit(t1, t2)
        self.done.emit()

    def _add_container(self, container):
        self.container = container
        for i in range(len(self.container)):
            index = self.index(i)
            self._queue_thumb(self.data(index, QtCore.Qt.UserRole), index.row())
        self.endResetModel()
        self.new_container.emit()

    def _update_container(self, container, count):
        for i in range(len(container) - count, len(container)):
            index = self.index(i)
            self._queue_thumb(self.data(index, QtCore.Qt.UserRole), index.row())
        self.endInsertRows()
        self.new_page.emit()

    @QtCore.pyqtSlot(int, object)
    def _update_thumb(self, row, media_item):
        index = self.index(row)
        if media_item == self.data(index, QtCore.Qt.UserRole):
            # delattr(media_item, 'thumb_queued')
            self.setData(index, None, role=QtCore.Qt.DecorationRole)

    def _queue_thumb(self, item, row):
        QtGui.QPixmapCache.insert(item.thumb, QtGui.QPixmap())
        self.thumb_queue.put((item, row))

    def fetch_container(self, server, key, page=0, size=50, sort="", params={}):
        self.thumb_queue.clear()
        self.beginResetModel()
        self.work_container.emit(server, key, page, size, sort, params)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if self.container is None else len(self.container)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if self.container is None:
            return QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            try:
                return self.container.children[index.row()].title
            except (AttributeError, IndexError):
                return QtCore.QVariant()
        elif role == QtCore.Qt.UserRole:
            try:
                return self.container.children[index.row()]
            except IndexError:
                return QtCore.QVariant()
        elif role == QtCore.Qt.DecorationRole:
            row = index.row()
            item = self.container.children[row]
            if hasattr(item, 'thumb_queued'):
                return QtCore.QVariant()
            key = item.thumb
            if not key:
                return plexdesktop.delegates.placeholder_thumb_generator(item.title)
            img = QtGui.QPixmapCache.find(key)
            if img:
                return img
            self._queue_thumb(item, row)
            # QtGui.QPixmapCache.insert(key, QtGui.QPixmap())
            # self.thumb_queue.put((item, row))
            return QtCore.QVariant()
        else:
            return QtCore.QVariant()

    def setData(self, index, value, role):
        if index.data(role=QtCore.Qt.UserRole) is None:
            return False
        if role == QtCore.Qt.DecorationRole:
            self.dataChanged.emit(index, index, [QtCore.Qt.DecorationRole])
            return True
        elif role == QtCore.Qt.UserRole:
            self.dataChanged.emit(index, index)
            return True

    def canFetchMore(self, index):
        if self.container is None or not len(self.container):
            return False
        last_item = self.container.children[-1]
        if isinstance(last_item, plexdevices.media.Directory) and bool(int(last_item.data.get('paging', 0))):
            return True
        return len(self.container) < self.container.total_size

    def fetchMore(self, parent):
        if not self.container:
            return
        last_item = self.container.children[-1]
        if isinstance(last_item, plexdevices.media.Directory) and bool(int(last_item.data.get('paging', 0))):
            self.beginInsertRows(
                QtCore.QModelIndex(),
                len(self.container),
                len(self.container) * 2 - 1
            )
        else:
            self.beginInsertRows(
                QtCore.QModelIndex(),
                len(self.container),
                min(self.container.total_size,
                    len(self.container) + self.container._size) - 1
            )
        self.work_container_fetch_more.emit(self.container)


class BrowserTabs(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabCloseRequested.connect(self.close_tab)
        self.customContextMenuRequested.connect(self.context_menu)
        self.browser = self.parent().parent()

    def context_menu(self, pos):
        self.currentWidget().customContextMenuRequested.emit(pos)

    def quit(self):
        for i in range(self.count()):
            self.close_tab(i)

    def close_tab(self, index):
        tab = self.widget(index)
        if tab:
            tab.quit()
            self.removeTab(index)
            tab.deleteLater()
            # QtGui.QPixmapCache.clear()

    def new_tab(self, location, server=None):
        view = ListView(self, server)
        view.working.connect(self.browser.ui.indicator.show)
        view.finished.connect(self.browser.ui.indicator.hide)
        view.play.connect(self.browser.create_player)
        view.photo.connect(self.browser.create_photo_viewer)
        view.metadata_selection.connect(self.browser.ui_update_metadata_panel)
        view.location_changed.connect(self.update_tab_text)
        view.download.connect(self.browser.download_manager.add)
        view.iconSizeChanged.connect(self.browser.ui_update_zoom)
        view.location_changed.connect(self.browser.location_changed)
        view.server_changed.connect(self.browser.server_changed)
        view.new_tab_requested.connect(self.new_tab)
        i = self.addTab(view, 'x')
        view.goto_location(location)
        self.setCurrentIndex(i)

    def update_tab_text(self, location):
        widget = self.sender()
        index = self.indexOf(widget)
        if index >= 0:
            self.setTabText(index, '{}@{}'.format(location.key.split('?')[0].split('%20')[0], widget.current_server.name))


# class PlaylistView(QtWidgets.QListView):
#     itemSelectionChanged = QtCore.pyqtSignal(list)
#     request_thumb = QtCore.pyqtSignal(object)
#     request_thumbs = QtCore.pyqtSignal(object)
#     play = QtCore.pyqtSignal(plexdevices.media.BaseObject)
#     remove = QtCore.pyqtSignal(list)

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._model = ListModel(self)
#         self.setModel(self._model)
#         self.list_delegate = plexdesktop.delegates.ListDelegate(self)
#         self.setItemDelegate(self.list_delegate)
#         self.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
#         self.setResizeMode(QtWidgets.QListView.Adjust)
#         self.icon_size(32)
#         self.setAlternatingRowColors(True)
#         self.doubleClicked.connect(self.double_click)
#         self.request_thumb.connect(self.model().request_thumb)
#         self.request_thumbs.connect(self.model().request_thumbs)
#         self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
#         self.customContextMenuRequested.connect(self.context_menu)

#     def quit(self):
#         self.model().quit()
#         self._model.deleteLater()
#         self._model = None

#     def set_container(self, container):
#         self.model().set_container(container)
#         indexes = (self.model().index(i) for i in range(self.model().rowCount()))
#         self.request_thumbs.emit(indexes)

#     def icon_size(self, x):
#         self.last_icon_size = QtCore.QSize(x, x)
#         self.setIconSize(self.last_icon_size)

#     def currentItem(self):
#         indexes = self.selectedIndexes()
#         if indexes:
#             return [indexes[0].data(role=QtCore.Qt.UserRole)]

#     def currentItems(self):
#         indexes = self.selectedIndexes()
#         return [index.data(role=QtCore.Qt.UserRole) for index in indexes]
#         if indexes:
#             return [indexes[0].data(role=QtCore.Qt.UserRole)]

#     def double_click(self, index):
#         self.play.emit(index.data(role=QtCore.Qt.UserRole))

#     def selectionChanged(self, selected, deselected):
#         super().selectionChanged(selected, deselected)
#         media = [index.data(role=QtCore.Qt.UserRole) for index in selected.indexes()]
#         self.itemSelectionChanged.emit(media)

#     def context_menu(self, pos):
#         items = self.currentItems()
#         if not items:
#             return
#         menu = QtWidgets.QMenu(self)
#         if len(items) == 1:
#             play = QtWidgets.QAction('Play', menu)
#             play.triggered.connect(self.cm_play_item)
#             play.setData(items[0])
#             menu.addAction(play)
#         remove = QtWidgets.QAction('Remove', menu)
#         remove.triggered.connect(self.cm_remove_item)
#         remove.setData(items)
#         menu.addAction(remove)
#         if not menu.isEmpty():
#             menu.exec_(QtGui.QCursor.pos())

#     def cm_play_item(self):
#         self.play.emit(self.sender().data())

#     def cm_remove_item(self):
#         self.remove.emit(self.sender().data())


class ListView(QtWidgets.QListView):
    viewModeChanged = QtCore.pyqtSignal()
    itemDoubleClicked = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    itemSelectionChanged = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    container_request = QtCore.pyqtSignal(plexdevices.device.Device,
                                          str, int, int, str, dict)

    queue = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    play = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    photo = QtCore.pyqtSignal(plexdevices.media.Photo)
    working = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    image_selection = QtCore.pyqtSignal(plexdevices.media.Photo)
    metadata_selection = QtCore.pyqtSignal(plexdevices.media.BaseObject)
    new_titles = QtCore.pyqtSignal(str, str)
    download = QtCore.pyqtSignal(plexdevices.media.BaseObject, str)

    location_changed = QtCore.pyqtSignal(plexdesktop.utils.Location)
    server_changed = QtCore.pyqtSignal(plexdevices.device.Device)
    new_tab_requested = QtCore.pyqtSignal(plexdesktop.utils.Location, plexdevices.device.Device)

    def __init__(self, parent=None, server=None):
        super().__init__(parent)
        self._model = ListModel(self)
        self.setModel(self._model)
        self._last_count = 0
        self.list_delegate = plexdesktop.delegates.ListDelegate(self)
        self.tile_delegate = plexdesktop.delegates.TileDelegateUniform(self)
        self.setItemDelegate(self.list_delegate)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.icon_size(32)
        self.setAlternatingRowColors(True)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        # self.setWrapping(True)
        # self.setBatchSize(50)
        # self.setLayoutMode(QtWidgets.QListView.Batched)

        self.min_icon_size = self.list_delegate.title_font_metrics.height()
        self.max_icon_size = 300

        self.doubleClicked.connect(self.double_click)
        self.container_request.connect(self.model().fetch_container)
        self.customContextMenuRequested.connect(self.context_menu)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        self.itemSelectionChanged.connect(self.selection_changed)
        # Model signals
        self.model().working.connect(self.working.emit)
        self.model().done.connect(self.finished.emit)
        self.model().done.connect(self.check_view_mode)
        self.model().new_container_titles.connect(self.new_titles.emit)

        self.location = plexdesktop.utils.Location.home()
        self.current_server = server
        self.history = [(self.current_server, self.location)]
        self.history_cursor = -1

        self.forced_toggle = False

    def quit(self):
        self._model.quit()
        self._model.deleteLater()
        self.list_delegate.deleteLater()
        self.tile_delegate.deleteLater()

    def mousePressEvent(self, event):
        if event.button() & QtCore.Qt.BackButton:
            self.go_back()
            event.accept()
        elif event.button() & QtCore.Qt.ForwardButton:
            self.go_forward()
            event.accept()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)

    # def resizeEvent(self, event):
    #     self.visible_items()
    #     super().resizeEvent(event)

    ########
    def clear_history(self):
        self.location = plexdesktop.utils.Location.home()
        self.history = [(self.current_server, self.location)]
        self.history_cursor = 0

    def sort(self, method):
        new_loc = plexdesktop.utils.Location(
            self.location.key, method,
            self.location.params)
        self.goto_location(new_loc, history=False)

    def reload(self):
        self.goto_location(self.location, history=False)

    def go_home(self):
        self.history = [(self.current_server, plexdesktop.utils.Location.home())]
        self.history_cursor = 0
        server, loc = self.history[self.history_cursor]
        self.goto_location(loc, history=False)

    def go_back(self):
        if self.history_cursor > 0:
            self.history_cursor -= 1
            server, loc = self.history[self.history_cursor]
            self.goto_location(loc, server, history=False)

    def go_forward(self):
        if self.history_cursor < len(self.history) - 1:
            self.history_cursor += 1
            server, loc = self.history[self.history_cursor]
            self.goto_location(loc, server, history=False)

    def goto_location(self, location, server=None, history=True):
        if not location.key.startswith('/'):
            location.key = self.location.key + '/' + location.key
        logger.info('BrowserList: key=' + location.key)

        if not server:
            server = self.current_server
            if not server:
                return

        if server != self.current_server:
            self.current_server = server
            self.server_changed.emit(server)

        self.location = location

        self.add_container(
            server=server,
            key=location.key,
            page=0,
            size=100,
            sort=location.sort,
            params=location.params
        )

        # History
        current_item = (server, self.location)
        if history:
            try:
                next_item = self.history[self.history_cursor + 1]
            except IndexError:
                next_item = self.history[-1]
            if current_item != next_item:
                self.history = self.history[:self.history_cursor + 1]
                self.history.append(current_item)
            self.history_cursor += 1

        self.location_changed.emit(location)
    ################

    def check_view_mode(self):
        if self.model().container:
            group = self.model().container.data.get('viewGroup')
            if group == 'photo':
                if self.viewMode() == QtWidgets.QListView.ListMode:
                    self.forced_toggle = True
                    self.toggle_view_mode()
            else:
                if self.forced_toggle and self.viewMode() == QtWidgets.QListView.IconMode:
                    self.toggle_view_mode()
                    self.forced_toggle = False

    def toggle_view_mode(self):
        if self.viewMode() == QtWidgets.QListView.ListMode:
            self.setItemDelegate(self.tile_delegate)
            self.setViewMode(QtWidgets.QListView.IconMode)
            bg_vertical = True
            self.setSpacing(4)
            self.icon_size(min(self.last_icon_size.height() * 2,
                               self.max_icon_size))
        else:
            self.setItemDelegate(self.list_delegate)
            self.setViewMode(QtWidgets.QListView.ListMode)
            bg_vertical = False
            self.setSpacing(0)
            self.icon_size(max(self.last_icon_size.height() / 2,
                               self.min_icon_size))
        self.setAlternatingRowColors(not bg_vertical)
        self.viewModeChanged.emit()
        if self.selectedIndexes():
            self.scrollTo(self.selectedIndexes()[0],
                          QtWidgets.QAbstractItemView.PositionAtCenter)

    def icon_size(self, x):
        self.last_icon_size = QtCore.QSize(x, x)
        self.setIconSize(self.last_icon_size)

    def add_container(self, server, key, page=0, size=50, sort=None, params=None):
        if page == 0:
            self.scrollToTop()
        self.container_request.emit(server, key, page, size,
                                    sort if sort is not None else '',
                                    params if params is not None else {})

    def double_click(self, index):
        self.itemDoubleClicked.emit(index.data(role=QtCore.Qt.UserRole))

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        try:
            self.itemSelectionChanged.emit(
                selected.indexes()[0].data(role=QtCore.Qt.UserRole))
        except IndexError:
            pass

    def currentItem(self):
        return self.currentIndex().data(role=QtCore.Qt.UserRole)

    def moveCursor(self, cursorAction, modifiers):
        index = self.currentIndex()
        if cursorAction == QtWidgets.QAbstractItemView.MoveNext:
            i = self.model().index(index.row() + 1, index.column())
            return i if i.isValid() else self.model().index(0, 0)
        elif cursorAction == QtWidgets.QAbstractItemView.MovePrevious:
            i = self.model().index(index.row() - 1, index.column())
            return i if i.isValid() else self.model().index(0, 0)
        return super().moveCursor(cursorAction, modifiers)

    def next_item(self):
        index = self.moveCursor(QtWidgets.QAbstractItemView.MoveNext,
                                QtCore.Qt.NoModifier)
        self.setCurrentIndex(index)

    def prev_item(self):
        index = self.moveCursor(QtWidgets.QAbstractItemView.MovePrevious,
                                QtCore.Qt.NoModifier)
        self.setCurrentIndex(index)

    # def update_batch_size(self):
    #     viewport = self.viewport().geometry()
    #     viewport.setRight(viewport.right() - self.verticalScrollBar().width())
    #     item_size = (self.visualRect(self.model().index(0)).size() +
    #                  QtCore.QSize(self.spacing(), self.spacing()))
    #     columns = max(1, viewport.width() // item_size.width())
    #     rows = math.ceil(viewport.height() / item_size.height())
    #     size = columns * rows
    #     self.setBatchSize(size)
    #     return (columns, rows)

    def visible_items(self):
        model = self.model()
        if not model.rowCount():
            return (0, [])
        rect = self.rect()

        # columns, rows = self.update_batch_size()

        visible = []

        start = self.indexAt(QtCore.QPoint(15, 15))
        for i in range(start.row() if start.isValid() else 0, model.rowCount()):
            index = model.index(i)
            if rect.intersects(self.visualRect(index)):
                visible.append(index)
            else:
                if visible:
                    break
        # print(len(visible))
        # self.request_thumbs.emit(visible)

    def preferences_prompt(self, item):
        plexdesktop.extra_widgets.PreferencesObjectDialog(item, parent=self)

    def search_prompt(self, item):
        text, ok = QtWidgets.QInputDialog.getText(self, 'Search', 'query:')
        if ok:
            self.goto_location(
                plexdesktop.utils.Location(item.key, params={'query': text}))

    def item_double_clicked(self, item):
        if isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.InputDirectory):
                self.search_prompt(item)
            elif isinstance(item, plexdevices.media.PreferencesDirectory):
                self.preferences_prompt(item)
            else:
                self.goto_location(plexdesktop.utils.Location(item.key))
        elif isinstance(item, plexdevices.media.MediaItem):
            if isinstance(item, (plexdevices.media.Movie,
                                 plexdevices.media.Episode,
                                 plexdevices.media.VideoClip,
                                 plexdevices.media.Track)):
                self.play.emit(item)
            elif isinstance(item, plexdevices.media.Photo):
                self.photo.emit(item)

    def selection_changed(self):
        m = self.currentItem()
        if m is None:
            return
        logger.debug(repr(m))
        if isinstance(m, (plexdevices.media.MediaItem,
                          plexdevices.media.MediaDirectory)):
            if isinstance(m, plexdevices.media.Photo):
                self.image_selection.emit(m)
            self.metadata_selection.emit(m)

    def context_menu(self, pos):
        index = self.currentIndex()
        item = index.data(role=QtCore.Qt.UserRole)
        if item is None:
            return
        component_manager = plexdesktop.components.ComponentManager.Instance()
        data = (item, index)
        menu = QtWidgets.QMenu(self)
        actions = []
        if isinstance(item, plexdevices.media.MediaItem):
            if isinstance(item, (plexdevices.media.Movie,
                                 plexdevices.media.Episode,
                                 plexdevices.media.VideoClip,
                                 plexdevices.media.Track)):
                main_action = QtWidgets.QAction('Play', menu)
                main_action.triggered.connect(self.cm_play)
                actions.append(main_action)
                if item.container.is_library:
                    for player in component_manager.players():
                        action = QtWidgets.QAction(
                            'Add to Queue: {}'.format(player.title), menu)
                        action.setData((item, player))
                        action.triggered.connect(self.cm_queue)
                        menu.addAction(action)
            elif isinstance(item, plexdevices.media.Photo):
                main_action = QtWidgets.QAction('View Photo', menu)
                main_action.triggered.connect(self.cm_play_photo)
                actions.append(main_action)
            copy_action = QtWidgets.QAction('Copy url', menu)
            copy_action.triggered.connect(self.cm_copy)
            actions.append(copy_action)
            save_action = QtWidgets.QAction('Download', menu)
            save_action.triggered.connect(self.cm_save_item)
            actions.append(save_action)
        elif isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.PreferencesDirectory):
                main_action = QtWidgets.QAction('Open', menu)
                main_action.triggered.connect(self.cm_settings)
                actions.append(main_action)
            else:
                main_action = QtWidgets.QAction('Open', menu)
                main_action.triggered.connect(self.cm_open)
                main_action2 = QtWidgets.QAction('Open in new tab', menu)
                main_action2.triggered.connect(self.cm_open_new_window)
                actions.append(main_action)
                actions.append(main_action2)
            if isinstance(item, (plexdevices.media.Show,
                                 plexdevices.media.Season,
                                 plexdevices.media.Album,
                                 plexdevices.media.Artist)):
                action = QtWidgets.QAction('Play all', menu)
                action.triggered.connect(self.cm_play)
                actions.append(action)

                if item.container.is_library:
                    for player in component_manager.players():
                        action = QtWidgets.QAction(
                            'Add to Queue: {}'.format(player.title), menu)
                        action.setData((item, player))
                        action.triggered.connect(self.cm_queue)
                        menu.addAction(action)
        if item.markable:
            mark_action = QtWidgets.QAction('Mark unwatched', menu)
            mark_action.triggered.connect(self.cm_mark_unwatched)
            mark_action2 = QtWidgets.QAction('Mark watched', menu)
            mark_action2.triggered.connect(self.cm_mark_watched)
            actions.append(mark_action)
            actions.append(mark_action2)

        if item.has_parent:
            open_action = QtWidgets.QAction(
                'goto: ' + plexdevices.types.get_type_string(item.parent_type),
                menu)
            open_action.triggered.connect(self.cm_open_parent)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = QtWidgets.QAction(
                'goto: ' + plexdevices.types.get_type_string(item.grandparent_type),
                menu)
            open_action.triggered.connect(self.cm_open_grandparent)
            actions.append(open_action)

        for action in actions:
            action.setData(data)
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(QtGui.QCursor.pos())

    def cm_queue(self):
        item, player = self.sender().data()
        self.queue.connect(player.queue)
        self.queue.emit(item)
        self.queue.disconnect()

    def cm_copy(self):
        url = self.sender().data()[0].resolve_url()
        QtWidgets.QApplication.clipboard().setText(url)

    def cm_settings(self):
        self.preferences_prompt(self.sender().data()[0])

    def cm_play(self):
        self.play.emit(self.sender().data()[0])

    def cm_play_photo(self):
        self.photo.emit(self.sender().data()[0])

    def cm_open(self):
        self.goto_location(plexdesktop.utils.Location(self.sender().data()[0].key))
        # self.goto_location(self.current_server, plexdesktop.utils.Location(self.sender().data()[0].key))

    def cm_open_new_window(self):
        item = self.sender().data()[0]
        # cm = plexdesktop.components.ComponentManager.Instance()
        # browser = cm.create_browser()
        loc = plexdesktop.utils.Location(
            item.key if item.key.startswith('/') else
            self.location.key + '/' + item.key)
        self.new_tab_requested.emit(loc, self.current_server)
        # browser.initialize(item.container.server, loc)

    def cm_open_parent(self):
        self.goto_location(plexdesktop.utils.Location(self.sender().data()[0].parent_key + '/children'))

    def cm_open_grandparent(self):
        self.goto_location(plexdesktop.utils.Location(self.sender().data()[0].grandparent_key + '/children'))

    def cm_mark_watched(self):
        item, index = self.sender().data()
        item.mark_watched()
        index.model().setData(index, None, QtCore.Qt.UserRole)

    def cm_mark_unwatched(self):
        item, index = self.sender().data()
        item.mark_unwatched()
        index.model().setData(index, None, QtCore.Qt.UserRole)

    def cm_save_item(self):
        item = self.sender().data()[0]
        save_dir = QtWidgets.QFileDialog.getExistingDirectory(self, 'Open Directory')
        if save_dir:
            self.download.emit(item, save_dir)
