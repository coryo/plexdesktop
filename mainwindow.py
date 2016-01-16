import pickle
from PyQt5.QtWidgets import QMainWindow
import plexdevices
import mainwindow_ui
from browser import Browser
from remote import Remote
from settings import Settings


class PlexApp(QMainWindow, mainwindow_ui.Ui_MainWindow):

    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)
        self.port = 8000
        self.remotes = []
        self.browsers = []
        self.session = None

        self.btn_login.clicked.connect(self.create_session)
        self.btn_remote.clicked.connect(self.create_remote)
        self.btn_browser.clicked.connect(self.create_browser)
        self.btn_browser.clicked.connect(self.close)

        settings = Settings()
        self.user.setText(settings.value('user'))
        self.loadSession()

    def loadSession(self):
        settings = Settings()
        try:
            self.session = pickle.loads(settings.value('session'))
            self.update_ui()
        except Exception as e:
            print(str(e))

    def create_session(self):
        sender = self.sender()
        settings = Settings()
        settings.setValue('user', self.user.text().strip())
        self.session = plexdevices.Session(user=self.user.text().strip(),
                                           password=self.password.text().strip())
        try:
            self.session.refresh_devices()
        except plexdevices.PlexTVError as e:
            print(str(e))
            return
        try:
            settings.setValue('session', pickle.dumps(self.session))
        except Exception as e:
            print(str(e))
            return
        self.update_ui()

    def update_ui(self):
        self.players.clear()
        self.servers.clear()
        for i, item in enumerate(self.session.players):
            self.players.addItem('{} - {}'.format(item.name, item.product), i)
            self.btn_remote.setEnabled(True)
        for i, item in enumerate(self.session.servers):
            self.servers.addItem('{} - {}'.format(item.name, item.product), i)
            self.btn_browser.setEnabled(True)

    def enable_remote(self):
        self.btn_remote.setEnabled(True)

    def enable_browser(self):
        self.btn_browser.setEnabled(True)

    def create_remote(self):
        try:
            port = self.remotes[-1].port + 1
        except Exception:
            port = self.port
        try:
            remote = Remote(self.session, self.session.players[self.players.currentIndex()],
                            port=port)
        except plexdevices.DeviceConnectionsError as e:
            print(str(e))
        else:
            self.remotes.append(remote)

    def create_browser(self):
        b = Browser(self.session, self.session.servers[self.servers.currentIndex()])
        self.browsers.append(b)
