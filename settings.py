from PyQt5.QtCore import QSettings


class Settings(QSettings):
    def __init__(self, parent=None):
        super(Settings, self).__init__('settings.ini', QSettings.IniFormat, parent)
        self.defaults = {
            'user': ''
            # 'password': '',
            # 'ext_player': 'c:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
            # 'ext_player_args': '%URL%'
        }

    def set_defaults(self):
        allkeys = self.allKeys()
        for k, v in self.defaults.items():
            if k not in allkeys:
                self.setValue(k, v)
