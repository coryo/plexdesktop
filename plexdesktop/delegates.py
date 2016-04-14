from PyQt5.QtWidgets import (QStyledItemDelegate, QApplication, QStyle,
                             QStyleOptionProgressBar, QProgressBar, QStyleOptionViewItem)
from PyQt5.QtGui import (QPixmap, QBrush, QPixmapCache, QColor, QPalette, QFont,
                         QFontMetrics, QPainter)
from PyQt5.QtCore import QSize, Qt, QRect, QPoint
from plexdesktop.utils import Location, hub_title, title, timestamp_from_ms
import plexdevices


class HubDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_bar = QProgressBar()

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        data = index.data(role=Qt.UserRole)
        if isinstance(data, plexdevices.hubs.Hub):
            return super().paint(painter, option, index)
        padding = 5
        icon_width = self.parent().iconSize().width()
        title_font = QFont(option.font.family(), 9)  # , weight=QFont.Bold)
        title_font_metrics = QFontMetrics(title_font)
        # Background
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        # Icon
        thumb = index.data(role=Qt.DecorationRole)
        if thumb is not None and not thumb.isNull():
            QApplication.style().drawItemPixmap(painter, option.rect,
                                                Qt.AlignLeft | Qt.AlignTop,
                                                thumb)
        else:
            thumb = QPixmap()
        # Title Line
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.setBrush(option.palette.highlightedText())
        else:
            painter.setBrush(option.palette.text())
        title_text = hub_title(data)
        painter.setFont(title_font)
        title_rect = QRect(option.rect.topLeft() + QPoint(icon_width + padding, 0),
                           option.rect.bottomRight())
        title_rect = QApplication.style().itemTextRect(title_font_metrics,
                                                       title_rect, Qt.AlignLeft,
                                                       True, title_text)
        QApplication.style().drawItemText(painter, title_rect,
                                          Qt.AlignLeft | Qt.TextWordWrap,
                                          option.palette, True, title_text)
        painter.restore()
        # Watched
        if isinstance(data, (plexdevices.media.Episode, plexdevices.media.Movie)):
            # Progress bar
            if data.in_progress:
                painter.save()
                progress = QStyleOptionProgressBar()
                progress.rect = QRect(option.rect.bottomLeft() - QPoint(0, padding), option.rect.bottomLeft() + QPoint(thumb.width(), 0))
                progress.state |= QStyle.State_Enabled
                progress.direction = QApplication.layoutDirection()
                progress.fontMetrics = QApplication.fontMetrics()
                progress.minimum = 0
                progress.maximum = 100
                progress.progress = 100 * data.view_offset / max(1, data.duration)
                QApplication.style().drawControl(QStyle.CE_ProgressBar, progress, painter, self.progress_bar)
                painter.restore()

    def sizeHint(self, option, index):
        item = index.data(role=Qt.UserRole)
        data = index.data(role=Qt.DecorationRole)
        if isinstance(item, plexdevices.hubs.Hub):
            return super().sizeHint(option, index)
        h = self.parent().iconSize().height() + 2 * 2 if data is None else data.height()
        return QSize(300, h)


class ListDelegate(QStyledItemDelegate):

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
        if option.state & QStyle.State_Selected:  # or option.state & QStyle.State_MouseOver:
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
        title_text = title(data)
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
        if isinstance(data, plexdevices.media.MediaItem) and data.markable:
            if not data.watched and not data.in_progress:
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
            if data.in_progress:
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
                progress.progress = 100 * data.view_offset / max(1, data.duration)
                progress.text = (timestamp_from_ms(data.view_offset) + " / " +
                                 timestamp_from_ms(data.duration))
                progress.textVisible = True
                QApplication.style().drawControl(QStyle.CE_ProgressBar, progress, painter, self.progress_bar)
                painter.restore()

    def sizeHint(self, option, index):
        data = index.data(role=Qt.UserRole)
        return QSize(300, self.parent().iconSize().height() + 2 * 2)

