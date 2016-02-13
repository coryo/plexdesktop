from PyQt5.QtWidgets import QMessageBox
from plexdevices import PlexType, Directory, Episode, Movie, Track, Season, Photo


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
    if isinstance(media, Directory):
        if isinstance(media, Season):
            t = '{} - {}'.format(media.parent_title, media.title)
            if media.unwatched_count > 0:
                t += ' ({})'.format(media.unwatched_count)
            return t
        else:
            return media.title
    else:
        if container.filters or not container.is_library:
            return media.title

        if isinstance(media, Episode):
            t = 's{:02d}e{:02d} - {}'.format(media.parent_index,
                                             media.index,
                                             media.title)
            if container.mixed_parents:
                t = media.grandparent_title + ' - ' + t
            return t
        elif isinstance(media, Movie):
            return '{} ({}) {}'.format(media.title, media.year, media.rating)
        elif isinstance(media, Track):
            return '{} - {}'.format(media.index, media.title)
        elif isinstance(media, Photo):
            return media.title
        else:
            return media.title
