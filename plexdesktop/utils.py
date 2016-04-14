from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter
from PyQt5.QtCore import Qt
import plexdevices


def timestamp_from_ms(milliseconds):
    m, s = divmod(milliseconds / 1000, 60)
    h, m = divmod(m, 60)
    return "{:.0f}:{:02.0f}:{:02.0f}".format(h, m, s)


def msg_box(message, title='plexdesktop'):
    msg = QMessageBox()
    msg.setText(message)
    msg.setWindowTitle(title)
    msg.exec_()


def title(media):
    container = media.container
    if isinstance(media, plexdevices.media.Directory):
        if isinstance(media, plexdevices.media.Season):
            t = '{} - {}'.format(media.parent_title, media.title)
            if media.unwatched_count > 0:
                t += ' ({})'.format(media.unwatched_count)
            return t
        else:
            return media.title
    else:
        if container.filters or not container.is_library:
            return media.title

        if isinstance(media, plexdevices.media.Episode):
            t = 's{:02d}e{:02d} - {}'.format(media.parent_index,
                                             media.index,
                                             media.title)
            if container.mixed_parents:
                t = media.grandparent_title + ' - ' + t
            return t
        elif isinstance(media, plexdevices.media.Movie):
            return '{} ({}) {}'.format(media.title, media.year, media.rating)
        elif isinstance(media, plexdevices.media.Track):
            return '{} - {}'.format(media.index, media.title)
        elif isinstance(media, plexdevices.media.Photo):
            return media.title
        else:
            return media.title


def hub_title(media):
    if isinstance(media, plexdevices.media.Directory):
        if isinstance(media, plexdevices.media.Season):
            t = '{} - {}'.format(media.parent_title, media.title)
            return t
        elif isinstance(media, plexdevices.media.Album):
            return '{} - {}'.format(media.parent_title, media.title)
        else:
            return media.title if media.title else media.data.get('tag')
    else:
        if isinstance(media, plexdevices.media.Episode):
            t = '{} - s{:02d}e{:02d} - {}'.format(media.grandparent_title,
                                                  media.parent_index,
                                                  media.index,
                                                  media.title)
            return t
        elif isinstance(media, plexdevices.media.Movie):
            return '{} ({}) {}'.format(media.title, media.year, media.rating)
        elif isinstance(media, plexdevices.media.Track):
            return '{} - {}'.format(media.index, media.title)
        elif isinstance(media, plexdevices.media.Photo):
            return media.title
    return media.title


class Location(object):
    def __init__(self, key, sort=0, params=None):
        self.key = key
        self.sort = sort
        self.params = params

    def tuple(self):
        return (self.key, self.sort, self.params)

    @staticmethod
    def home():
        return Location('/library/sections')

    @staticmethod
    def on_deck():
        return Location('/library/onDeck')

    @staticmethod
    def recently_added():
        return Location('/library/recentlyAdded')

    @staticmethod
    def channels():
        return Location('/channels/all')


def icon_factory(res_path, color, size):
    pixmap = QPixmap(res_path)
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QIcon(pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
