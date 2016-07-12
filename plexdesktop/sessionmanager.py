import logging
import pickle

import plexdevices

import PyQt5.QtCore

import plexdesktop.settings
import plexdesktop.utils

logger = logging.getLogger('plexdesktop')


class SessionManager(PyQt5.QtCore.QObject):
    done = PyQt5.QtCore.pyqtSignal(bool, str)
    active = PyQt5.QtCore.pyqtSignal(bool)
    shortcuts_changed = PyQt5.QtCore.pyqtSignal()
    shortcuts_loaded = PyQt5.QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = plexdevices.create_session()
        self.shortcuts = None
        self.current_server = None

    @property
    def user(self):
        settings = plexdesktop.settings.Settings()
        user = settings.value('user')
        return user

    @property
    def server(self):
        if self.current_server is None:
            settings = plexdesktop.settings.Settings()
            last_server = settings.value('last_server')
        else:
            last_server = self.current_server
        server = self.find_server(last_server)
        return server if server is not None else (self.session.servers[0] if self.session.servers else None)

    def load_session(self):
        settings = plexdesktop.settings.Settings()
        try:
            self.session = pickle.loads(settings.value('session'))
            self.active.emit(True)
        except Exception as e:
            logger.error('SessionManager: load_session: ' + str(e))
            self.active.emit(False)

    def save_session(self):
        settings = plexdesktop.settings.Settings()
        try:
            logger.info('SessionManager: saving session')
            settings.setValue('session', pickle.dumps(self.session))
        except Exception as e:
            logger.error('SessionManager: save_session: ' + str(e))

    def find_server(self, identifier):
        try:
            return [x for x in self.session.servers if x.client_identifier == identifier][0]
        except Exception:
            return None

    def create_session(self, user, passwd):
        settings = plexdesktop.settings.Settings()
        try:
            logger.debug('SessionManager: creating session')
            self.session = plexdevices.create_session(user=user, password=passwd)
        except plexdevices.PlexTVError as e:
            logger.error('SessionManager: create_session: ' + str(e))
            self.done.emit(False, str(e))
        else:
            self.refresh_devices()
            self.refresh_users()
            for user in self.session.users:
                if user['title'] == self.session.user:
                    settings.setValue('user', user['id'])
                    break
            self.save_session()
            self.active.emit(True)
            self.done.emit(True, '')

    def refresh_devices(self):
        try:
            logger.info('SessionManager: refreshing devices')
            self.session.refresh_devices()
        except plexdevices.PlexTVError as e:
            logger.error('SessionManager: refresh_devices: ' + str(e))
            self.done.emit(False, str(e))
        else:
            self.save_session()
            self.done.emit(True, '')

    def refresh_users(self):
        try:
            logger.info('SessionManager: getting plex home users.')
            self.session.refresh_users()
        except Exception as e:
            logger.error('SessionManager: refresh_users: ' + str(e))
            self.done.emit(False, '')
        else:
            self.done.emit(True, '')

    def delete_session(self):
        settings = plexdesktop.settings.Settings()
        settings.remove('session')
        settings.remove('user')
        settings.remove('last_server')
        self.session = plexdevices.create_session()
        self.active.emit(False)

    def switch_server(self, server):
        settings = plexdesktop.settings.Settings()
        settings.setValue('last_server', server.client_identifier)
        self.current_server = server.client_identifier
        self.shortcuts = Shortcuts(self.server)
        self.shortcuts.shortcuts_changed.connect(self.shortcuts_changed.emit)
        self.shortcuts.shortcuts_loaded.connect(self.shortcuts_loaded.emit)
        self.shortcuts.load()

    def manual_add_server(self, protocol, address, port, token):
        logger.debug('{}, {}, {}, {}'.format(protocol, address, port, token))
        try:
            self.session.manual_add_server(address, port, protocol, token)
        except ConnectionError as e:
            self.done.emit(False, str(e))
        else:
            self.save_session()
            self.done.emit(True, '')

    def switch_user(self, userid, pin=None):
        settings = plexdesktop.settings.Settings()
        try:
            logger.info('SessionManager: changing user.')
            self.session.switch_user(userid, pin=pin)
        except plexdevices.PlexTVError as e:
            logger.error('SessionManager: switch_user: ' + str(e))
            self.done.emit(False, str(e))
        else:
            settings.setValue('user', userid)
            self.save_session()
            self.done.emit(True, '')


class Shortcuts(PyQt5.QtCore.QObject):
    shortcuts_changed = PyQt5.QtCore.pyqtSignal()
    shortcuts_loaded = PyQt5.QtCore.pyqtSignal(int)

    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self.shortcuts = {}
        self.s = plexdesktop.settings.Settings()

    def __contains__(self, location):
        return location in self.shortcuts.values()

    def __getitem__(self, name):
        return self.shortcuts[name]

    def items(self):
        return self.shortcuts.items()

    def add(self, name, location):
        """ Add a shortcut to location with the given name """
        self.shortcuts[name] = location
        self.save()
        self.shortcuts_changed.emit()

    def remove(self, location):
        """ Remove a shortcut to location """
        try:
            k = [x for x in self.shortcuts if self.shortcuts[x] == location][0]
        except Exception as e:
            logger.debug('failed to remove shortcut: {}'.format(e))
        else:
            del self.shortcuts[k]
            self.save()
            self.shortcuts_changed.emit()

    def remove_name(self, name):
        """ Remove shortcut by name """
        if 'name' in self.shortcuts:
            del self.shortcuts[name]
            self.save()
            self.shortcuts_changed.emit()

    def save(self):
        """ Save the shortcuts to settings """
        self.s.setValue('shortcuts-{}'.format(self.server.client_identifier),
                        {k: v.__dict__ for k, v in self.shortcuts.items()})

    def load(self):
        """ Load the shortcuts from settings for the server """
        f = self.s.value('shortcuts-{}'.format(self.server.client_identifier))
        if f:
            self.shortcuts = {k: plexdesktop.utils.Location(**v) for k, v in f.items()}
        self.shortcuts_loaded.emit(len(self.shortcuts))
