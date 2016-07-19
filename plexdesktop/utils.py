import plexdevices

import PyQt5.QtWidgets


def timestamp_from_ms(milliseconds, minimal=False):
    m, s = divmod(milliseconds / 1000, 60)
    h, m = divmod(m, 60)
    if minimal:
        return ':'.join(('{:02.0f}'.format(x) for x in (h, m, s) if x > 0))
    return '{:.0f}:{:02.0f}:{:02.0f}'.format(h, m, s)


def msg_box(message, title='plexdesktop'):
    msg = PyQt5.QtWidgets.QMessageBox()
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

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @classmethod
    def home(cls):
        return cls('/library/sections')

    @classmethod
    def on_deck(cls):
        return cls('/library/onDeck')

    @classmethod
    def recently_added(cls):
        return cls('/library/recentlyAdded')

    @classmethod
    def channels(cls):
        return cls('/channels/all')


class Singleton(object):
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
