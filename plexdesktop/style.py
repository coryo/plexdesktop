from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, QFile, QCoreApplication
from plexdesktop.settings import Settings
"""
Usage:

from plexdesktop.style import STYLE

STYLE.widget.register(widget, 'icon-name')
STYLE.refresh()
"""


class WidgetIconManager(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = {}

    def register(self, item, off, on=None):
        self.items[self.key(item)] = (item, off, on)
        item.destroyed.connect(self.on_item_delete)

    def switch_theme(self, name):
        for key, (item, off, on) in self.items.items():
            icon = QIcon()
            icon.addFile(':/images/theme_{}/{}.png'.format(name, off))
            if on is not None:
                icon.addFile(':/images/theme_{}/{}.png'.format(name, on), state=QIcon.On)
            item.setIcon(icon)

    def on_item_delete(self):
        a = self.sender()
        try:
            del self.items[self.key(a)]
        except KeyError:
            pass

    def key(self, obj):
        return hash(obj.objectName() + obj.parent().objectName())


class QSSManager(QObject):

    def load_qss(self, qss):
        file = QFile(qss)
        file.open(QFile.ReadOnly)
        ss = bytes(file.readAll()).decode('latin-1')
        app = QCoreApplication.instance()
        app.setStyleSheet(ss)

    def switch_theme(self, theme):
        self.load_qss(theme)


class Style(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = WidgetIconManager()
        self.style = QSSManager()
        self.themes = {
            'light': ':/resources/light.qss',
            'dark': ':/resources/dark.qss'
        }
        self.current = None

        def _add_switcher(name):
            def s():
                self.theme(name)
            setattr(self, name, s)
        for theme in self.themes:
            _add_switcher(theme)

    def theme(self, name):
        s = Settings()
        if name in self.themes:
            self.style.switch_theme(self.themes[name])
            self.widget.switch_theme(name)
            s.setValue('theme', name)
            self.current = name

    def refresh_actions(self):
        self.widget.switch_theme(self.current)

    def refresh(self):
        self.widget.switch_theme(self.current)


STYLE = Style()
