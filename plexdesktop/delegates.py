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

import plexdevices

import PyQt5.QtWidgets
import PyQt5.QtGui
import PyQt5.QtCore

from plexdesktop.utils import hub_title, title, timestamp_from_ms
from plexdesktop.settings import Settings

Qt = PyQt5.QtCore.Qt


class BaseDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = Settings()
        browser_font_size = int(s.value('browser_font', 9))
        self.title_font = PyQt5.QtGui.QFont('Open Sans Extrabold', browser_font_size)
        self.summary_font = PyQt5.QtGui.QFont('Open Sans', browser_font_size * 0.95, PyQt5.QtGui.QFont.Bold)
        self.title_font_metrics = PyQt5.QtGui.QFontMetrics(self.title_font)
        self.summary_font_metrics = PyQt5.QtGui.QFontMetrics(self.title_font)


def placeholder_thumb_generator(title, size=150):
    """Returns a PyQt5.QtGui.QPixmap of size with the first letter of each word in title"""
    initials = ' '.join([x[0] for x in title.split(' ') if len(x) > 2])
    key = 'placeholder' + initials
    img = PyQt5.QtGui.QPixmapCache.find(key)
    if img:
        return img
    qsize = PyQt5.QtCore.QSize(size, size)
    circle_color = PyQt5.QtGui.QColor(50, 50, 50)
    text_color = PyQt5.QtGui.QColor(75, 75, 75)
    font = PyQt5.QtGui.QFont('Open Sans', qsize.height() / 4, weight=PyQt5.QtGui.QFont.Bold)
    # font_metrics = PyQt5.QtGui.QFontMetrics(font)
    rect = PyQt5.QtCore.QRect(PyQt5.QtCore.QPoint(0, 0), PyQt5.QtCore.QPoint(qsize.width(), qsize.height()))
    center = PyQt5.QtCore.QPoint(qsize.width() / 2, qsize.height() / 2)
    img = PyQt5.QtGui.QPixmap(qsize)
    img.fill(Qt.transparent)
    p = PyQt5.QtGui.QPainter(img)
    p.setFont(font)
    p.setBrush(PyQt5.QtGui.QBrush(circle_color))
    p.setPen(circle_color)
    p.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing, True)
    p.drawEllipse(center, qsize.width() / 2 - 1, qsize.height() / 2 - 1)
    p.setPen(text_color)
    p.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, initials)
    PyQt5.QtGui.QPixmapCache.insert(key, img)
    return img


def draw_progress_bar(plex_item, pixmap, height=6):
    """draw a progress indicator on the bottom of pixmap with height pixels"""
    if (not isinstance(plex_item, (plexdevices.media.Episode, plexdevices.media.Movie)) or
            not plex_item.in_progress):
        return
    progress_color = PyQt5.QtGui.QColor(204, 123, 25)
    progress = plex_item.view_offset / max(1, plex_item.duration)
    p = PyQt5.QtGui.QPainter(pixmap)
    rect = p.window()
    progress_rect = PyQt5.QtCore.QRect(rect.bottomLeft() - PyQt5.QtCore.QPoint(0, height), rect.bottomRight())
    progress_fill = PyQt5.QtCore.QRect(progress_rect)
    progress_fill.setWidth(rect.width() * progress)
    p.fillRect(progress_rect, PyQt5.QtGui.QBrush(Qt.black))
    p.fillRect(progress_fill, PyQt5.QtGui.QBrush(progress_color))


def draw_unwatched_indicator(plex_item, pixmap, size=0.20):
    """draw a triangle on the top right of pixmap"""
    if (not isinstance(plex_item, (plexdevices.media.Episode, plexdevices.media.Movie)) or
            plex_item.watched or plex_item.in_progress):
        return
    p = PyQt5.QtGui.QPainter(pixmap)
    rect = p.window()
    top_right = rect.topRight()
    size = pixmap.height() * size
    color = PyQt5.QtGui.QColor(204, 123, 25)
    triangle = PyQt5.QtGui.QPolygon([top_right, top_right - PyQt5.QtCore.QPoint(size, 0),
                                     top_right + PyQt5.QtCore.QPoint(0, size)])
    p.setPen(PyQt5.QtGui.QPen(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor(0, 0, 0, 120)), 6))
    p.drawLine(triangle.point(1), triangle.point(2))
    p.setBrush(PyQt5.QtGui.QBrush(color))
    p.setPen(color)
    p.drawPolygon(triangle)


def elide_text(painter, rect, string):
    """paint `string` with `painter` inside `rect`"""
    font_metrics = painter.fontMetrics()
    line_spacing = font_metrics.lineSpacing()
    y = 0
    text_layout = PyQt5.QtGui.QTextLayout(string, painter.font())
    text_layout.beginLayout()
    while True:
        line = text_layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(rect.width())
        next_line_y = y + line_spacing
        if rect.height() >= next_line_y + line_spacing:
            line.draw(painter, PyQt5.QtCore.QPoint(rect.left(), rect.top() + y))
            y = next_line_y
        else:
            last_line = string[line.textStart():]
            elided_last_line = font_metrics.elidedText(last_line, Qt.ElideRight,
                                                       rect.width())
            painter.drawText(PyQt5.QtCore.QPoint(rect.left(),
                                                 rect.top() + y + font_metrics.ascent()),
                             elided_last_line)
            line = text_layout.createLine()
            break


class TileDelegate(BaseDelegate):

    def summary_line_count(self, item):
        summary_lines = 0
        if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Album,
                             plexdevices.media.Track, plexdevices.media.Episode)):
            if isinstance(item, plexdevices.media.Episode):
                summary_lines = 2
            else:
                summary_lines = 1
        return summary_lines

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        item = index.data(role=Qt.UserRole)
        if item is None:
            return

        icon_size = self.parent().iconSize()

        summary_lines = self.summary_line_count(item)

        icon_rect = PyQt5.QtCore.QRect(
            option.rect.topLeft(),
            option.rect.topRight() + PyQt5.QtCore.QPoint(0, icon_size.height())
        )

        background_rect = PyQt5.QtCore.QRect(
            option.rect.topLeft(),
            icon_rect.bottomRight() +
            PyQt5.QtCore.QPoint(0, self.title_font_metrics.height() +
                                self.summary_font_metrics.height() * summary_lines)
        )

        # Background
        if option.state & PyQt5.QtWidgets.QStyle.State_Selected:
            painter.fillRect(background_rect, option.palette.highlight())
        elif option.state & PyQt5.QtWidgets.QStyle.State_MouseOver:
            brush = option.palette.base()
            if brush.color().lightness() > 127:
                brush.setColor(brush.color().darker(120))
            else:
                brush.setColor(brush.color().lighter(120))
            painter.fillRect(background_rect, brush)

        # Icon
        thumb = index.data(role=Qt.DecorationRole)
        if not item.thumb:
            thumb = placeholder_thumb_generator(item.title)
            thumb = thumb.scaled(icon_size)
        if not thumb.isNull():
            scaled = thumb.scaledToHeight(icon_size.height(), Qt.SmoothTransformation)
            draw_progress_bar(item, scaled, height=6)
            draw_unwatched_indicator(item, scaled, size=0.20)
            PyQt5.QtWidgets.QApplication.style().drawItemPixmap(painter, option.rect, Qt.AlignTop, scaled)

        # Title
        # title_font = QFont(option.font.family(), 9, weight=QFont.Bold)

        painter.save()
        painter.setBrush(option.palette.highlightedText() if option.state & PyQt5.QtWidgets.QStyle.State_Selected
                         else option.palette.text())
        # title_text = item.title
        painter.setFont(self.title_font)

        _x = option.rect.topLeft() + PyQt5.QtCore.QPoint(0, icon_size.height())
        line1_rect = PyQt5.QtCore.QRect(_x, _x + PyQt5.QtCore.QPoint(option.rect.width(), + painter.fontMetrics().height()))

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
        if summary_lines:
            painter.save()
            if painter.pen().color().lightness() > 127:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().darker()))
            else:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().lighter()))

            painter.setFont(self.summary_font)
            line2_rect = PyQt5.QtCore.QRect(line1_rect.bottomLeft(),
                                            line1_rect.bottomRight() + PyQt5.QtCore.QPoint(0, painter.fontMetrics().height()))
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
        if summary_lines >= 2:
            line3_text = 'S{} E{}'.format(item.parent_index, item.index)
            painter.save()
            if painter.pen().color().lightness() > 127:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().darker()))
            else:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().lighter()))
            painter.setFont(self.summary_font)
            line3_rect = PyQt5.QtCore.QRect(line2_rect.bottomLeft(),
                                            line2_rect.bottomRight() + PyQt5.QtCore.QPoint(0, painter.fontMetrics().height()))
            elided_text = painter.fontMetrics().elidedText(line3_text, Qt.ElideRight, line3_rect.width())
            painter.drawText(line3_rect, Qt.AlignLeft, elided_text)
            painter.restore()

    def sizeHint(self, option, index):
        icon_size = self.parent().iconSize()
        item = index.data(role=Qt.UserRole)
        summary_lines = self.summary_line_count(item)

        text_height = self.title_font_metrics.height() + self.summary_font_metrics.height() * summary_lines
        thumb = index.data(role=Qt.DecorationRole)
        default = PyQt5.QtCore.QSize(icon_size.width(), icon_size.height() + text_height)
        if thumb is None or thumb.isNull():
            # Try and figure out the width before we have the thumb ...
            if isinstance(item, (plexdevices.media.Show, plexdevices.media.Season, plexdevices.media.Movie)):
                ar = 0.66  # posters are 2:3
                return PyQt5.QtCore.QSize(icon_size.width() * ar, icon_size.height() + text_height)
            elif isinstance(item, plexdevices.media.Album):
                return default
            try:
                ar = item.media[0].aspect_ratio
                w = icon_size.height() * ar
                return PyQt5.QtCore.QSize(w, icon_size.height() + text_height)
            except Exception:
                return default
        thumb_size = thumb.size()
        s = thumb_size.scaled(9999999, icon_size.height(), Qt.KeepAspectRatio)
        return PyQt5.QtCore.QSize(s.width(), s.height() + text_height)


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

        # Background
        if option.state & PyQt5.QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & PyQt5.QtWidgets.QStyle.State_MouseOver:
            brush = option.palette.base()
            if brush.color().lightness() > 127:
                brush.setColor(brush.color().darker(120))
            else:
                brush.setColor(brush.color().lighter(120))
            painter.fillRect(option.rect, brush)

        # Icon
        if isinstance(item, plexdevices.hubs.Hub):
            scaled = PyQt5.QtCore.QSize(0, 0)
        else:
            thumb = index.data(role=Qt.DecorationRole)
            if not item.thumb:
                thumb = placeholder_thumb_generator(title_text)
                thumb = thumb.scaled(self.parent().iconSize())
            if thumb and not thumb.isNull():
                scaled = thumb.scaledToHeight(self.parent().iconSize().width(), Qt.SmoothTransformation)
                draw_progress_bar(item, scaled, height=6)
                draw_unwatched_indicator(item, scaled, size=0.20)
                PyQt5.QtWidgets.QApplication.style().drawItemPixmap(painter, option.rect,
                                                                    Qt.AlignLeft | Qt.AlignVCenter,
                                                                    scaled)
            else:
                scaled = self.parent().iconSize()

        # Title Line
        painter.save()
        if option.state & PyQt5.QtWidgets.QStyle.State_Selected:
            painter.setBrush(option.palette.highlightedText())
        else:
            painter.setBrush(option.palette.text())
        painter.setFont(self.title_font)
        title_rect = PyQt5.QtCore.QRect(option.rect.topLeft() + PyQt5.QtCore.QPoint(scaled.width() + 5, 0),
                                        option.rect.topRight() + PyQt5.QtCore.QPoint(0, painter.fontMetrics().height()))
        elide_text(painter, title_rect, title_text)
        painter.restore()

        # Right Title
        if isinstance(item, plexdevices.media.Track):
            line_text = timestamp_from_ms(item.duration, minimal=True)
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().darker(150)))
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
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(PyQt5.QtGui.QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)
            summary_rect = PyQt5.QtCore.QRect(title_rect.bottomLeft(), option.rect.bottomRight())
            elide_text(painter, summary_rect, summary_text)
            painter.restore()

    def sizeHint(self, option, index):
        if isinstance(index.data(role=Qt.UserRole), plexdevices.hubs.Hub):
            return super().sizeHint(option, index)
        return PyQt5.QtCore.QSize(300, self.parent().iconSize().height() + 2)
