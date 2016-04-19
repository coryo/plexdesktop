# from PyQt5.QtWidgets import QDialog, QFormLayout, QLabel, QComboBox, QDialogButtonBox
from PyQt5.QtCore import QSettings#, Qt
# from plexdesktop.style import STYLE


class Settings(QSettings):
    def __init__(self, parent=None):
        super(Settings, self).__init__('settings.ini', QSettings.IniFormat, parent)



