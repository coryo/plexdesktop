import logging
from PyQt5.QtWidgets import QMainWindow, QMessageBox
import plexdevices
import mainwindow_ui
from browser import Browser
from remote import Remote
from settings import Settings
import utils
logger = logging.getLogger('plexdesktop')


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
            self.session = plexdevices.Session.load(settings.value('session'))
            self.update_ui()
        except Exception as e:
            logger.error(str(e))

    def create_session(self):
        sender = self.sender()
        settings = Settings()
        settings.setValue('user', self.user.text().strip())
        try:
            logger.info('MainWindow: creating session')
            self.session = plexdevices.Session(user=self.user.text().strip(),
                                               password=self.password.text().strip())
        except plexdevices.PlexTVError as e:
            logger.error(str(e))
            utils.msg_box(str(e))
            return
        try:
            logger.info('MainWindow: refreshing devices')
            self.session.refresh_devices()
        except plexdevices.PlexTVError as e:
            logger.error(str(e))
            utils.msg_box(str(e))
            return
        try:
            logger.info('MainWindow: getting plex home users.')
            self.session.refresh_users()
        except Exception as e:
            logger.error(str(e))
        try:
            logger.info('MainWindow: saving session')
            settings.setValue('session', self.session.dump())
        except Exception as e:
            logger.error(str(e))
            utils.msg_box(str(e))

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

        settings = Settings()
        last_server = [x for x in self.session.servers if x.client_identifier == settings.value('last_server')]
        if last_server:
            index = self.session.servers.index(last_server[0])
            self.servers.setCurrentIndex(index)

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
            player = self.session.players[self.players.currentIndex()]
            logger.info('MainWindow: creating remote on port {}. player={}'.format(port, player))
            remote = Remote(self.session, player, port=port)
        except plexdevices.DeviceConnectionsError as e:
            logger.error(str(e))
            utils.msg_box(str(e))
        else:
            self.remotes.append(remote)

    def create_browser(self):
        logger.info('MainWindow: creating browser')
        b = Browser(self.session, self.session.servers[self.servers.currentIndex()])
        self.browsers.append(b)
