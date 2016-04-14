import logging
import os
from threading import Thread
from PyQt5.QtWidgets import (QListView, QStyledItemDelegate, QApplication,
                             QAbstractItemView, QMenu, QAction, QFileDialog)
from PyQt5.QtGui import (QPixmap, QPixmapCache, QCursor)
from PyQt5.QtCore import (pyqtSignal, QObject, QSize, Qt, QThread,
                          QAbstractListModel, QModelIndex, QPoint, QVariant)
from plexdesktop.sqlcache import DB_THUMB, DB_IMAGE
from plexdesktop.utils import *
from plexdesktop.workers import ThumbWorker, ContainerWorker
from plexdesktop.extra_widgets import PreferencesObjectDialog
from plexdesktop.delegates import ListDelegate
import plexdevices
logger = logging.getLogger('plexdesktop')


class ListModel(QAbstractListModel):
    operate = pyqtSignal(plexdevices.device.Device, str, int, int, str, dict)
    new_item = pyqtSignal(QModelIndex)
    working = pyqtSignal()
    done = pyqtSignal()
    new_container_titles = pyqtSignal(str, str)
    new_container = pyqtSignal()
    new_page = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None
        self.busy = False
        self._worker_thread = QThread()
        self._thumb_queue = {}

        self._worker = ContainerWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker.result_ready.connect(self._add_container)
        self._worker.finished.connect(self._done)

        self.operate.connect(self._worker.run)
        self.operate.connect(self.working.emit)

        self._worker_thread.start()

    def clear(self):
        self.beginResetModel()
        self.container = None
        self.endResetModel()

    def quit(self):
        logger.debug('BrowserList: ListModel: stop thread')
        self._worker_thread.quit()
        DB_THUMB.commit()

    def _done(self):
        if self.container:
            t1, t2 = self.container.title1, self.container.title2
            self.new_container_titles.emit(t1, t2)
        self.done.emit()

    def _add_container(self, container):
        if self.container is None:
            start_len = 0
            self.container = container
            self.endResetModel()
            self.new_container.emit()
        else:
            start_len = len(self.container.children)
            self.container.children += container.children
            self.endInsertRows()
            self.new_page.emit()
        self.busy = False

    def request_thumbs(self, n, indexes):
        queue = (i for i in indexes if i not in self._thumb_queue)
        for index in queue:
            worker = ThumbWorker(index)
            worker.result_ready.connect(self._update_thumb)
            worker.finished.connect(DB_THUMB.commit)
            self._thumb_queue[index] = self.start_thumb_worker(worker)

    def start_thumb_worker(self, worker):
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self.remove_thumb_worker)
        thread.worker = worker
        thread.start()
        return thread

    def remove_thumb_worker(self):
        worker = self.sender().worker
        self._thumb_queue[worker.index].deleteLater()
        worker.deleteLater()
        self._thumb_queue[worker.index].worker = None
        del self._thumb_queue[worker.index]
        worker.index = None

    def _update_thumb(self, img, index):
        self.setData(index, img, role=Qt.DecorationRole)

    def set_container(self, container):
        self.beginResetModel()
        self.container = container
        self.endResetModel()
        self.done.emit()

    def fetch_container(self, server, key, page=0, size=50, sort="", params={}):
        if self.busy:
            return
        self.beginResetModel()
        self.busy = True
        self.server = server
        self.key = key
        self.page = page
        self.container_size = size
        self.sort = sort
        self.params = params
        self.container = None

        self.operate.emit(self.server, self.key, self.page, self.container_size,
                          self.sort, self.params)
        self.page += 1

    def rowCount(self, parent=QModelIndex()):
        return 0 if self.container is None else len(self.container)

    def data(self, index, role=Qt.DisplayRole):
        if self.container is None:
            return QVariant()
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
                img = None
            if img is None:
                img = QPixmap()
            return (img if img.isNull() else
                    self.container.children[index.row()].user_data.scaled(
                        self.parent().iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def setData(self, index, value, role):
        if index.data(role=Qt.UserRole) is None:
            return False
        if role == Qt.DecorationRole:
            index.data(role=Qt.UserRole).user_data = value
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            return True

    def canFetchMore(self, index):
        return (False if self.container is None or not len(self.container.children) else
                len(self.container.children) < self.container.total_size)

    def fetchMore(self, parent):
        start_len = len(self.container)
        remaining = self.container.total_size - len(self.container)
        items_to_fetch = min(self.container_size, remaining)
        self.beginInsertRows(QModelIndex(), len(self.container),
                             len(self.container) + items_to_fetch - 1)
        self.operate.emit(self.server, self.key, self.page, self.container_size,
                          self.sort, self.params)
        self.page += 1

    def has_thumb(self, index):
        try:
            return self.container.children[index.row()].user_data is not None
        except (AttributeError, IndexError):
            return False


class PlaylistView(QListView):
    itemSelectionChanged = pyqtSignal(list)
    request_thumbs = pyqtSignal(int, object)
    play = pyqtSignal(plexdevices.media.BaseObject)
    remove = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ListModel(self)
        self.setModel(self._model)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setResizeMode(QListView.Adjust)
        self.icon_size(24)
        self.setAlternatingRowColors(True)
        self.doubleClicked.connect(self.double_click)
        self.request_thumbs.connect(self.model().request_thumbs)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def set_container(self, container):
        self.model().set_container(container)
        indexes = (self.model().index(i) for i in range(self.model().rowCount()))
        self.request_thumbs.emit(self.model().rowCount(), indexes)

    def icon_size(self, x):
        self.last_icon_size = QSize(x, x)
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

    def closeEvent(self, event):
        self.model().quit()

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        media = [index.data(role=Qt.UserRole) for index in selected.indexes()]
        self.itemSelectionChanged.emit(media)

    def context_menu(self, pos):
        items = self.currentItems()
        if not items:
            return
        menu = QMenu(self)
        if len(items) == 1:
            play = QAction('Play', menu)
            play.triggered.connect(self.cm_play_item)
            play.setData(items[0])
            menu.addAction(play)
        remove = QAction('Remove', menu)
        remove.triggered.connect(self.cm_remove_item)
        remove.setData(items)
        menu.addAction(remove)
        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def cm_play_item(self):
        self.play.emit(self.sender().data())

    def cm_remove_item(self):
        self.remove.emit(self.sender().data())


class ListView(QListView):
    viewModeChanged = pyqtSignal()
    itemDoubleClicked = pyqtSignal(plexdevices.media.BaseObject)
    itemSelectionChanged = pyqtSignal(plexdevices.media.BaseObject)
    container_request = pyqtSignal(plexdevices.device.Device, str, int, int, str, dict)
    request_thumbs = pyqtSignal(int, object)
    goto_location = pyqtSignal(Location)
    queue = pyqtSignal(plexdevices.media.BaseObject)
    play = pyqtSignal(plexdevices.media.BaseObject)
    photo = pyqtSignal(plexdevices.media.Photo)
    working = pyqtSignal()
    finished = pyqtSignal()
    image_selection = pyqtSignal(plexdevices.media.Photo)
    metadata_selection = pyqtSignal(plexdevices.media.BaseObject)
    new_titles = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ListModel(parent=self)
        self.setModel(self._model)
        self._last_count = 0
        self._player_state, self._photo_viewer_state = False, False
        self.delegate = ListDelegate(self)
        self.delegate_default = QStyledItemDelegate()
        self.setItemDelegate(self.delegate)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setResizeMode(QListView.Adjust)
        self.icon_size(32)
        self.setAlternatingRowColors(True)

        self.doubleClicked.connect(self.double_click)
        self.container_request.connect(self.model().fetch_container)
        self.verticalScrollBar().valueChanged.connect(self.visibleItemsChanged)
        self.request_thumbs.connect(self.model().request_thumbs)
        self.customContextMenuRequested.connect(self.context_menu)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        self.itemSelectionChanged.connect(self.selection_changed)
        # Model signals
        self._model.done.connect(self.visibleItemsChanged)
        self._model.working.connect(self.working.emit)
        self._model.done.connect(self.finished.emit)
        self._model.new_container_titles.connect(self.new_titles.emit)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def closeEvent(self, event):
        self.model().quit()
        super().closeEvent(event)

    def resizeEvent(self, event):
        n, indexes = self.visible_items()
        if n != self._last_count:
            logger.debug('request_thumbs')
            self._last_count = n
            self.request_thumbs.emit(n, indexes)
        super().resizeEvent(event)

    def clear(self):
        self.model().clear()

    def toggle_view_mode(self):
        if self.viewMode() == QListView.ListMode:
            self.setViewMode(QListView.IconMode)
            self.bg_vertical = True
        else:
            self.setViewMode(QListView.ListMode)
            self.bg_vertical = False
        self.setAlternatingRowColors(not self.bg_vertical)
        self.viewModeChanged.emit()

    def icon_size(self, x):
        self.last_icon_size = QSize(x, x)
        self.setIconSize(self.last_icon_size)
        self.visibleItemsChanged()

    def add_container(self, server, key, page=0, size=50, sort="", params=None):
        self.container_request.emit(server, key, page, size, sort,
                                    params if params is not None else {})

    def double_click(self, index):
        self.itemDoubleClicked.emit(index.data(role=Qt.UserRole))

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        self.itemSelectionChanged.emit(selected.indexes()[0].data(role=Qt.UserRole))

    def currentItem(self):
        indexes = self.selectedIndexes()
        if indexes:
            return indexes[0].data(role=Qt.UserRole)

    def next_item(self):
        index = self.moveCursor(QAbstractItemView.MoveDown, Qt.NoModifier)
        self.setCurrentIndex(index)

    def prev_item(self):
        index = self.moveCursor(QAbstractItemView.MoveUp, Qt.NoModifier)
        self.setCurrentIndex(index)

    def visibleItemsChanged(self):
        n, indexes = self.visible_items()
        self.request_thumbs.emit(n, indexes)

    def visible_items(self):
        model = self.model()
        if not model.rowCount():
            return (0, [])
        min_item = self.indexAt(QPoint(5, 5))
        max_item = self.indexAt(QPoint(5, self.height() - 5))
        if min_item is None:
            min_item = model.index(0)
        if max_item is None:
            max_item = model.index(model.rowCount() - 1)
        min_row, max_row = min_item.row(), max_item.row()
        if max_row < 0:
            max_row = model.rowCount()
        max_row = min(model.rowCount(), max_row + 1)
        return (max_row - min_row, (model.index(x) for x in range(min_row, max_row)))

    def preferences_prompt(self, item):
        dialog = PreferencesObjectDialog(item, parent=self)

    def search_prompt(self, item):
        text, ok = QInputDialog.getText(self, 'Search', 'query:')
        if ok:
            self.goto_location(Location(item.key, params={'query': text}))

    def item_double_clicked(self, item):
        if isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.InputDirectory):
                self.search_prompt(item)
            elif isinstance(item, plexdevices.media.PreferencesDirectory):
                self.preferences_prompt(item)
            else:
                self.goto_location.emit(Location(item.key))
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
        item = self.currentItem()
        if item is None:
            return
        menu = QMenu(self)
        actions = []
        if isinstance(item, plexdevices.media.MediaItem):
            if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode,
                                 plexdevices.media.VideoClip, plexdevices.media.Track)):
                main_action = QAction('Play', menu)
                main_action.triggered.connect(self.cm_play)
                actions.append(main_action)
                if self._player_state and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)
            elif isinstance(item, plexdevices.media.Photo):
                main_action = QAction('View Photo', menu)
                main_action.triggered.connect(self.cm_play_photo)
                save_action = QAction('Save', menu)
                save_action.triggered.connect(self.cm_save_photo)
                actions.append(main_action)
                actions.append(save_action)
            copy_action = QAction('Copy url', menu)
            copy_action.triggered.connect(self.cm_copy)
            actions.append(copy_action)
        elif isinstance(item, plexdevices.media.Directory):
            if isinstance(item, plexdevices.media.PreferencesDirectory):
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.cm_settings)
                actions.append(main_action)
            else:
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.cm_open)
                actions.append(main_action)
            if isinstance(item, (plexdevices.media.Show, plexdevices.media.Season,
                                 plexdevices.media.Album, plexdevices.media.Artist)):
                action = QAction('Play all', menu)
                action.triggered.connect(self.cm_play)
                actions.append(action)
                if self._player_state and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)

        if item.markable:
            mark_action = QAction('Mark unwatched', menu)
            mark_action.triggered.connect(self.cm_mark_unwatched)
            mark_action2 = QAction('Mark watched', menu)
            mark_action2.triggered.connect(self.cm_mark_watched)
            actions.append(mark_action)
            actions.append(mark_action2)

        if item.has_parent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.parent_type), menu)
            open_action.triggered.connect(self.cm_open_parent)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.grandparent_type), menu)
            open_action.triggered.connect(self.cm_open_grandparent)
            actions.append(open_action)

        for action in actions:
            action.setData(item)
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def cm_queue(self):
        self.queue.emit(self.sender().data())

    def cm_copy(self):
        url = self.sender().data().resolve_url()
        QApplication.clipboard().setText(url)

    def cm_settings(self):
        self.preferences_prompt(self.sender().data())

    def cm_play(self):
        self.play.emit(self.sender().data())

    def cm_play_photo(self):
        self.photo.emit(self.sender().data())

    def cm_open(self):
        self.goto_location.emit(Location(self.sender().data().key))

    def cm_open_parent(self):
        self.goto_location.emit(Location(self.sender().data().parent_key + '/children'))

    def cm_open_grandparent(self):
        self.goto_location.emit(Location(self.sender().data().grandparent_key + '/children'))

    def cm_mark_watched(self):
        self.sender().data().mark_watched()

    def cm_mark_unwatched(self):
        self.sender().data().mark_unwatched()

    def cm_save_photo(self):
        item = self.sender().data()
        url = item.resolve_url()
        ext = url.split('?')[0].split('/')[-1].split('.')[-1]
        fname = '{}.{}'.format(''.join([x if x.isalnum() else "_" for x in item.title]), ext)
        logger.debug(('Browser: save_photo: item={}, url={}, ext={}, '
                      'fname={}').format(item, url, ext, fname))
        save_file, filtr = QFileDialog.getSaveFileName(self, 'Open Directory',
                                                       fname,
                                                       'Images (*.{})'.format(ext))
        if save_file:
            self.working.emit()
            t = Thread(target=self.write_image, args=(item, url, save_file))
            t.start()

    def write_image(self, item, url, file):
        try:
            data = DB_IMAGE[url]
            if data is None:
                logger.debug('Browser: write_image: downloading image')
                data = item.container.server.image(url)
            else:
                logger.debug('Browser: write_image: image was in the cache')
        except Exception as e:
            logger.error('Browser: write_image: ' + str(e))
        else:
            with open(os.path.abspath(file), 'wb') as f:
                logger.info('Browser: write_image: writing to: {}'.format(file))
                f.write(data)
        self.finished.emit()

    def player_state(self, state):
        self._player_state = state

    def photo_viewer_state(self, state):
        self._photo_viewer_state = state
