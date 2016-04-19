from PyQt5.QtWidgets import (QStyledItemDelegate, QApplication, QStyle,
                             QStyleOptionProgressBar, QProgressBar, QStyleOptionViewItem)
from PyQt5.QtGui import (QPixmap, QBrush, QPixmapCache, QColor, QPalette, QFont,
                         QFontMetrics, QPainter, QPen, QPolygon)
from PyQt5.QtCore import QSize, Qt, QRect, QPoint
from plexdesktop.utils import Location, hub_title, title, timestamp_from_ms
import plexdevices


def placeholder_thumb_generator(title, qsize):
    """Returns a QPixmap of size qsize with the first letter of each word in title"""
    font = QFont('Helvetica', qsize.height() / 4, weight=QFont.Bold)
    font_metrics = QFontMetrics(font)
    rect = QRect(QPoint(0, 0), QPoint(qsize.width(), qsize.height()))
    center = QPoint(qsize.width() / 2, qsize.height() / 2)
    initials = ' '.join([x[0] for x in title.split(' ') if len(x) > 2])
    img = QPixmap(qsize)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setFont(font)
    p.setBrush(QBrush(QColor(50, 50, 50)))
    p.setPen(QColor(50, 50, 50))
    p.setRenderHint(QPainter.Antialiasing, True)
    p.drawEllipse(center, qsize.width() / 2 - 1, qsize.height() / 2 - 1)
    p.setPen(QColor(75, 75, 75))
    p.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, initials)
    return img


def draw_progress_bar(plex_item, pixmap, height=6):
    """draw a progress indicator on the bottom of pixmap with height pixels"""
    if (not isinstance(plex_item, (plexdevices.media.Episode, plexdevices.media.Movie)) or
            not plex_item.in_progress):
        return
    progress = plex_item.view_offset / max(1, plex_item.duration)
    p = QPainter(pixmap)
    rect = p.window()
    progress_rect = QRect(rect.bottomLeft() - QPoint(0, height), rect.bottomRight())
    progress_fill = QRect(progress_rect)
    progress_fill.setWidth(rect.width() * progress)
    p.fillRect(progress_rect, QBrush(Qt.black))
    p.fillRect(progress_fill, QBrush(QColor(204, 123, 25)))


def draw_unwatched_indicator(plex_item, pixmap, size=0.20):
    """draw a triangle on the top right of pixmap"""
    if (not isinstance(plex_item, (plexdevices.media.Episode, plexdevices.media.Movie)) or
            plex_item.watched or plex_item.in_progress):
        return
    p = QPainter(pixmap)
    rect = p.window()
    top_right = rect.topRight()
    size = pixmap.height() * size
    color = QColor(204, 123, 25)
    triangle = QPolygon([top_right, top_right - QPoint(size, 0),
                         top_right + QPoint(0, size)])
    p.setPen(QPen(QBrush(QColor(0, 0, 0, 120)), 6))
    p.drawLine(triangle.point(1), triangle.point(2))
    p.setBrush(QBrush(color))
    p.setPen(color)
    p.drawPolygon(triangle)


class TileDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        item = index.data(role=Qt.UserRole)
        if item is None:
            return
        icon_size = self.parent().iconSize()
        # Icon
        thumb = index.data(role=Qt.DecorationRole)
        if thumb is None or thumb.isNull():
            thumb = placeholder_thumb_generator(item.title, icon_size)
        scaled = thumb.scaledToHeight(icon_size.height(), Qt.SmoothTransformation)
        draw_progress_bar(item, scaled, height=6)
        draw_unwatched_indicator(item, scaled, size=0.20)
        QApplication.style().drawItemPixmap(painter, option.rect, Qt.AlignTop, scaled)
        # Title
        text_rect = QRect(option.rect.topLeft() + QPoint(0, icon_size.height()), option.rect.bottomRight())
        title_font = QFont(option.font.family(), 9, weight=QFont.Bold)
        title_font_metrics = QFontMetrics(title_font)
        painter.save()
        painter.setBrush(option.palette.highlightedText() if option.state & QStyle.State_Selected
                         else option.palette.text())
        title_text = item.title
        painter.setFont(title_font)
        QApplication.style().drawItemText(painter, text_rect,
                                          Qt.AlignLeft | Qt.TextWordWrap,
                                          option.palette, True, title_text)
        painter.restore()
        # Selection Frame
        if option.state & (QStyle.State_Selected | QStyle.State_MouseOver):
            thickness = 1
            painter.save()
            painter.setPen(QPen(QBrush(QColor(204, 123, 25)), thickness, join=Qt.MiterJoin))
            painter.drawRect(option.rect.left(), option.rect.top(),
                             option.rect.width() - thickness, icon_size.height())
            painter.restore()

    def sizeHint(self, option, index):
        icon_size = self.parent().iconSize()
        thumb = index.data(role=Qt.DecorationRole)
        default = QSize(icon_size.width(), icon_size.height() + 50)
        if thumb is None or thumb.isNull():
            # Try and figure out the width before we have the thumb ...
            item = index.data(role=Qt.UserRole)
            if isinstance(item, (plexdevices.media.Show, plexdevices.media.Season, plexdevices.media.Movie)):
                ar = 0.66  # posters are 2:3
                return QSize(icon_size.width() * ar, icon_size.height() + 50)
            elif isinstance(item, plexdevices.media.Album):
                return default
            try:
                ar = item.media[0].aspect_ratio
                w = icon_size.height() * ar
                return QSize(w, icon_size.height() + 50)
            except Exception:
                return default
        thumb_size = thumb.size()
        s = thumb_size.scaled(9999999, icon_size.height(), Qt.KeepAspectRatio)
        return QSize(s.width(), s.height() + 50)


class ListDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        item = index.data(role=Qt.UserRole)
        title_font = QFont(option.font.family(), 9, weight=QFont.Bold)
        title_font_metrics = QFontMetrics(title_font)
        summary_font = QFont(option.font.family(), 7)
        summary_font_metrics = QFontMetrics(summary_font)

        if item.__class__.__name__ == 'HubsItem':
            title_text = hub_title(item)
        elif isinstance(item, plexdevices.hubs.Hub):
            title_text = item.title.upper()
        else:
            title_text = title(item)

        # # Background
        # if option.state & QStyle.State_Selected:
        #     painter.fillRect(option.rect, option.palette.highlight())

        # Icon
        if isinstance(item, plexdevices.hubs.Hub):
            scaled = QSize(0, 0)
        else:
            thumb = index.data(role=Qt.DecorationRole)
            if thumb is None or thumb.isNull():
                thumb = placeholder_thumb_generator(title_text, self.parent().iconSize())
            scaled = thumb.scaledToHeight(self.parent().iconSize().width(), Qt.SmoothTransformation)
            draw_progress_bar(item, scaled, height=6)
            draw_unwatched_indicator(item, scaled, size=0.20)
            QApplication.style().drawItemPixmap(painter, option.rect,
                                                Qt.AlignLeft | Qt.AlignVCenter,
                                                scaled)
        # Selection Frame
        if option.state & (QStyle.State_Selected | QStyle.State_MouseOver):
            thickness = 1
            painter.save()
            painter.setPen(QPen(QBrush(QColor(204, 123, 25)), thickness, join=Qt.MiterJoin))
            painter.drawRect(QRect(option.rect.topLeft(), option.rect.bottomRight() - QPoint(1, 1)))
            painter.restore()
        # Title Line
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.setBrush(option.palette.highlightedText())
        else:
            painter.setBrush(option.palette.text())
        painter.setFont(title_font)
        title_rect = QRect(option.rect.topLeft() + QPoint(scaled.width() + 5, 0),
                           option.rect.bottomRight())
        title_rect = QApplication.style().itemTextRect(title_font_metrics,
                                                       title_rect, Qt.AlignLeft,
                                                       True, title_text)
        QApplication.style().drawItemText(painter, title_rect,
                                          Qt.AlignLeft | Qt.TextWordWrap,
                                          option.palette, True, title_text)
        painter.restore()

    def sizeHint(self, option, index):
        if isinstance(index.data(role=Qt.UserRole), plexdevices.hubs.Hub):
            return super().sizeHint(option, index)
        return QSize(300, self.parent().iconSize().height() + 2 * 2)

