import logging
import pickle
from PyQt5.QtCore import pyqtSignal, QObject
from plexdesktop.settings import Settings
import plexdevices

logger = logging.getLogger('plexdesktop')


class SessionManager(QObject):
    done = pyqtSignal(bool, str)
    active = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.session = plexdevices.create_session()

    @property
    def user(self):
        settings = Settings()
        user = settings.value('user')
        return user

    @property
    def server(self):
        settings = Settings()
        last_server = settings.value('last_server')
        server = self.find_server(last_server)
        return server if server is not None else (self.session.servers[0] if self.session.servers else None)

    def load_session(self):
        settings = Settings()
        try:
            self.session = pickle.loads(settings.value('session'))
            self.active.emit(True)
        except Exception as e:
            logger.error('SessionManager: load_session: ' + str(e))
            self.active.emit(False)

    def save_session(self):
        settings = Settings()
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
        settings = Settings()
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
        settings = Settings()
        settings.remove('session')
        settings.remove('user')
        settings.remove('last_server')
        self.session = plexdevices.create_session()
        self.active.emit(False)

    def switch_server(self, server):
        settings = Settings()
        settings.setValue('last_server', server.client_identifier)

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
        settings = Settings()
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
