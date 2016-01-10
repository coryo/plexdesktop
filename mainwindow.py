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

        self.btn_login.clicked.connect(self.newSession)
        self.btn_launch.clicked.connect(self.newRemote)
        self.btn_browser.clicked.connect(self.newBrowser)

        settings = Settings()
        self.user.setText(settings.value('user'))
        self.password.setText(settings.value('password'))
        self.loadSession()

    def loadSession(self):
        settings = Settings()
        try:
            self.session = pickle.loads(settings.value('session'))
            self.updateUi()
        except Exception as e:
            print(str(e))

    def newSession(self):
        sender = self.sender()
        settings = Settings()
        settings.setValue('user', self.user.text().strip())
        settings.setValue('password', self.password.text().strip())
        self.session = plexdevices.Session(user=self.user.text().strip(),
                                    password=self.password.text().strip())
        try:
            self.session.refresh_devices()
        except plexdevices.exceptions.PlexTVError as e:
            print(str(e))
            return
        try:
            settings.setValue('session', pickle.dumps(self.session))
        except Exception as e:
            print(str(e))
            return
        self.updateUi()

    def updateUi(self):
        self.players.clear()
        self.servers.clear()
        for i, item in enumerate(self.session.players):
            self.players.addItem('{} - {}'.format(item.name, item.product), i)
            self.btn_launch.setEnabled(True)
        for i, item in enumerate(self.session.servers):
            self.servers.addItem('{} - {}'.format(item.name, item.product), i)
            self.btn_browser.setEnabled(True)          

    def enable_remote(self):
        self.btn_launch.setEnabled(True)

    def enable_browser(self):
        self.btn_browser.setEnabled(True)

    def newRemote(self):
        try:
            port = self.remotes[-1].port + 1
        except Exception:
            port = self.port
        try:
            remote = Remote(self.session, self.session.players[self.players.currentIndex()],
                            port=port)
        except plexdevices.exceptions.DeviceConnectionsError as e:
            print(str(e))
        else:
            self.remotes.append(remote)

    def newBrowser(self):
        b = Browser(self.session, self.session.servers[self.servers.currentIndex()])
        self.browsers.append(b)