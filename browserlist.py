import hashlib
import logging
from PyQt5.QtWidgets import (QListView, QStyledItemDelegate, QApplication,
                             QStyle, QAbstractItemView, QStyleOptionProgressBar, QProgressBar, QStyleOptionViewItem)
from PyQt5.QtGui import (QPixmap, QBrush, QPixmapCache, QColor, QPalette, QFont,
                         QFontMetrics, QPainter)
from PyQt5.QtCore import (pyqtSignal, QObject, QSize, Qt, QObject, QThread,
                          QAbstractListModel, QModelIndex, QRect, QPoint, QVariant)
from sqlcache import DB_THUMB
import plexdevices
import utils
logger = logging.getLogger('plexdesktop')


class DetailsViewDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_bar = QProgressBar()

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        data = index.data(role=Qt.UserRole)
        padding = 5
        title_font = QFont(option.font.family(), 9, weight=QFont.Bold)
        title_font_metrics = QFontMetrics(title_font)
        summary_font = QFont(option.font.family(), 7)
        summary_font_metrics = QFontMetrics(summary_font)
        # Background
        if option.state & QStyle.State_Selected:# or option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, option.palette.highlight())
        # Icon
        thumb = index.data(role=Qt.DecorationRole)
        if thumb is not None and not thumb.isNull():
            QApplication.style().drawItemPixmap(painter, option.rect,
                                                 Qt.AlignLeft | Qt.AlignVCenter,
                                                 thumb)
        # Title Line
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.setBrush(option.palette.highlightedText())
        else:
            painter.setBrush(option.palette.text())
        title_text = utils.title(data)
        painter.setFont(title_font)
        title_rect = QRect(option.rect.topLeft() + QPoint(thumb.width() + padding, 0),
                           option.rect.bottomRight())
        title_rect = QApplication.style().itemTextRect(title_font_metrics,
                                                        title_rect, Qt.AlignLeft,
                                                        True, title_text)
        QApplication.style().drawItemText(painter, title_rect,
                                           Qt.AlignLeft | Qt.TextWordWrap,
                                           option.palette, True, title_text)
        painter.restore()
        # Watched
        if data.is_video and not data.watched and not data.in_progress:
            rect = QRect(title_rect.topRight(), title_rect.bottomRight() + QPoint(title_rect.height(), 0))
            point = title_rect.topRight() + QPoint(title_font_metrics.height(), title_rect.height() / 2)
            painter.save()
            painter.setBrush(QBrush(QColor(204, 123, 25)))
            r = (title_font_metrics.height() * 0.75) // 2
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.drawEllipse(point, r, r)
            painter.restore()
        # # Summary text
        # if 'summary' in data:
        #     painter.save()
        #     summary_text = data['summary']
        #     painter.setFont(summary_font)
        #     summary_rect = QRect(title_rect.bottomLeft(), option.rect.bottomRight())
        #     QApplication.style().drawItemText(painter, summary_rect,
        #                                        Qt.AlignLeft | Qt.TextWordWrap,
        #                                        option.palette, True, summary_text)
        #     painter.restore()
        # Progress bar
        if 'viewOffset' in data and 'duration' in data:
            painter.save()
            painter.setFont(summary_font)
            progress = QStyleOptionProgressBar()
            progress.rect = QRect(option.rect.bottomLeft() - QPoint(-thumb.width() - padding,
                                  summary_font_metrics.height()), option.rect.bottomRight())
            progress.state |= QStyle.State_Enabled
            progress.direction = QApplication.layoutDirection()
            progress.fontMetrics = QApplication.fontMetrics()
            progress.minimum = 0
            progress.maximum = 100
            progress.progress = 100 * int(data['viewOffset']) / int(data['duration'])
            progress.text = (utils.timestamp_from_ms(int(data['viewOffset'])) + " / " +
                             utils.timestamp_from_ms(int(data['duration'])))
            progress.textVisible = True
            QApplication.style().drawControl(QStyle.CE_ProgressBar, progress, painter, self.progress_bar)
            painter.restore()

    def sizeHint(self, option, index):
        data = index.data(role=Qt.UserRole)
        return QSize(300, index.model().parent().iconSize().height() + 2 * 2)


class ListModel(QAbstractListModel):
    operate = pyqtSignal(plexdevices.Device, str, int, int, str, dict)
    new_item = pyqtSignal(plexdevices.MediaObject, int)
    working = pyqtSignal()
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None
        self.busy = False
        self._worker_thread = QThread()
        self._worker_thread.start()
        self._worker = ContainerWorker()
        self._thumb_worker = ThumbWorker()

        self._thumb_worker.moveToThread(self._worker_thread)
        self._thumb_worker.result_ready.connect(self._update_thumb)
        self.new_item.connect(self._thumb_worker.do_work)
        self._worker.moveToThread(self._worker_thread)
        self.operate.connect(self._worker.run, type=Qt.QueuedConnection)
        self._worker.done.connect(self._add_container)
        self.operate.connect(self._working)
        self._worker.finished.connect(self._done)

    def _stop_thread(self):
        logger.debug('BrowserList: ListModel: stop thread')
        self._worker_thread.quit()
        self._worker_thread.wait()

    def _working(self):
        self.working.emit()

    def _done(self, success):
        if success:
            t1, t2 = self.container.get('title1', ''), self.container.get('title2', '')
            self.done.emit(t1, t2)
        else:
            self.done.emit('', '')
            utils.msg_box('Error fetching data.')

    def _add_container(self, container):
        if self.container is None:
            start_len = 0
            self.container = container
            self.endResetModel()
        else:
            start_len = len(self.container.children)
            self.container.children += container.children

            self.endInsertRows()

        for i, item in enumerate(container.children):  # TODO: this seems kind of dumb
            if 'thumb' in item:
                self.new_item.emit(item, i + start_len)
        self.busy = False

    def _update_thumb(self, img, i):
        try:
            index = self.index(i)
        except Exception:
            logger.warning('BrowserList: ListModel: unable to set thumb.')
        else:
            self.setData(index, img, role=Qt.DecorationRole)

    def set_container2(self, container):
        self.beginResetModel()
        self._add_container(container)

    def set_container(self, server, key, page=0, size=50, sort="", params={}):
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
        self._thumb_worker.work = False
        DB_THUMB.commit()
        self._thumb_worker.work = True
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
        return (False if self.container is None or not len(self.container.children) else
                len(self.container.children) < int(self.container.get('totalSize', 0)))

    def fetchMore(self, parent):
        start_len = len(self.container.children)
        remaining = self.container['totalSize'] - len(self.container.children)
        items_to_fetch = min(self.container_size, remaining)
        self.beginInsertRows(QModelIndex(), len(self.container.children),
                             len(self.container.children) + items_to_fetch - 1)
        self.operate.emit(self.server, self.key, self.page, self.container_size,
                          self.sort, self.params)
        self.page += 1


class ListView(QListView):
    resize_signal = pyqtSignal()
    viewModeChanged = pyqtSignal()
    itemDoubleClicked = pyqtSignal(plexdevices.MediaObject)
    itemSelectionChanged = pyqtSignal(plexdevices.MediaObject)
    container_request = pyqtSignal(plexdevices.Device, str, int, int, str, dict)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.delegate = DetailsViewDelegate()
        self.delegate_default = QStyledItemDelegate()
        self.setItemDelegate(self.delegate)
        self.doubleClicked.connect(self.double_click)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setResizeMode(QListView.Adjust)
        self.icon_size(32)
        self.setAlternatingRowColors(True)

        self.model = ListModel(parent=self)
        self.setModel(self.model)
        self.container_request.connect(self.model.set_container, type=Qt.QueuedConnection)
        self.closed.connect(self.model._stop_thread)

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
        self.container_request.emit(server, key, page, size, sort, params)

    def add_container2(self, container):
        self.model.set_container2(container)

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
        self.closed.emit()
        super().closeEvent(event)


class ContainerWorker(QObject):
    done = pyqtSignal(plexdevices.MediaContainer)
    finished = pyqtSignal(bool)

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
            self.finished.emit(False)
        else:
            logger.debug('BrowserList: url=' + server.active.url)
            container = plexdevices.MediaContainer(server, data)
            self.done.emit(container)
            self.finished.emit(True)


class ThumbWorker(QObject):
    result_ready = pyqtSignal(QPixmap, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.work = True

    def do_work(self, media_object, row):
        if not self.work:
            return
        self.media_object = media_object
        url = media_object['thumb']
        key = media_object.parent.server.client_identifier + url
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        img = QPixmapCache.find(key_hash)
        if img is None:
            img_data = DB_THUMB[url]
            if img_data is None:  # not in cache, fetch from server
                if media_object.parent.is_library:  # trancode
                    img_data = media_object.parent.server.image(url, w=300, h=300)
                else:  # don't transcode
                    img_data = media_object.parent.server.image(url)
                DB_THUMB[url] = img_data
            img = QPixmap()
            img.loadFromData(img_data)
            QPixmapCache.insert(key_hash, img)
        self.result_ready.emit(img, row)
        self.media_object = None
