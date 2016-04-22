from PyQt5.QtWidgets import QStyledItemDelegate, QApplication, QStyle
from PyQt5.QtGui import (QPixmap, QBrush, QColor, QFont, QFontMetrics, QPainter,
                         QPen, QPolygon, QTextLayout, QTextLine)
from PyQt5.QtCore import QSize, Qt, QRect, QPoint
from plexdesktop.utils import hub_title, title, timestamp_from_ms
from plexdesktop.settings import Settings
import plexdevices


class BaseDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = Settings()
        browser_font_size = int(s.value('browser_font', 9))
        self.title_font = QFont('Open Sans Extrabold', browser_font_size)
        self.summary_font = QFont('Open Sans', browser_font_size * 0.95, QFont.Bold)
        self.title_font_metrics = QFontMetrics(self.title_font)
        self.summary_font_metrics = QFontMetrics(self.title_font)


def placeholder_thumb_generator(title, qsize):
    """Returns a QPixmap of size qsize with the first letter of each word in title"""
    circle_color = QColor(50, 50, 50)
    text_color = QColor(75, 75, 75)
    font = QFont('Open Sans', qsize.height() / 4, weight=QFont.Bold)
    font_metrics = QFontMetrics(font)
    rect = QRect(QPoint(0, 0), QPoint(qsize.width(), qsize.height()))
    center = QPoint(qsize.width() / 2, qsize.height() / 2)
    initials = ' '.join([x[0] for x in title.split(' ') if len(x) > 2])
    img = QPixmap(qsize)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setFont(font)
    p.setBrush(QBrush(circle_color))
    p.setPen(circle_color)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.drawEllipse(center, qsize.width() / 2 - 1, qsize.height() / 2 - 1)
    p.setPen(text_color)
    p.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, initials)
    return img


def draw_progress_bar(plex_item, pixmap, height=6):
    """draw a progress indicator on the bottom of pixmap with height pixels"""
    if (not isinstance(plex_item, (plexdevices.media.Episode, plexdevices.media.Movie)) or
            not plex_item.in_progress):
        return
    progress_color = QColor(204, 123, 25)
    progress = plex_item.view_offset / max(1, plex_item.duration)
    p = QPainter(pixmap)
    rect = p.window()
    progress_rect = QRect(rect.bottomLeft() - QPoint(0, height), rect.bottomRight())
    progress_fill = QRect(progress_rect)
    progress_fill.setWidth(rect.width() * progress)
    p.fillRect(progress_rect, QBrush(Qt.black))
    p.fillRect(progress_fill, QBrush(progress_color))


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


def elide_text(painter, rect, string):
    """paint `string` with `painter` inside `rect`"""
    font_metrics = painter.fontMetrics()
    line_spacing = font_metrics.lineSpacing()
    y = 0
    text_layout = QTextLayout(string, painter.font())
    text_layout.beginLayout()
    while True:
        line = text_layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(rect.width())
        next_line_y = y + line_spacing
        if rect.height() >= next_line_y + line_spacing:
            line.draw(painter, QPoint(rect.left(), rect.top() + y))
            y = next_line_y
        else:
            last_line = string[line.textStart():]
            elided_last_line = font_metrics.elidedText(last_line, Qt.ElideRight,
                                                       rect.width())
            painter.drawText(QPoint(rect.left(),
                                    rect.top() + y + font_metrics.ascent()),
                             elided_last_line)
            line = text_layout.createLine()
            break


class TileDelegate(BaseDelegate):

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
        scaled = thumb.scaledToHeight(icon_size.height(), Qt.FastTransformation)
        draw_progress_bar(item, scaled, height=6)
        draw_unwatched_indicator(item, scaled, size=0.20)
        QApplication.style().drawItemPixmap(painter, option.rect, Qt.AlignTop, scaled)

        # Title
        title_font = QFont(option.font.family(), 9, weight=QFont.Bold)

        painter.save()
        painter.setBrush(option.palette.highlightedText() if option.state & QStyle.State_Selected
                         else option.palette.text())
        # title_text = item.title
        painter.setFont(self.title_font)

        _x = option.rect.topLeft() + QPoint(0, icon_size.height())
        line1_rect = QRect(_x, _x + QPoint(option.rect.width(), + painter.fontMetrics().height()))

        if isinstance(item, plexdevices.media.Episode):
            line1_text = item.grandparent_title
        elif isinstance(item, plexdevices.media.Album):
            line1_text = item.parent_title
        else:
            line1_text = item.title

        elided_text = painter.fontMetrics().elidedText(line1_text, Qt.ElideRight, line1_rect.width())
        painter.drawText(line1_rect, Qt.AlignLeft, elided_text)
        painter.restore()

        # Line 2
        if isinstance(item, (plexdevices.media.Episode, plexdevices.media.Movie,
                             plexdevices.media.Album, plexdevices.media.Track)):
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)
            line2_rect = QRect(line1_rect.bottomLeft(),
                               line1_rect.bottomRight() + QPoint(0, painter.fontMetrics().height()))
            if isinstance(item, plexdevices.media.Episode):
                line2_text = item.title
            elif isinstance(item, plexdevices.media.Movie):
                line2_text = str(item.year)
            elif isinstance(item, plexdevices.media.Album):
                line2_text = item.title
            elif isinstance(item, plexdevices.media.Track):
                line2_text = timestamp_from_ms(item.duration, minimal=True)
            elided_text = painter.fontMetrics().elidedText(line2_text, Qt.ElideRight, line2_rect.width())
            painter.drawText(line2_rect, Qt.AlignLeft, elided_text)
            painter.restore()

        # Line 3
        if isinstance(item, plexdevices.media.Episode):
            line3_text = 'S{} E{}'.format(item.parent_index, item.index)
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)
            line3_rect = QRect(line2_rect.bottomLeft(),
                               line2_rect.bottomRight() + QPoint(0, painter.fontMetrics().height()))
            elided_text = painter.fontMetrics().elidedText(line3_text, Qt.ElideRight, line3_rect.width())
            painter.drawText(line3_rect, Qt.AlignLeft, elided_text)
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
        text_height = self.title_font_metrics.height() + self.summary_font_metrics.height() * 2
        thumb = index.data(role=Qt.DecorationRole)
        default = QSize(icon_size.width(), icon_size.height() + text_height)
        if thumb is None or thumb.isNull():
            # Try and figure out the width before we have the thumb ...
            item = index.data(role=Qt.UserRole)
            if isinstance(item, (plexdevices.media.Show, plexdevices.media.Season, plexdevices.media.Movie)):
                ar = 0.66  # posters are 2:3
                return QSize(icon_size.width() * ar, icon_size.height() + text_height)
            elif isinstance(item, plexdevices.media.Album):
                return default
            try:
                ar = item.media[0].aspect_ratio
                w = icon_size.height() * ar
                return QSize(w, icon_size.height() + text_height)
            except Exception:
                return default
        thumb_size = thumb.size()
        s = thumb_size.scaled(9999999, icon_size.height(), Qt.KeepAspectRatio)
        return QSize(s.width(), s.height() + text_height)


class ListDelegate(BaseDelegate):

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        item = index.data(role=Qt.UserRole)

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
            scaled = thumb.scaledToHeight(self.parent().iconSize().width(), Qt.FastTransformation)
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
        painter.setFont(self.title_font)
        title_rect = QRect(option.rect.topLeft() + QPoint(scaled.width() + 5, 0),
                           option.rect.topRight() + QPoint(0, painter.fontMetrics().height()))
        elide_text(painter, title_rect, title_text)
        painter.restore()

        # Right Title
        if isinstance(item, plexdevices.media.Track):
            line_text = timestamp_from_ms(item.duration, minimal=True)
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)
            painter.drawText(title_rect, Qt.AlignRight, line_text)
            painter.restore()

        # Summary text. wrap and elide
        if hasattr(item, 'summary'):
            summary_text = item.summary
            if summary_text is None:
                return
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)
            summary_rect = QRect(title_rect.bottomLeft(), option.rect.bottomRight())
            elide_text(painter, summary_rect, summary_text)
            painter.restore()

    def sizeHint(self, option, index):
        if isinstance(index.data(role=Qt.UserRole), plexdevices.hubs.Hub):
            return super().sizeHint(option, index)
        return QSize(300, self.parent().iconSize().height() + 2 * 2)
