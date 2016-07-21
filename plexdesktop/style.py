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

import PyQt5.QtGui
import PyQt5.QtCore

import plexdesktop.utils
import plexdesktop.settings
"""
Usage:

style = plexdesktop.style.Style.Instance()
style.widget.register(widget, 'icon-name')
style.refresh()
"""


class WidgetIconManager(PyQt5.QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = {}

    def register(self, item, off, on=None):
        self.items[self.key(item)] = (item, off, on)
        item.destroyed.connect(self.on_item_delete)

    def switch_theme(self, name):
        for key, (item, off, on) in self.items.items():
            icon = PyQt5.QtGui.QIcon()
            icon.addFile('resources/themes/{}/images/{}.png'.format(name, off))
            if on is not None:
                icon.addFile('resources/themes/{}/images/{}.png'.format(name, on), state=PyQt5.QtGui.QIcon.On)
            item.setIcon(icon)

    def on_item_delete(self):
        a = self.sender()
        try:
            del self.items[self.key(a)]
        except KeyError:
            pass

    def key(self, obj):
        return hash(obj.objectName() + obj.parent().objectName())


class QSSManager(PyQt5.QtCore.QObject):
    def load_qss(self, theme):
        path = 'resources/themes/{}/style.qss'.format(theme)
        file = PyQt5.QtCore.QFile(path)
        file.open(PyQt5.QtCore.QFile.ReadOnly)
        ss = bytes(file.readAll()).decode('latin-1')
        app = PyQt5.QtCore.QCoreApplication.instance()
        app.setStyleSheet(ss)
        self.current = ss

    def switch_theme(self, theme):
        self.load_qss(theme)


@plexdesktop.utils.Singleton
class Style(PyQt5.QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = WidgetIconManager()
        self.style = QSSManager()
        self.themes = ['light', 'dark']
        self.current = None

        def _add_switcher(name):
            def s():
                self.theme(name)
            setattr(self, name, s)
        for theme in self.themes:
            _add_switcher(theme)

    def theme(self, name):
        s = plexdesktop.settings.Settings()
        if name in self.themes:
            self.style.switch_theme(name)
            self.widget.switch_theme(name)
            s.setValue('theme', name)
            self.current = name

    def refresh_actions(self):
        self.widget.switch_theme(self.current)

    def refresh(self):
        self.widget.switch_theme(self.current)
        self.style.switch_theme(self.current)


# STYLE = Style()
