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

from PyQt5 import QtWidgets, QtGui, QtCore

from plexdesktop.utils import hub_title, title, timestamp_from_ms
from plexdesktop.settings import Settings


class BaseDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = Settings()
        browser_font_size = int(s.value('browser_font', 9))
        self.title_font = QtGui.QFont('Open Sans Extrabold', browser_font_size)
        self.summary_font = QtGui.QFont('Open Sans',
                                        browser_font_size * 0.95,
                                        QtGui.QFont.Bold)
        self.title_font_metrics = QtGui.QFontMetrics(self.title_font)
        self.summary_font_metrics = QtGui.QFontMetrics(self.title_font)
        self.last_icon_size = self.parent().iconSize().height()


def placeholder_thumb_generator(title, size=150):
    """Returns a QPixmap of size with the first letter of each word in title"""
    initials = ' '.join([x[0] for x in title.split(' ') if len(x) > 2])
    key = 'placeholder' + initials
    img = QtGui.QPixmapCache.find(key)
    if img:
        return img
    qsize = QtCore.QSize(size, size)
    circle_color = QtGui.QColor(50, 50, 50)
    text_color = QtGui.QColor(75, 75, 75)
    rect = QtCore.QRect(QtCore.QPoint(0, 0), QtCore.QPoint(size, size))
    center = QtCore.QPoint(size / 2, size / 2)
    img = QtGui.QPixmap(qsize)
    img.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(img)
    p.setFont(QtGui.QFont('Open Sans', size / 4, weight=QtGui.QFont.Bold))
    p.setBrush(QtGui.QBrush(circle_color))
    p.setPen(circle_color)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    p.drawEllipse(center, size / 2 - 1, size / 2 - 1)
    p.setPen(text_color)
    p.drawText(rect, QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter, initials)
    QtGui.QPixmapCache.insert(key, img)
    return img


def draw_progress_bar(plex_item, pixmap, height=6):
    """draw a progress indicator on the bottom of pixmap with height pixels"""
    if not hasattr(plex_item, 'in_progress'):
        return
    if not plex_item.in_progress:
        return
    progress_color = QtGui.QColor(204, 123, 25)
    progress = plex_item.view_offset / max(1, plex_item.duration)
    p = QtGui.QPainter(pixmap)
    rect = p.window()
    progress_rect = QtCore.QRect(rect.bottomLeft() - QtCore.QPoint(0, height),
                                 rect.bottomRight())
    progress_fill = QtCore.QRect(progress_rect)
    progress_fill.setWidth(rect.width() * progress)
    p.fillRect(progress_rect, QtGui.QBrush(QtCore.Qt.black))
    p.fillRect(progress_fill, QtGui.QBrush(progress_color))


def draw_unwatched_indicator(plex_item, pixmap, size=0.20):
    """draw a triangle on the top right of pixmap"""
    if not hasattr(plex_item, 'watched') and not hasattr(plex_item, 'in_progress'):
        return
    if plex_item.watched or plex_item.in_progress:
        return
    p = QtGui.QPainter(pixmap)
    rect = p.window()
    top_right = rect.topRight()
    size = pixmap.height() * size
    color = QtGui.QColor(204, 123, 25)
    triangle = QtGui.QPolygon([top_right, top_right - QtCore.QPoint(size, 0),
                               top_right + QtCore.QPoint(0, size)])
    p.setPen(QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0, 120)), 6))
    p.drawLine(triangle.point(1), triangle.point(2))
    p.setBrush(QtGui.QBrush(color))
    p.setPen(color)
    p.drawPolygon(triangle)


def elide_text(painter, rect, string):
    """paint `string` with `painter` inside `rect`"""
    font_metrics = painter.fontMetrics()
    line_spacing = font_metrics.lineSpacing()
    y = 0
    text_layout = QtGui.QTextLayout(string, painter.font())
    text_layout.beginLayout()
    while True:
        line = text_layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(rect.width())
        next_line_y = y + line_spacing
        if rect.height() >= next_line_y + line_spacing:
            line.draw(painter, QtCore.QPoint(rect.left(), rect.top() + y))
            y = next_line_y
        else:
            last_line = string[line.textStart():]
            elided_last_line = font_metrics.elidedText(
                last_line, QtCore.Qt.ElideRight, rect.width())
            painter.drawText(QtCore.QPoint(rect.left(),
                             rect.top() + y + font_metrics.ascent()),
                             elided_last_line)
            line = text_layout.createLine()
            break


# class TileDelegate(BaseDelegate):

#     def summary_line_count(self, item):
#         summary_lines = 0
#         if isinstance(item,
#                       (plexdevices.media.Movie, plexdevices.media.Album,
#                        plexdevices.media.Track, plexdevices.media.Episode)):
#             if isinstance(item, plexdevices.media.Episode):
#                 summary_lines = 2
#             else:
#                 summary_lines = 1
#         return summary_lines

#     def paint(self, painter, option, index):
#         self.initStyleOption(option, index)
#         item = index.data(role=QtCore.Qt.UserRole)
#         if item is None:
#             return

#         icon_size = self.parent().iconSize()

#         summary_lines = self.summary_line_count(item)

#         icon_rect = QtCore.QRect(
#             option.rect.topLeft(),
#             option.rect.topRight() + QtCore.QPoint(0, icon_size.height())
#         )

#         background_rect = QtCore.QRect(
#             option.rect.topLeft(),
#             icon_rect.bottomRight() +
#             QtCore.QPoint(0, self.title_font_metrics.height() +
#                           self.summary_font_metrics.height() * summary_lines)
#         )

#         # Background
#         if option.state & QtWidgets.QStyle.State_Selected:
#             painter.fillRect(background_rect, option.palette.highlight())
#         elif option.state & QtWidgets.QStyle.State_MouseOver:
#             brush = option.palette.base()
#             if brush.color().lightness() > 127:
#                 brush.setColor(brush.color().darker(120))
#             else:
#                 brush.setColor(brush.color().lighter(120))
#             painter.fillRect(background_rect, brush)

#         # Icon
#         thumb = index.data(role=QtCore.Qt.DecorationRole)
#         if not item.thumb:
#             thumb = placeholder_thumb_generator(item.title)
#             thumb = thumb.scaled(icon_size)
#         if not thumb.isNull():
#             scaled = thumb.scaledToHeight(icon_size.height(),
#                                           QtCore.Qt.SmoothTransformation)
#             draw_progress_bar(item, scaled, height=6)
#             draw_unwatched_indicator(item, scaled, size=0.20)
#             QtWidgets.QApplication.style().drawItemPixmap(
#                 painter, option.rect, QtCore.Qt.AlignTop, scaled)

#         # Title
#         # title_font = QtGui.QFont(option.font.family(), 9, weight=QtGui.QFont.Bold)

#         painter.save()
#         painter.setBrush(option.palette.highlightedText() if
#                          option.state & QtWidgets.QStyle.State_Selected else
#                          option.palette.text())
#         # title_text = item.title
#         painter.setFont(self.title_font)

#         _x = option.rect.topLeft() + QtCore.QPoint(0, icon_size.height())
#         line1_rect = QtCore.QRect(_x,
#                                   _x + QtCore.QPoint(option.rect.width(),
#                                                      painter.fontMetrics().height()))

#         if isinstance(item, plexdevices.media.Episode):
#             line1_text = item.grandparent_title
#         elif isinstance(item, plexdevices.media.Album):
#             line1_text = item.parent_title
#         else:
#             line1_text = item.title

#         elided_text = painter.fontMetrics().elidedText(
#             line1_text, QtCore.Qt.ElideRight, line1_rect.width())
#         painter.drawText(line1_rect, QtCore.Qt.AlignLeft, elided_text)
#         painter.restore()

#         # Line 2
#         if summary_lines:
#             painter.save()
#             if painter.pen().color().lightness() > 127:
#                 painter.setPen(QtGui.QPen(painter.pen().color().darker()))
#             else:
#                 painter.setPen(QtGui.QPen(painter.pen().color().lighter()))

#             painter.setFont(self.summary_font)
#             line2_rect = QtCore.QRect(line1_rect.bottomLeft(),
#                                       line1_rect.bottomRight() +
#                                       QtCore.QPoint(0, painter.fontMetrics().height()))
#             if isinstance(item, plexdevices.media.Episode):
#                 line2_text = item.title
#             elif isinstance(item, plexdevices.media.Movie):
#                 line2_text = str(item.year)
#             elif isinstance(item, plexdevices.media.Album):
#                 line2_text = item.title
#             elif isinstance(item, plexdevices.media.Track):
#                 line2_text = timestamp_from_ms(item.duration, minimal=True)
#             elided_text = painter.fontMetrics().elidedText(
#                 line2_text, QtCore.Qt.ElideRight, line2_rect.width())
#             painter.drawText(line2_rect, QtCore.Qt.AlignLeft, elided_text)
#             painter.restore()

#         # Line 3
#         if summary_lines >= 2:
#             line3_text = 'S{} E{}'.format(item.parent_index, item.index)
#             painter.save()
#             if painter.pen().color().lightness() > 127:
#                 painter.setPen(QtGui.QPen(painter.pen().color().darker()))
#             else:
#                 painter.setPen(QtGui.QPen(painter.pen().color().lighter()))
#             painter.setFont(self.summary_font)
#             line3_rect = QtCore.QRect(line2_rect.bottomLeft(),
#                                       line2_rect.bottomRight() +
#                                       QtCore.QPoint(0, painter.fontMetrics().height()))
#             elided_text = painter.fontMetrics().elidedText(
#                 line3_text, QtCore.Qt.ElideRight, line3_rect.width())
#             painter.drawText(line3_rect, QtCore.Qt.AlignLeft, elided_text)
#             painter.restore()

#     def sizeHint(self, option, index):
#         icon_size = self.parent().iconSize()
#         item = index.data(role=QtCore.Qt.UserRole)
#         summary_lines = self.summary_line_count(item)

#         text_height = (self.title_font_metrics.height() +
#                        self.summary_font_metrics.height() * summary_lines)
#         thumb = index.data(role=QtCore.Qt.DecorationRole)
#         default = QtCore.QSize(icon_size.width(), icon_size.height() + text_height)
#         if thumb is None or thumb.isNull():
#             # Try and figure out the width before we have the thumb ...
#             if isinstance(item, (plexdevices.media.Show,
#                                  plexdevices.media.Season,
#                                  plexdevices.media.Movie)):
#                 ar = 0.66  # posters are 2:3
#                 return QtCore.QSize(icon_size.width() * ar, icon_size.height() +
#                                     text_height)
#             elif isinstance(item, plexdevices.media.Album):
#                 return default
#             try:
#                 ar = item.media[0].aspect_ratio
#                 w = icon_size.height() * ar
#                 return QtCore.QSize(w, icon_size.height() + text_height)
#             except Exception:
#                 return default
#         thumb_size = thumb.size()
#         s = thumb_size.scaled(9999999, icon_size.height(), QtCore.Qt.KeepAspectRatio)
#         return QtCore.QSize(s.width(), s.height() + text_height)


class ListDelegate(BaseDelegate):

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        item = index.data(role=QtCore.Qt.UserRole)

        icon_size = self.parent().iconSize()
        thumb_rect = QtCore.QRect(option.rect.topLeft(), icon_size)

        if item.__class__.__name__ == 'HubsItem':
            title_text = hub_title(item)
        elif isinstance(item, plexdevices.hubs.Hub):
            title_text = item.title.upper()
        else:
            title_text = title(item)

        # Background
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QtWidgets.QStyle.State_MouseOver:
            brush = option.palette.base()
            if brush.color().lightness() > 127:
                brush.setColor(brush.color().darker(120))
            else:
                brush.setColor(brush.color().lighter(120))
            painter.fillRect(option.rect, brush)

        # Icon
        thumb = index.data(role=QtCore.Qt.DecorationRole)
        if thumb and not thumb.isNull():
            if thumb.width() > thumb.height():
                scaled = thumb.scaledToHeight(
                    icon_size.height(), QtCore.Qt.SmoothTransformation)
                scaled = scaled.copy(scaled.width() / 2 - icon_size.height() / 2, 0,
                                     icon_size.height(), icon_size.height())
            elif thumb.width() < thumb.height():
                scaled = thumb.scaledToWidth(
                    icon_size.height(), QtCore.Qt.SmoothTransformation)
                scaled = scaled.copy(0, scaled.height() / 2 - icon_size.height() / 2,
                                     icon_size.height(), icon_size.height())
            else:
                scaled = thumb.scaledToHeight(
                    icon_size.height(), QtCore.Qt.SmoothTransformation)
            if item.markable:
                draw_progress_bar(item, scaled, height=6)
                draw_unwatched_indicator(item, scaled, size=0.20)
            QtWidgets.QApplication.style().drawItemPixmap(
                painter, option.rect,
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                scaled)

        text_rect = QtCore.QRect(option.rect.topLeft(), option.rect.bottomRight())
        text_rect.setLeft(thumb_rect.right() + 4)

        # Right Title
        if hasattr(item, 'duration'):
            line_text = timestamp_from_ms(item.duration, minimal=True)
            painter.save()
            if painter.pen().color().value() < 128:
                painter.setPen(QtGui.QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QtGui.QPen(painter.pen().color().darker(150)))
            painter.setFont(self.summary_font)

            painter.drawText(text_rect, QtCore.Qt.AlignRight, line_text)

            bounding_rect = painter.boundingRect(text_rect, QtCore.Qt.AlignRight, line_text)
            text_rect.setRight(bounding_rect.left())
            painter.restore()

        # Title Line
        painter.save()
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.setBrush(option.palette.highlightedText())
        else:
            painter.setBrush(option.palette.text())
        painter.setFont(self.title_font)

        elided_text = painter.fontMetrics().elidedText(
            title_text, QtCore.Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, QtCore.Qt.AlignLeft, elided_text)

        text_rect.setRight(option.rect.right())
        text_rect.setTop(option.rect.top() + painter.fontMetrics().height())

        painter.restore()

        # Summary text. wrap and elide
        if hasattr(item, 'summary'):
            painter.save()
            painter.setFont(self.summary_font)
            summary_text = item.summary
            if not summary_text or text_rect.height() < painter.fontMetrics().height():
                painter.restore()
                return
            if painter.pen().color().value() < 128:
                painter.setPen(QtGui.QPen(painter.pen().color().lighter()))
            else:
                painter.setPen(QtGui.QPen(painter.pen().color().darker(150)))
            elide_text(painter, text_rect, summary_text)
            painter.restore()

        self.last_icon_size = self.parent().iconSize().height()

    def sizeHint(self, option, index):
        if isinstance(index.data(role=QtCore.Qt.UserRole), plexdevices.hubs.Hub):
            return super().sizeHint(option, index)
        return QtCore.QSize(0, self.parent().iconSize().height())


class TileDelegateUniform(BaseDelegate):

    def summary_line_count(self, item):
        if isinstance(item, plexdevices.media.Episode):
            return 2
        elif isinstance(item, plexdevices.media.Album):
            return 1
        elif isinstance(item, plexdevices.media.Movie):
            return 1
        elif isinstance(item, plexdevices.media.Track):
            return 1
        else:
            return 0

    def paint(self, painter, option, index):
        item = index.data(role=QtCore.Qt.UserRole)
        if not item:
            return

        self.initStyleOption(option, index)

        icon_size = self.parent().iconSize()

        lines = []
        if isinstance(item, plexdevices.media.Episode):
            lines.append(item.grandparent_title)
            lines.append(item.title)
            lines.append('S{} E{}'.format(item.parent_index, item.index))
        elif isinstance(item, plexdevices.media.Album):
            lines.append(item.parent_title)
            lines.append(item.title)
        elif isinstance(item, plexdevices.media.Movie):
            lines.append(item.title)
            lines.append(str(item.year))
        elif isinstance(item, plexdevices.media.Track):
            lines.append(item.title)
            lines.append(timestamp_from_ms(item.duration, minimal=True))
        else:
            lines.append(item.title)

        icon_rect = QtCore.QRect(
            option.rect.topLeft(),
            option.rect.topRight() + QtCore.QPoint(0, icon_size.height())
        )

        background_rect = QtCore.QRect(
            option.rect.topLeft(),
            icon_rect.bottomRight() +
            QtCore.QPoint(0, self.title_font_metrics.height() +
                          self.summary_font_metrics.height() * (len(lines) - 1))
        )

        text_rect = QtCore.QRect(option.rect.topLeft(), option.rect.bottomRight())
        text_rect.setTop(icon_rect.bottom())

        # Background
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(background_rect, option.palette.highlight())
        elif option.state & QtWidgets.QStyle.State_MouseOver:
            brush = option.palette.base()
            if brush.color().lightness() > 127:
                brush.setColor(brush.color().darker(120))
            else:
                brush.setColor(brush.color().lighter(120))
            painter.fillRect(background_rect, brush)

        # Icon
        thumb = index.data(role=QtCore.Qt.DecorationRole)
        if thumb and not thumb.isNull():
            if thumb.height() > thumb.width():
                scaled = thumb.scaledToWidth(icon_size.height(),
                                             QtCore.Qt.SmoothTransformation)
                scaled = scaled.copy(0, scaled.height() / 2 - icon_size.height() / 2,
                                     icon_size.height(), icon_size.height())
            elif thumb.height() < thumb.width():
                scaled = thumb.scaledToHeight(icon_size.height(),
                                              QtCore.Qt.SmoothTransformation)
            else:
                scaled = thumb.scaledToHeight(
                    icon_size.height(), QtCore.Qt.SmoothTransformation)
            if item.markable:
                draw_progress_bar(item, scaled, height=6)
                draw_unwatched_indicator(item, scaled, size=0.20)
            QtWidgets.QApplication.style().drawItemPixmap(
                painter, option.rect, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, scaled)

        # Title
        painter.save()
        painter.setBrush(option.palette.highlightedText() if
                         option.state & QtWidgets.QStyle.State_Selected else
                         option.palette.text())
        painter.setFont(self.title_font)

        elided_text = painter.fontMetrics().elidedText(
            lines[0], QtCore.Qt.ElideRight, option.rect.width())
        painter.drawText(text_rect, QtCore.Qt.AlignLeft, elided_text)
        text_rect.setTop(text_rect.top() + painter.fontMetrics().height())
        painter.restore()
        painter.save()
        if painter.pen().color().lightness() > 127:
            painter.setPen(QtGui.QPen(painter.pen().color().darker()))
        else:
            painter.setPen(QtGui.QPen(painter.pen().color().lighter()))
        painter.setFont(self.summary_font)

        # extra lines
        for line in lines[1:]:
            elided_text = painter.fontMetrics().elidedText(
                line, QtCore.Qt.ElideRight, option.rect.width())
            painter.drawText(text_rect, QtCore.Qt.AlignLeft, elided_text)
            text_rect.setTop(text_rect.top() + painter.fontMetrics().height())

        painter.restore()

    def sizeHint(self, option, index):
        icon_size = self.parent().iconSize()
        item = index.data(role=QtCore.Qt.UserRole)
        summary_lines = self.summary_line_count(item)
        text_height = (self.title_font_metrics.height() +
                       self.summary_font_metrics.height() * summary_lines)
        return QtCore.QSize(icon_size.width(), icon_size.height() + text_height)