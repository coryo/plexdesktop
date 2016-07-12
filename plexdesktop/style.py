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
            icon.addFile(':/images/theme_{}/{}.png'.format(name, off))
            if on is not None:
                icon.addFile(':/images/theme_{}/{}.png'.format(name, on), state=PyQt5.QtGui.QIcon.On)
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

    def load_qss(self, qss):
        file = PyQt5.QtCore.QFile(qss)
        file.open(PyQt5.QtCore.QFile.ReadOnly)
        ss = bytes(file.readAll()).decode('latin-1')
        app = PyQt5.QtCore.QCoreApplication.instance()
        app.setStyleSheet(ss)

    def switch_theme(self, theme):
        self.load_qss(theme)


@plexdesktop.utils.Singleton
class Style(PyQt5.QtCore.QObject):

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
        s = plexdesktop.settings.Settings()
        if name in self.themes:
            self.style.switch_theme(self.themes[name])
            self.widget.switch_theme(name)
            s.setValue('theme', name)
            self.current = name

    def refresh_actions(self):
        self.widget.switch_theme(self.current)

    def refresh(self):
        self.widget.switch_theme(self.current)


# STYLE = Style()
