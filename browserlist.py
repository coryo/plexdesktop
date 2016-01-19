import hashlib
from PyQt5.QtWidgets import (QListView, QStyledItemDelegate, QApplication,
                             QStyle, QAbstractItemView, QStyleOptionProgressBar)
from PyQt5.QtGui import (QPixmap, QBrush, QPixmapCache, QColor, QPalette, QFont,
                         QFontMetrics)
from PyQt5.QtCore import (pyqtSignal, QObject, QSize, Qt, QObject, QThread,
                          QAbstractListModel, QModelIndex, QRect, QPoint, QVariant)
from sqlcache import SqlCache
import plexdevices
import utils


class DetailsViewDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        data = index.data(role=Qt.UserRole)
        padding = 5
        title_font = QFont(option.font.family(), 9, weight=QFont.Bold)
        summary_font = QFont(option.font.family(), 7)
        # Background
        if option.state & QStyle.State_Selected or option.state & QStyle.State_MouseOver:
            brush = QApplication.palette().highlight()
            color = QApplication.palette().highlight().color()
            color.setAlpha(32)
            brush.setColor(color)
            painter.save()
            painter.fillRect(option.rect, brush)
            painter.restore()
        # Icon
        thumb = index.data(role=Qt.DecorationRole)
        if thumb is not None and not thumb.isNull():
            option.widget.style().drawItemPixmap(painter, option.rect,
                                                 Qt.AlignLeft | Qt.AlignVCenter,
                                                 thumb)
        # Title Line
        painter.save()
        title_text = utils.title(data)
        painter.setFont(title_font)
        title_rect = QRect(option.rect.topLeft() + QPoint(thumb.width() + padding, 0),
                           option.rect.bottomRight())
        title_rect = option.widget.style().itemTextRect(QFontMetrics(title_font),
                                                        title_rect, Qt.AlignLeft,
                                                        True, title_text)
        option.widget.style().drawItemText(painter, title_rect,
                                           Qt.AlignLeft | Qt.TextWordWrap,
                                           option.palette, True, title_text)
        painter.restore()

        # Watched
        if data.is_video and not data.watched and not data.in_progress:
            rect = QRect(title_rect.topRight(), title_rect.bottomRight()+QPoint(title_rect.height(), 0))
            point = title_rect.topRight() + QPoint(QFontMetrics(title_font).height(), title_rect.height()/2)
            painter.save()
            painter.setBrush(QBrush(QColor(204, 123, 25))) #204,123,25
            painter.drawEllipse(point, 5, 5)
            painter.restore()

        # Summary text
        if 'summary' in data:
            painter.save()
            summary_text = data['summary']
            painter.setFont(summary_font)
            summary_rect = QRect(title_rect.bottomLeft(), option.rect.bottomRight())
            option.widget.style().drawItemText(painter, summary_rect,
                                               Qt.AlignLeft | Qt.TextWordWrap,
                                               option.palette, True, summary_text)
            painter.restore()
        # Progress bar
        if 'viewOffset' in data and 'duration' in data:
            painter.save()
            painter.setFont(summary_font)
            progress = QStyleOptionProgressBar()
            progress.rect = QRect(option.rect.bottomLeft() - QPoint(-thumb.width() - padding,
                                  QFontMetrics(painter.font()).height()), option.rect.bottomRight())
            progress.maximum = 100
            progress.progress = 100 * int(data['viewOffset']) / int(data['duration'])
            progress.textAlignment = Qt.AlignHCenter | Qt.AlignVCenter
            progress.text = (utils.timestamp_from_ms(int(data['viewOffset'])) + " / " +
                             utils.timestamp_from_ms(int(data['duration'])))
            progress.textVisible = True
            option.widget.style().drawControl(QStyle.CE_ProgressBar, progress, painter)
            painter.restore()

    def sizeHint(self, option, index):
        data = index.data(role=Qt.UserRole)
        return QSize(400, index.model().parent().iconSize().height() + 2 * 2)


class ListModel(QAbstractListModel):
    operate = pyqtSignal(plexdevices.Device, str, int, int, str, dict)
    new_item = pyqtSignal(plexdevices.MediaObject, int)
    working = pyqtSignal()
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker_thread = QThread()
        self._worker = ContainerWorker()
        self._thumb_worker = ThumbWorker()

        self._thumb_worker.moveToThread(self._worker_thread)
        self._thumb_worker.result_ready.connect(self._update_thumb)
        self._worker_thread.started.connect(self._thumb_worker.save_cache)
        self.new_item.connect(self._thumb_worker.do_work, type=Qt.QueuedConnection)
        self._worker.moveToThread(self._worker_thread)
        self.operate.connect(self._worker.run, type=Qt.QueuedConnection)
        self._worker.done.connect(self._add_container)
        self.operate.connect(self._working)
        self._worker.finished.connect(self._done)

    def _working(self):
        self.working.emit()

    def _done(self):
        t1, t2 = self.container.get('title1', ''), self.container.get('title2', '')
        self.done.emit(t1, t2)

    def _close(self):
        self._worker_thread.quit()
        self._worker_thread.wait()

    def _add_container(self, container):
        if self.container is None:
            start_len = 0
            self.container = container
            self.endResetModel()
        else:
            start_len = len(self.container.children)
            self.container.children += container.children

            self.endInsertRows()

        for i, item in enumerate(container.children):
            if 'thumb' in item:
                self.new_item.emit(item, i + start_len)

    def _update_thumb(self, img, i):
        self.setData(self.index(i), img, role=Qt.DecorationRole)

    def set_container(self, server, key, page=0, size=50, sort="", params={}):
        self.beginResetModel()
        self.server = server
        self.key = key
        self.page = page
        self.container_size = size
        self.sort = sort
        self.params = params
        self.container = None
        self._worker_thread.quit()
        self._worker_thread.wait()
        self._worker_thread.start()
        self.operate.emit(self.server, self.key, self.page, self.container_size,
                          self.sort, self.params)
        self.page += 1

    def rowCount(self, parent=QModelIndex()):
        return 0 if self.container is None else len(self.container)

    def data(self, index, role=Qt.DisplayRole):
        if self.container is None:
            return QVariant()
        if role == Qt.DisplayRole:
            return self.container.children[index.row()]['title']
        elif role == Qt.UserRole:
            return self.container.children[index.row()]
        elif role == Qt.DecorationRole:
            img = self.container.children[index.row()].get('icon', QPixmap())
            return (img if img.isNull() else
                    self.container.children[index.row()]['icon'].scaled(
                        self.parent().iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def setData(self, index, value, role):
        if index.data(role=Qt.UserRole) is None:
            return
        if role == Qt.DecorationRole:
            index.data(role=Qt.UserRole)['icon'] = value
            self.dataChanged.emit(index, index, [Qt.DecorationRole])

    def canFetchMore(self, index):
        return (False if self.container is None else
                len(self.container.children) < int(self.container.get('totalSize', 0)))

    def fetchMore(self, parent):
        start_len = len(self.container.children)
        remaining = self.container['totalSize'] - len(self.container.children)
        items_to_fetch = min(self.container_size, remaining)
        self.beginInsertRows(QModelIndex(), len(self.container.children),
                             len(self.container.children) + items_to_fetch - 1)
        self._worker_thread.quit()
        self._worker_thread.wait()
        self._worker_thread.start()
        self.operate.emit(self.server, self.key, self.page, self.container_size,
                          self.sort, self.params)
        self.page += 1


class ListView(QListView):
    resize_signal = pyqtSignal()
    viewModeChanged = pyqtSignal()
    itemDoubleClicked = pyqtSignal(plexdevices.MediaObject)
    itemSelectionChanged = pyqtSignal(plexdevices.MediaObject)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.delegate = DetailsViewDelegate()
        self.setItemDelegate(self.delegate)
        self.doubleClicked.connect(self.double_click)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setResizeMode(QListView.Adjust)
        self.icon_size(48)
        self.setAlternatingRowColors(True)

        self.model = ListModel(parent=self)
        self.setModel(self.model)

    def toggle_view_mode(self):
        if self.viewMode() == QListView.ListMode:
            self.setViewMode(QListView.IconMode)
            self.bg_vertical = True
            self.setAlternatingRowColors(False)
        else:
            self.setViewMode(QListView.ListMode)
            self.bg_vertical = False
            self.setAlternatingRowColors(True)
        self.viewModeChanged.emit()

    def icon_size(self, x):
        self.last_icon_size = QSize(x, x)
        self.setIconSize(self.last_icon_size)

    def add_container(self, server, key, page=0, size=50, sort="", params={}):
        self.model.set_container(server, key, page, size, sort, params)

    def double_click(self, index):
        self.itemDoubleClicked.emit(index.data(role=Qt.UserRole))

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        indexes = selected.indexes()
        self.itemSelectionChanged.emit(indexes[0].data(role=Qt.UserRole))

    def currentItem(self):
        indexes = self.selectedIndexes()
        return indexes[0].data(role=Qt.UserRole)

    def next_item(self):
        index = self.moveCursor(QAbstractItemView.MoveDown, Qt.NoModifier)
        self.setCurrentIndex(index)

    def prev_item(self):
        index = self.moveCursor(QAbstractItemView.MoveUp, Qt.NoModifier)
        self.setCurrentIndex(index)

    def closeEvent(self, event):
        self.model._close()
        super().closeEvent(event)


class ContainerWorker(QObject):
    done = pyqtSignal(plexdevices.MediaContainer)
    finished = pyqtSignal()

    def run(self, server, key, page=0, size=20, sort="", params={}):
        p = {} if not sort else {'sort': sort}
        if params:
            p.update(params)
        try:
            data = server.container(key, page=page, size=size, params=p)
        except (plexdevices.exceptions.DeviceConnectionsError, TypeError) as e:
            print(str(e))
        else:
            container = plexdevices.MediaContainer(server, data)
            self.done.emit(container)
        self.finished.emit()


class ThumbWorker(QObject):
    result_ready = pyqtSignal(QPixmap, int)

    def __init__(self, parent=None):
        super().__init__()
        self.cache = None

    def save_cache(self):
        if self.cache is not None:
            self.cache.save()

    def do_work(self, media_object, row):
        if self.cache is None:
            self.cache = SqlCache('thumb', access=False)
            self.cache.open()
        url = media_object['thumb']
        key = media_object.parent.server.client_identifier + url
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        img = QPixmapCache.find(key_hash)
        if img is None:
            img_data = self.cache[url]
            if img_data is None:
                img_data = media_object.parent.server.image(url, w=300, h=300)
                self.cache[url] = img_data
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(key_hash, img)
        self.result_ready.emit(img, row)
        return
