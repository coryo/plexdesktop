import PyQt5.QtCore


class Settings(PyQt5.QtCore.QSettings):
    def __init__(self, parent=None):
        super().__init__('settings.ini', PyQt5.QtCore.QSettings.IniFormat, parent)
