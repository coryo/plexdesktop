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
import uuid

import PyQt5.QtCore
import PyQt5.QtWidgets

import plexdesktop.browser
import plexdesktop.utils

logger = logging.getLogger('plexdesktop')


class ComponentObject(PyQt5.QtCore.QObject):
    closed = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

    def _shutdown(self):
        """call when the component is ready to be destroyed"""
        self.closed.emit(self.name)


class ComponentWindow(PyQt5.QtWidgets.QMainWindow):
    closed = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

    def _shutdown(self):
        """call when the component is ready to be destroyed"""
        self.closed.emit(self.name)


@plexdesktop.utils.Singleton
class ComponentManager(PyQt5.QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.components = {}

    def add(self, component):
        logger.debug('ComponentManager: adding {}'.format(component.name))
        self.components[component.name] = component
        component.closed.connect(self.remove)

    def remove(self, name):
        logger.debug('ComponentManager: removing {}'.format(name))
        try:
            # component = self.components[name]
            # component.deleteLater()
            del self.components[name]
        except Exception as e:
            logger.debug(e)

    def exists(self, name):
        return name in self.components

    def get(self, name):
        return self.components.get(name, None)

    def create_component(self, cls, name=None, **kwargs):
        component = cls(name=name if name is not None else
                        '{}-{}'.format(cls.__name__, uuid.uuid4().hex), **kwargs)
        self.add(component)
        return component

    @PyQt5.QtCore.pyqtSlot()
    def create_browser(self):
        browser = self.create_component(plexdesktop.browser.Browser)
        browser.show()
        return browser


# COMPONENT_MANAGER = ComponentManager()
