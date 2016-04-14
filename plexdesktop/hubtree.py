import logging
from PyQt5.QtWidgets import QTreeView, QAction, QMenu
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Qt, QAbstractItemModel,
                          QModelIndex, QVariant, QEvent, QThread, QSize, QRect, QPoint)
from PyQt5.QtGui import QCursor
from plexdesktop.utils import Location, hub_title, timestamp_from_ms
from plexdesktop.workers import ThumbWorker, ContainerWorker, HubWorker
from plexdesktop.sqlcache import DB_THUMB
from plexdesktop.delegates import HubDelegate
import plexdevices
logger = logging.getLogger('plexdesktop')


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
        return [
            hub_title(self.plex_item),  # display title
        ][column]

    def row(self):
        return self.parent.child_items.index(self) if self.parent is not None else 0

    def parentItem(self):
        return self.parent


class TreeModel(QAbstractItemModel):

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.root_item = TreeItem()
        self.setupModelData(data, self.root_item)
        self._thumb_queue = {}
        self._parent = parent

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = (self.root_item if not parent.isValid() else
                       parent.internalPointer())
        child_item = parent_item.child(row)
        return self.createIndex(row, column, child_item) if child_item else QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parentItem()

        if parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        parent_item = (self.root_item if not parent.isValid() else
                       parent.internalPointer())
        return parent_item.childCount()

    def total_rows(self):
        count = self.rowCount()
        return count + sum((self.rowCount(self.index(i, 0)) for i in range(count)))

    def columnCount(self, parent=QModelIndex()):
        return (parent.internalPointer().columnCount() if parent.isValid() else
                self.root_item.columnCount())

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        if role == Qt.UserRole:
            return index.internalPointer().plex_item
        elif role == Qt.DisplayRole:
            return index.internalPointer().data(index.column())
        elif role == Qt.DecorationRole:
            return index.internalPointer().thumb
        else:
            return QVariant()

    def flags(self, index):
        return 0 if not index.isValid() else super().flags(index)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_item.data(section)
        return QVariant()

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
            index.internalPointer().thumb = value.scaledToWidth(self._parent.iconSize().width(), Qt.SmoothTransformation)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            return True
        else:
            return False

    def request_thumbs(self):
        root_indexes = [self.index(i, 0) for i in range(self.rowCount())]
        indexes = root_indexes
        for index in root_indexes:
            indexes += [self.index(x, 0, parent=index) for x in range(index.internalPointer().childCount())]
        queue = (i for i in indexes if (i not in self._thumb_queue and not isinstance(i.data(role=Qt.UserRole), plexdevices.hubs.Hub)))
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

    def has_thumb(self, index):
        return index.internalPointer().thumb is not None


class TreeView(QTreeView):
    request_container = pyqtSignal(plexdevices.device.Device, str, dict)
    goto_location = pyqtSignal(Location)
    goto_hub = pyqtSignal(plexdevices.hubs.Hub)
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.setItemsExpandable(False)
        self.doubleClicked.connect(self.double_click)
        self.setIconSize(QSize(48, 48))
        self.setAlternatingRowColors(True)
        self._model = None

        self._worker_thread = QThread()
        self._worker = HubWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker.result_ready.connect(self._add_container)
        self.request_container.connect(self._worker.run)
        self._worker_thread.start()

        self.delegate = HubDelegate(self)
        self.setItemDelegate(self.delegate)

        self.goto_hub.connect(self.load_hub)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
        else:
            event.ignore()

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
        loc = Location(item.key)
        self.goto_location.emit(loc)

    def context_menu(self, pos):
        item = self.current_item()
        logger.debug(item)

        if isinstance(item, plexdevices.hubs.Hub):
            return

        menu = QMenu(self)
        actions = []
        if isinstance(item, plexdevices.media.MediaItem):
            pass
        elif isinstance(item, plexdevices.media.Directory):
            if hasattr(item, 'key'):
                action = QAction('go', menu)
                action.triggered.connect(self.cm_goto)
                action.setData(Location(item.key))
                actions.append(action)

        if hasattr(item, 'parent_key'):
            action = QAction('goto: ' + plexdevices.get_type_string(item.parent_type), menu)
            action.triggered.connect(self.cm_goto)
            action.setData(Location(item.parent_key))
            actions.append(action)
        if hasattr(item, 'grandparent_key'):
            action = QAction('goto: ' + plexdevices.get_type_string(item.grandparent_type), menu)
            action.triggered.connect(self.cm_goto)
            action.setData(Location(item.grandparent_key))
            actions.append(action)

        for action in actions:
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def cm_goto(self, state):
        loc = self.sender().data()
        self.goto_location.emit(loc)

    def search(self, server, query):
        self.request_container.emit(server, '/hubs/search', {'query': query})
        self.setWindowTitle('Search Results: {}'.format(query))

    def load_hub(self, hub):
        self.goto(hub.container.server, hub.key)

    def goto(self, server, key, params=None):
        logger.debug('{} {}'.format(server, key))
        if key:
            self.request_container.emit(server, key, {})

    def _add_container(self, container):
        self._model = TreeModel(container, self)
        self.setModel(self._model)
        self.header().hide()
        self.expandAll()
        # self.resize(350, self.iconSize().height() * (self.model().total_rows() + 1))

        logger.debug(self._model.total_rows())
        if self._model.total_rows():
            self.model().request_thumbs()
            self.show()
        self.finished.emit()

    @pyqtSlot()
    def _show(self):
        if self._model is not None:
            self.show()
            self.finished.emit()
