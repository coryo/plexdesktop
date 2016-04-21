import logging
from PyQt5.QtWidgets import (QDialog, QMainWindow, QAction, QInputDialog,
                             QApplication, QLineEdit)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QCoreApplication, QThread, QFile, QSize
from PyQt5.QtGui import QColor
from plexdesktop import __version__
from plexdesktop.ui.browser_ui import Ui_Browser
from plexdesktop.settings import Settings
from plexdesktop.player import MPVPlayer
from plexdesktop.photo_viewer import PhotoViewer
from plexdesktop.utils import title, msg_box, Location, timestamp_from_ms
from plexdesktop.style import STYLE
from plexdesktop.extra_widgets import ManualServerDialog, LoginDialog, SettingsDialog
from plexdesktop.sqlcache import DB_IMAGE, DB_THUMB
from plexdesktop.remote import Remote
from plexdesktop.sessionmanager import SessionManager
from plexdesktop.hubtree import TreeModel, TreeView
from plexdesktop.about import About
import plexdevices

logger = logging.getLogger('plexdesktop')


class Browser(QMainWindow):
    create_session = pyqtSignal(str, str)
    refresh_devices = pyqtSignal()
    refresh_users = pyqtSignal()
    change_user = pyqtSignal(str, str)
    manual_add_server = pyqtSignal(str, str, str, str)
    new_hub_search = pyqtSignal(plexdevices.device.Server, str)
    player_exists = pyqtSignal(bool)
    photo_viewer_exists = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Browser()
        self.ui.setupUi(self)
        self.ui.indicator.hide()
        self.ui.metadata_panel.hide()

        self.session_manager = SessionManager()

        self.worker_thread = QThread()
        self.session_manager.moveToThread(self.worker_thread)
        self.session_manager.active.connect(self.ui.actionLogout.setEnabled)
        self.session_manager.active.connect(self.ui.actionRefresh_Devices.setEnabled)
        self.session_manager.active.connect(self.ui.actionRefresh_Users.setEnabled)
        self.session_manager.active.connect(self.ui.menuRemotes.setEnabled)
        self.session_manager.active.connect(self.ui.actionInfo.setEnabled)
        self.create_session.connect(self.session_manager.create_session)
        self.refresh_devices.connect(self.session_manager.refresh_devices)
        self.refresh_users.connect(self.session_manager.refresh_users)
        self.change_user.connect(self.session_manager.switch_user)
        self.manual_add_server.connect(self.session_manager.manual_add_server)
        self.session_manager.done.connect(self._session_manager_cb)
        self.worker_thread.start()

        self.remotes = []
        self.mpvplayer = None
        self.image_viewer = None
        self.container_size = 50
        self.initialized = False
        self.shortcuts = {}

        self.ui.servers.currentIndexChanged.connect(self.action_change_server)
        self.ui.users.currentIndexChanged.connect(self.action_change_user)
        self.ui.shortcuts.activated.connect(self.load_shortcut)

        # Register actions with style, assign their icon name.
        STYLE.widget.register(self.ui.actionBack, 'glyphicons-chevron-left')
        STYLE.widget.register(self.ui.actionRefresh, 'glyphicons-refresh')
        STYLE.widget.register(self.ui.actionFind, 'glyphicons-search')
        STYLE.widget.register(self.ui.actionHome, 'glyphicons-home')
        STYLE.widget.register(self.ui.actionChannels, 'channels')
        STYLE.widget.register(self.ui.actionMetadata, 'glyphicons-list')
        STYLE.widget.register(self.ui.actionAdd_Shortcut, 'glyphicons-plus', 'glyphicons-minus')
        STYLE.refresh()
        # Menu
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionLogin_Refresh.triggered.connect(self.action_login)
        self.ui.actionLogout.triggered.connect(self.action_logout)
        self.ui.actionReload_Stylesheet.triggered.connect(self.action_reload_stylesheet)
        self.ui.actionAdd_Server.triggered.connect(self.action_manual_add_server)
        self.ui.actionTrim_Image_Cache.triggered.connect(self.action_trim_image_cache)
        self.ui.actionTrim_Thumb_Cache.triggered.connect(self.action_trim_thumb_cache)
        self.ui.actionRefresh_Devices.triggered.connect(self.action_refresh_devices)
        self.ui.actionRefresh_Users.triggered.connect(self.action_refresh_users)
        self.ui.actionFind.triggered.connect(self.toggle_search_bar)
        self.ui.actionFind.triggered.connect(self.ui.hub_search.setFocus)
        self.ui.actionAbout.triggered.connect(self.about)
        self.ui.actionPreferences.triggered.connect(self.preferences)
        self.ui.actionView_Mode.triggered.connect(self.ui.list.toggle_view_mode)
        # List signals
        self.ui.list.goto_location.connect(self.goto_location)
        self.ui.list.working.connect(self.ui.indicator.show)
        self.ui.list.finished.connect(self.ui.indicator.hide)
        self.ui.list.play.connect(self.play_list_item)
        self.ui.list.photo.connect(self.play_list_item_photo)
        self.ui.list.metadata_selection.connect(self.ui_update_metadata_panel)
        self.ui.list.new_titles.connect(self.ui_update_path)
        self.player_exists.connect(self.ui.list.player_state)
        self.photo_viewer_exists.connect(self.ui.list.photo_viewer_state)
        # Buttons
        self.ui.actionBack.triggered.connect(self.back)
        self.ui.actionRefresh.triggered.connect(self.reload)
        self.ui.actionHome.triggered.connect(self.home)
        self.ui.actionOn_Deck.triggered.connect(self.on_deck)
        self.ui.actionRecently_Added.triggered.connect(self.recently_added)
        self.ui.actionChannels.triggered.connect(self.channels)
        self.ui.actionHubs.triggered.connect(self.load_hubs)
        self.ui.actionMetadata.triggered.connect(self.toggle_metadata_panel)
        self.ui.actionAdd_Shortcut.toggled.connect(self.add_remove_shortcut)
        # Zoom slider
        self.ui.zoom.valueChanged.connect(self.ui.list.icon_size)
        # Sort combobox
        self.ui.sort.addItem('Default sort', None)
        self.ui.sort.addItem('Added (new)', 'addedAt:desc')
        self.ui.sort.addItem('Added (old)', 'addedAt:asc')
        self.ui.sort.addItem('Release (new)', 'originallyAvailableAt:desc')
        self.ui.sort.addItem('Release (old)', 'originallyAvailableAt:asc')
        self.ui.sort.addItem('A-Z', 'titleSort:asc')
        self.ui.sort.addItem('Z-A', 'titleSort:desc')
        self.ui.sort.addItem('Rating (high)', 'rating:desc')
        self.ui.sort.addItem('Rating (low)', 'rating:asc')
        self.ui.sort.addItem('Resolution (low)', 'mediaHeight:asc')
        self.ui.sort.addItem('Resolution (high)', 'mediaHeight:desc')
        self.ui.sort.addItem('Duration (long)', 'duration:desc')
        self.ui.sort.addItem('Duration (short)', 'duration:asc')
        self.ui.sort.currentIndexChanged.connect(self.sort)
        # Hub Search
        self.ui.hub_dock.close()
        self.ui.hub_search.returnPressed.connect(self.hub_search)
        self.ui.hub_tree.goto_location.connect(self.goto_location)
        self.ui.hub_tree.finished.connect(self.ui.indicator.hide)
        self.ui.hub_tree.finished.connect(self.ui.hub_dock.show)
        self.new_hub_search.connect(self.ui.hub_tree.search)
        self.new_hub_search.connect(self.ui.indicator.show)
        self.ui.hub_search.cancel.connect(self.ui.hub_search.hide)
        self.ui.hub_search.hide()

        self.ui.hub_tree.play.connect(self.play_list_item)
        self.ui.hub_tree.play_photo.connect(self.play_list_item_photo)

        self.session_manager.load_session()
        self.ui_update_session()
        self.show()

    def preferences(self):
        dialog = SettingsDialog()

    def about(self):
        self._about = About()
        self._about.show()

    def initialize(self, server):
        """load the given server into the browser."""
        if server is None:
            return
        logger.info('Browser: initializing browser on server={}'.format(server))
        self.session_manager.switch_server(server)
        self.location = Location.home()
        self.history = [self.location]
        self.shortcuts = {}
        self.load_shortcuts()
        self.ui_update_title()
        try:
            self.goto_location(self.location)
        except Exception as e:
            logger.error('Browser: initialize: ' + str(e))
        else:
            self.initialized = True

    @pyqtSlot(Location)
    @pyqtSlot(Location, bool)
    def goto_location(self, location, history=True):
        if not location.key.startswith('/'):
            location.key = self.location.key + '/' + location.key
        logger.info('Browser: key=' + location.key)

        self.ui_update_sort_no_signal(location.sort)
        self.ui.sort.setEnabled(location.key.startswith('/library'))

        self.location = location
        self.ui.list.add_container(self.session_manager.server, location.key, 0,
                                   self.container_size,
                                   self.ui.sort.itemData(location.sort), location.params)

        self.toggle_shortcut_button()

        if history and self.history[-1] != self.location:
            if self.history[-1].key == location.key:
                self.history.pop()
            self.history.append(self.location)

    def hub_search(self):
        query = self.ui.hub_search.text()
        s = self.session_manager.server
        if s is not None:
            self.new_hub_search.emit(s, query)

    def load_hubs(self):
        self.ui.hub_tree.goto(self.session_manager.server, '/hubs')

    @pyqtSlot()
    def toggle_search_bar(self):
        self.ui.hub_search.setVisible(not self.ui.hub_search.isVisible())
        self.ui.hub_search.clear()

    def toggle_shortcut_button(self):
        add = self.location.tuple() in self.shortcuts.values()
        self.ui.actionAdd_Shortcut.blockSignals(True)
        self.ui.actionAdd_Shortcut.setChecked(add)
        self.ui.actionAdd_Shortcut.blockSignals(False)

    def add_remove_shortcut(self, state):
        if state:
            self.add_shortcut()
        else:
            self.remove_shortcut()

    def remove_shortcut(self):
        try:
            k = [x for x in self.shortcuts if self.shortcuts[x] == self.location.tuple()][0]
        except Exception as e:
            logger.debug('failed to remove shortcut {}'.format(str(e)))
        else:
            del self.shortcuts[k]
            self.save_shortcuts()
            self.load_shortcuts()
            self.toggle_shortcut_button()

    def save_shortcuts(self):
        s = Settings()
        s.setValue('shortcuts-{}'.format(self.session_manager.server.client_identifier),
                   self.shortcuts)

    def add_shortcut(self):
        name, ok = QInputDialog.getText(self, 'Add Shortcut', 'name:')
        if ok:
            self.shortcuts[name] = self.location.tuple()
            logger.debug(self.shortcuts)
            self.save_shortcuts()
            self.load_shortcuts()
        self.toggle_shortcut_button()

    def load_shortcuts(self):
        self.ui.shortcuts.blockSignals(True)
        self.ui.shortcuts.clear()
        s = Settings()
        f = s.value('shortcuts-{}'.format(self.session_manager.server.client_identifier))
        if f:
            self.shortcuts = f
            for name, loc in f.items():
                self.ui.shortcuts.addItem(name, name)
        self.ui.shortcuts.setVisible(self.ui.shortcuts.count() > 0)
        self.ui.shortcuts.blockSignals(False)

    @pyqtSlot()
    def load_shortcut(self):
        i = self.ui.shortcuts.currentText()
        logger.debug(self.shortcuts)
        logger.debug(i)
        loc = Location(*self.shortcuts[i])
        self.goto_location(loc)

    @pyqtSlot(int)
    def action_change_server(self, index):
        try:
            server = self.session_manager.session.servers[index]
        except Exception as e:
            logger.error('Browser: unable to switch server. ' + str(e))
        else:
            self.initialize(server)

    @pyqtSlot(int)
    def action_change_user(self, index):
        logger.info('Browser: switching user -> {}'.format(self.ui.users.currentText()))
        try:
            user = self.session_manager.session.users[index]
            user_id, user_auth = user['id'], bool(int(user['protected']))
        except Exception as e:
            logger.error('Browser: unable to switch user. ' + str(e))
            self.ui_update_users_no_signal(last_index)
            return
        pin = None
        if user_auth:
            text, ok = QInputDialog.getText(self, 'Switch User', 'PIN:',
                                            QLineEdit.Password)
            if ok:
                pin = text
            else:
                self.ui_update_users_no_signal(last_index)
                return
        logger.debug('Browser: userid={}'.format(user_id))

        self.initialized = False
        self.ui.indicator.show()
        self.change_user.emit(user_id, pin)

    @pyqtSlot(str)
    def destroy_remote(self, name):
        for i, r in enumerate(self.remotes):
            if r.name == name:
                logger.debug('Browser: deleting remote ' + r.name)
                del self.remotes[i]
                return

    def create_player(self):
        self.mpvplayer = MPVPlayer()
        self.mpvplayer.show()
        self.player_exists.emit(True)
        self.ui.list.queue.connect(self.mpvplayer.queue)

    @pyqtSlot()
    def destroy_player(self):
        logger.debug('Browser: deleting mpv player.')
        self.mpvplayer = None
        self.player_exists.emit(False)

    def create_photo_viewer(self):
        if self.image_viewer is not None:
            self.image_viewer.close()
        self.image_viewer = PhotoViewer()
        self.image_viewer.closed.connect(self.destroy_photo_viewer)
        self.image_viewer.next_button.connect(self.ui.list.next_item)
        self.image_viewer.prev_button.connect(self.ui.list.prev_item)
        self.ui.list.image_selection.connect(self.image_viewer.load_image)
        self.photo_viewer_exists.emit(True)

    @pyqtSlot()
    def destroy_photo_viewer(self):
        logger.debug('Browser: deleting photo viewer.')
        self.ui.list.image_selection.disconnect()
        self.image_viewer.close()
        self.image_viewer = None
        self.photo_viewer_exists.emit(False)

    @pyqtSlot(plexdevices.media.BaseObject)
    def play_list_item(self, item):
        if self.mpvplayer is not None:
            self.mpvplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        self.mpvplayer.play(item)

    @pyqtSlot(plexdevices.media.BaseObject)
    def play_list_item_photo(self, item):
        self.create_photo_viewer()
        self.image_viewer.load_image(item)
        self.image_viewer.show()

    # Menu Actions #############################################################
    @pyqtSlot()
    def action_launch_remote(self):
        sender = self.sender()
        player = sender.data()
        port = 8000 + len(self.remotes)
        try:
            logger.info('Browser: creating remote on port {}. player={}'.format(port, player))
            remote = Remote(self.session_manager.session, player, port=port,
                            name='pdremote-{}'.format(port))
        except plexdevices.DeviceConnectionsError as e:
            logger.error(str(e))
            msg_box(str(e))
        else:
            self.remotes.append(remote)
            remote.closed.connect(self.destroy_remote)

    @pyqtSlot()
    def action_login(self):
        d = LoginDialog(session=self.session_manager.session)
        if d.exec_() == QDialog.Accepted:
            self.initialized = False
            self.ui.indicator.show()
            username, password = d.data()
            self.create_session.emit(username.strip(), password.strip())

    @pyqtSlot()
    def action_logout(self):
        self.session_manager.delete_session()
        self.ui_update_session()
        self.ui.list.clear()
        self.ui.hub_tree.clear()
        self.initialized = False

    @pyqtSlot()
    def action_manual_add_server(self):
        d = ManualServerDialog()
        if d.exec_() == QDialog.Accepted:
            protocol, address, port, token = d.data()
            self.ui.indicator.show()
            self.manual_add_server.emit(protocol, address, port, token)

    @pyqtSlot()
    def action_reload_stylesheet(self):
        app = QCoreApplication.instance()
        file = QFile(':/resources/dark.qss')
        file.open(QFile.ReadOnly)
        ss = bytes(file.readAll()).decode('latin-1')
        app.setStyleSheet(ss)

    @pyqtSlot()
    def action_trim_image_cache(self):
        DB_IMAGE.remove(5)

    @pyqtSlot()
    def action_trim_thumb_cache(self):
        DB_THUMB.remove(5)

    @pyqtSlot()
    def action_refresh_devices(self):
        self.ui.indicator.show()
        self.refresh_devices.emit()

    @pyqtSlot()
    def action_refresh_users(self):
        self.ui.indicator.show()
        self.refresh_users.emit()

    @pyqtSlot(bool, str)
    def _session_manager_cb(self, success, message):
        self.ui.indicator.hide()
        self.ui_update_session()
        if not success:
            msg_box(message)

    # Button slots #############################################################
    @pyqtSlot()
    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.goto_location(self.history[-1], history=False)

    @pyqtSlot()
    def reload(self):
        self.goto_location(self.location)

    @pyqtSlot()
    def sort(self):
        key, sort, params = self.location.tuple()
        new_sort = self.ui.sort.currentIndex()
        self.goto_location(Location(key, new_sort, params), history=False)

    @pyqtSlot()
    def home(self):
        self.history = [Location.home()]
        self.goto_location(self.history[0])

    @pyqtSlot()
    def on_deck(self):
        self.goto_location(Location.on_deck())

    @pyqtSlot()
    def recently_added(self):
        self.goto_location(Location.recently_added())

    @pyqtSlot()
    def channels(self):
        self.goto_location(Location.channels())

    @pyqtSlot()
    def toggle_metadata_panel(self):
        self.ui.metadata_panel.setVisible(not self.ui.metadata_panel.isVisible())

    # UI Updates ###############################################################
    def ui_update_servers(self):
        self.ui.servers.blockSignals(True)
        self.ui.servers.clear()
        session = self.session_manager.session
        for server in session.servers:
            self.ui.servers.addItem('{} - {}'.format(server.name, server.product),
                                    server.client_identifier)
        self.ui.servers.blockSignals(False)

    def ui_update_users(self):
        self.ui.users.blockSignals(True)
        self.ui.users.clear()
        session = self.session_manager.session
        for user in session.users:
            self.ui.users.addItem(user['title'], user['id'])
            logger.debug('{} {}'.format(user['title'], user['id']))
        self.ui.users.blockSignals(False)
        self.ui.users.setVisible(self.ui.users.count() > 0)

    @pyqtSlot(str, str)
    def ui_update_path(self, t1, t2):
        if not t1 or not t2:
            self.ui.lbl_path.setText(' / '.join(self.location.key.lstrip('/').split()))
        else:
            self.ui.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def ui_update_title(self):
        self.setWindowTitle('plexdesktop v{} - {}'.format(__version__, self.session_manager.server.name))

    @pyqtSlot(plexdevices.media.BaseObject)
    def ui_update_metadata_panel(self, media_object):
        elements = ['title', 'summary', 'year', 'duration', 'rating', 'view_offset']
        data = {x: getattr(media_object, x) for x in elements
                if hasattr(media_object, x) and getattr(media_object, x)}
        if 'summary' in data:
            data['summary'] = data['summary'][:500]
        if 'view_offset' in data:
            data['view_offset'] = timestamp_from_ms(data['view_offset'])
        if 'duration' in data:
            data['duration'] = timestamp_from_ms(data['duration'])
        if 'view_offset' in data and 'duration' in data:
            data['duration'] = data['view_offset'] + ' / ' + data['duration']
            del data['view_offset']
        txt = ['{}: {}'.format(k, str(v)) for k, v in sorted(data.items())]
        self.ui.lbl_metadata.setText('\n'.join(txt))

    def ui_update_sort_no_signal(self, index):
        self.ui.sort.blockSignals(True)
        self.ui.sort.setCurrentIndex(index)
        self.ui.sort.blockSignals(False)

    def ui_update_users_no_signal(self, index):
        self.ui.users.blockSignals(True)
        self.ui.users.setCurrentIndex(index)
        self.ui.users.blockSignals(False)

    def ui_update_servers_no_signal(self, index):
        self.ui.servers.blockSignals(True)
        self.ui.servers.setCurrentIndex(index)
        self.ui.servers.blockSignals(False)

    def ui_update_session(self):
        session = self.session_manager.session
        server = self.session_manager.server
        self.ui.menuRemotes.clear()
        self.ui_update_servers()
        self.ui_update_users()
        try:
            self.ui_update_servers_no_signal(session.servers.index(server))
        except Exception as e:
            logger.error('Browser: no servers. ' + str(e))

        try:
            self.ui_update_users_no_signal(self.ui.users.findData(self.session_manager.user))
        except Exception as e:
            logger.error('Browser: no users. ' + str(e))

        for player in session.players:
            action = QAction(str(player), self.ui.menuRemotes)
            action.setData(player)
            action.triggered.connect(self.action_launch_remote)
            self.ui.menuRemotes.addAction(action)

        if not self.initialized:
            self.initialize(self.session_manager.server)

    # QT Events ################################################################
    def closeEvent(self, event):
        self.ui.list.close()
        self.ui.hub_tree.quit()
        self.worker_thread.quit()
        self.worker_thread.wait()

    def mousePressEvent(self, event):
        if event.buttons() & Qt.BackButton:
            self.back()
            event.accept()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            degrees = event.angleDelta().y() / 8
            steps = int(degrees / 15)
            self.ui.zoom.setSliderPosition(self.ui.zoom.value() + steps * 20)
            event.accept()
        else:
            super().wheelEvent(event)
