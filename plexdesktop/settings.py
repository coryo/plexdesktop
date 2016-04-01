from PyQt5.QtCore import QSettings


class Settings(QSettings):
    def __init__(self, parent=None):
        super(Settings, self).__init__('settings.ini', QSettings.IniFormat, parent)
