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

import logging
import pickle
import base64

import requests

import plexdevices

from PyQt5 import QtCore

import plexdesktop.settings
import plexdesktop.utils
import plexdesktop.sqlcache

logger = logging.getLogger('plexdesktop')


class SessionManager(QtCore.QObject):
    working = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal(bool, str)
    active = QtCore.pyqtSignal(bool)
    shortcuts_changed = QtCore.pyqtSignal()
    shortcuts_loaded = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = plexdevices.create_session()
        self.shortcuts = None
        self.current_server = None
        self.user = None

    @property
    def server(self):
        if not self.current_server:
            settings = plexdesktop.settings.Settings()
            return self.session.get_server_by_id(settings.value('last_server'))
        else:
            return self.current_server

    def load_session(self):
        settings = plexdesktop.settings.Settings()
        try:
            # with open('session.pickle', 'rb') as f:
            #     self.session = pickle.load(f)
            self.session = pickle.loads(base64.b64decode(settings.value('session').encode()))
            self.user = self.session.get_user_by_id(settings.value('user'))
            self.current_server = self.session.get_server_by_id(settings.value('last_server'))
            self.active.emit(True)
        except Exception as e:
            logger.error('SessionManager: load_session: ' + str(e))
            self.active.emit(False)

    def save_session(self):
        settings = plexdesktop.settings.Settings()
        try:
            logger.info('SessionManager: saving session')
            # with open('session.pickle', 'wb') as f:
            #     pickle.dump(self.session, f)
            settings.setValue('session', base64.b64encode(pickle.dumps(self.session)).decode())
        except Exception as e:
            logger.error('SessionManager: save_session: ' + str(e))

    def create_session(self, user, passwd):
        self.working.emit()
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
                if user.title == self.session.user:
                    settings.setValue('user', user.id)
                    break
            self.save_session()
            self.user = self.session.get_user_by_id(settings.value('user'))
            self.current_server = self.session.get_server_by_id(settings.value('last_server'))
            if not self.current_server and self.session.servers:
                self.current_server = self.session.servers[0]
            self.active.emit(True)
            self.done.emit(True, '')

    def refresh_devices(self):
        self.working.emit()
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
        self.working.emit()
        try:
            logger.info('SessionManager: getting plex home users.')
            self.session.refresh_users()
        except Exception as e:
            logger.error('SessionManager: refresh_users: ' + str(e))
            self.done.emit(False, '')
        else:
            self.cache_user_thumbs()
            self.done.emit(True, '')

    def cache_user_thumbs(self):
        logger.info('SessionManager: refreshing user thumbs')
        with plexdesktop.sqlcache.db_thumb() as cache:
            for user in self.session.users:
                if user.thumb in cache:
                    continue
                try:
                    logger.info('getting thumb {}'.format(user.thumb))
                    r = requests.get(user.thumb)
                except Exception:
                    logger.error(
                        'SessionManager: cache_user_thumbs {}'.format(user.thumb))
                else:
                    if r.ok:
                        img_data = r.content
                        cache[user.thumb] = img_data

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
        self.current_server = server
        self.shortcuts = Shortcuts(self.server)
        self.shortcuts.shortcuts_changed.connect(self.shortcuts_changed.emit)
        self.shortcuts.shortcuts_loaded.connect(self.shortcuts_loaded.emit)
        self.shortcuts.load()

    def manual_add_server(self, protocol, address, port, token):
        self.working.emit()
        logger.debug('{}, {}, {}, {}'.format(protocol, address, port, token))
        try:
            self.session.manual_add_server(address, port, protocol, token)
        except ConnectionError as e:
            self.done.emit(False, str(e))
        else:
            self.save_session()
            self.done.emit(True, '')

    def switch_user(self, user, pin=None):
        self.working.emit()
        settings = plexdesktop.settings.Settings()
        try:
            logger.info('SessionManager: changing user.')
            self.session.switch_user(user, pin=pin)
        except plexdevices.PlexTVError as e:
            logger.error('SessionManager: switch_user: ' + str(e))
            self.done.emit(False, str(e))
        else:
            settings.setValue('user', user.id)
            server = self.session.get_server_by_id(self.current_server.client_identifier)
            self.current_server = server if server else self.session.servers[0]
            self.user = user
            self.save_session()
            self.done.emit(True, '')


class Shortcuts(QtCore.QObject):
    shortcuts_changed = QtCore.pyqtSignal()
    shortcuts_loaded = QtCore.pyqtSignal(int)

    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self.shortcuts = {}
        self.s = plexdesktop.settings.Settings()

    def __len__(self):
        return len(self.shortcuts)

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
