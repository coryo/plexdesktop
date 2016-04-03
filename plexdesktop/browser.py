import logging
import os
from threading import Thread
from PyQt5.QtWidgets import (QDialog, QMainWindow, QAction, QMenu, QInputDialog,
                             QFileDialog, QApplication, QLineEdit)
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication, QThread
from PyQt5.QtGui import QCursor
from plexdesktop.ui.browser_ui import Ui_Browser
from plexdesktop.settings import Settings
from plexdesktop.player import MPVPlayer
from plexdesktop.photo_viewer import PhotoViewer
from plexdesktop.utils import *
from plexdesktop.extra_widgets import (PreferencesObjectDialog, ManualServerDialog,
                                       LoginDialog)
from plexdesktop.sqlcache import DB_IMAGE, DB_THUMB
from plexdesktop.remote import Remote
from plexdesktop.sessionmanager import SessionManager
import plexdevices

logger = logging.getLogger('plexdesktop')


class Location(object):
    def __init__(self, key, sort=0, params=None):
        self.key = key
        self.sort = sort
        self.params = params

    def tuple(self):
        return (self.key, self.sort, self.params)

    @staticmethod
    def home():
        return Location('/library/sections')

    @staticmethod
    def on_deck():
        return Location('/library/onDeck')

    @staticmethod
    def recently_added():
        return Location('/library/recentlyAdded')

    @staticmethod
    def channels():
        return Location('/channels/all')


class Browser(QMainWindow):
    new_image_selection = pyqtSignal(plexdevices.BaseObject)
    new_metadata_selection = pyqtSignal(plexdevices.BaseObject)
    create_session = pyqtSignal(str, str)
    refresh_devices = pyqtSignal()
    refresh_users = pyqtSignal()
    change_user = pyqtSignal(str, str)
    manual_add_server = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Browser()
        self.ui.setupUi(self)
        self.ui.indicator.hide()
        self.ui.metadata_panel.hide()
        self.ui.statusbar.hide()

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
        # List signals
        self.ui.list.itemDoubleClicked.connect(self.item_double_clicked)
        self.ui.list.customContextMenuRequested.connect(self.context_menu)
        self.ui.list.itemSelectionChanged.connect(self.selection_changed)
        self.ui.list.model().working.connect(self.ui.indicator.show)
        self.ui.list.model().done.connect(self.ui.indicator.hide)
        self.ui.list.model().done.connect(self.ui_update_path)
        # Buttons
        self.ui.btn_back.clicked.connect(self.back)
        self.ui.btn_on_deck.clicked.connect(self.on_deck)
        self.ui.btn_recently_added.clicked.connect(self.recently_added)
        self.ui.btn_home.clicked.connect(self.home)
        self.ui.btn_channels.clicked.connect(self.channels)
        self.ui.btn_view_mode.pressed.connect(self.ui.list.toggle_view_mode)
        self.ui.btn_reload.pressed.connect(self.reload)
        self.ui.btn_metadata.pressed.connect(self.toggle_metadata_panel)
        self.ui.btn_add_shortcut.pressed.connect(self.action_add_shortcut)
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
        self.ui.sort.currentIndexChanged.connect(self.reload)

        self.new_metadata_selection.connect(self.ui_update_metadata_panel)

        self.session_manager.load_session()

        self.ui_update_session()

        self.show()

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

    def toggle_shortcut_button(self):
        self.ui.btn_add_shortcut.disconnect()
        if self.location.tuple() in self.shortcuts.values():
            self.ui.btn_add_shortcut.setText('- shortcut')
            self.ui.btn_add_shortcut.pressed.connect(self.remove_shortcut)
        else:
            self.ui.btn_add_shortcut.setText('+ shortcut')
            self.ui.btn_add_shortcut.pressed.connect(self.action_add_shortcut)

    def remove_shortcut(self):
        try:
            k = [x for x in self.shortcuts if self.shortcuts[x] == self.location.key][0]
        except Exception:
            logger.debug('failed to remove shortcut')
        else:
            del self.shortcuts[k]
            self.save_shortcuts()
            self.load_shortcuts()
            self.toggle_shortcut_button()

    def save_shortcuts(self):
        s = Settings()
        s.setValue('shortcuts-{}'.format(self.session_manager.server.client_identifier),
                   self.shortcuts)

    def action_add_shortcut(self):
        name, ok = QInputDialog.getText(self, 'Add Shortcut', 'name:')
        if ok:
            self.shortcuts[name] = self.location.tuple()
            logger.debug(self.shortcuts)
            self.save_shortcuts()
            self.load_shortcuts()
            self.toggle_shortcut_button()

    def load_shortcuts(self):
        self.ui.shortcuts.disconnect()
        self.ui.shortcuts.clear()
        s = Settings()
        f = s.value('shortcuts-{}'.format(self.session_manager.server.client_identifier))
        if f:
            self.shortcuts = f
            for name, loc in f.items():
                self.ui.shortcuts.addItem(name, name)
        self.ui.shortcuts.setVisible(self.ui.shortcuts.count() > 0)
        self.ui.shortcuts.activated.connect(self.load_shortcut)

    def load_shortcut(self):
        i = self.ui.shortcuts.currentText()
        logger.debug(self.shortcuts)
        logger.debug(i)
        loc = Location(*self.shortcuts[i])
        self.goto_location(loc)

    def action_change_server(self, index):
        try:
            server = self.session_manager.session.servers[index]
        except Exception as e:
            logger.error('Browser: unable to switch server. ' + str(e))
        else:
            self.initialize(server)

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

    def destroy_remote(self, name):
        for i, r in enumerate(self.remotes):
            if r.name == name:
                logger.debug('Browser: deleting remote ' + r.name)
                del self.remotes[i]
                return

    def create_player(self):
        self.mpvplayer = MPVPlayer()
        self.mpvplayer.show()
        self.ui.indicator.show()
        self.mpvplayer.playback_started.connect(self.ui.indicator.hide)
        self.mpvplayer.player_stopped.connect(self.ui.indicator.hide)

    def destroy_player(self):
        logger.debug('Browser: deleting mpv player.')
        self.mpvplayer = None

    def create_photo_viewer(self):
        if self.image_viewer is not None:
            self.image_viewer.close()
        self.image_viewer = PhotoViewer()
        self.image_viewer.closed.connect(self.destroy_photo_viewer)
        self.image_viewer.next_button.connect(self.ui.list.next_item)
        self.image_viewer.prev_button.connect(self.ui.list.prev_item)
        self.new_image_selection.connect(self.image_viewer.load_image)

    def destroy_photo_viewer(self):
        logger.debug('Browser: deleting photo viewer.')
        self.new_image_selection.disconnect()
        self.image_viewer.close()
        self.image_viewer = None

    def play_list_item(self, item):
        if self.mpvplayer is not None:
            self.mpvplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        self.mpvplayer.play(item)

    def play_list_item_photo(self, item):
        self.create_photo_viewer()
        self.image_viewer.load_image(item)
        self.image_viewer.show()

    def preferences_prompt(self, item):
        dialog = PreferencesObjectDialog(item, parent=self)

    def search_prompt(self, item):
        text, ok = QInputDialog.getText(self, 'Search', 'query:')
        if ok:
            self.goto_location(Location(item.key, params={'query': text}))

    def item_double_clicked(self, item):
        if isinstance(item, plexdevices.Directory):
            if isinstance(item, plexdevices.InputDirectory):
                self.search_prompt(item)
            elif isinstance(item, plexdevices.PreferencesDirectory):
                self.preferences_prompt(item)
            else:
                self.goto_location(Location(item.key))
        elif isinstance(item, plexdevices.MediaItem):
            if isinstance(item, (plexdevices.Movie, plexdevices.Episode,
                                 plexdevices.VideoClip, plexdevices.Track)):
                self.play_list_item(item)
            elif isinstance(item, plexdevices.Photo):
                self.play_list_item_photo(item)

    def selection_changed(self):
        if self.ui.list.currentItem() is None:
            return
        m = self.ui.list.currentItem()
        logger.debug(repr(m))
        if isinstance(m, (plexdevices.MediaItem, plexdevices.MediaDirectory)):
            if isinstance(m, plexdevices.Photo):
                self.new_image_selection.emit(m)
            self.new_metadata_selection.emit(m)
        else:
            self.ui_update_metadata_panel(None)

    # Menu Actions #############################################################
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

    def action_login(self):
        d = LoginDialog(session=self.session_manager.session)
        if d.exec_() == QDialog.Accepted:
            self.initialized = False
            self.ui.indicator.show()
            username, password = d.data()
            self.create_session.emit(username.strip(), password.strip())

    def action_logout(self):
        self.session_manager.delete_session()
        self.ui_update_session()
        self.ui.list.clear()
        self.initialized = False

    def action_manual_add_server(self):
        d = ManualServerDialog()
        if d.exec_() == QDialog.Accepted:
            protocol, address, port, token = d.data()
            self.ui.indicator.show()
            self.manual_add_server.emit(protocol, address, port, token)

    def action_reload_stylesheet(self):
        app = QCoreApplication.instance()
        try:
            with open('resources/plexdesktop.qss', 'r') as f:
                app.setStyleSheet(f.read())
        except EnvironmentError as e:
            logger.error('Browser: reload_stylesheet: ' + str(e))

    def action_trim_image_cache(self):
        DB_IMAGE.remove(5)

    def action_trim_thumb_cache(self):
        DB_THUMB.remove(5)

    def action_refresh_devices(self):
        self.ui.indicator.show()
        self.refresh_devices.emit()

    def action_refresh_users(self):
        self.ui.indicator.show()
        self.refresh_users.emit()

    def _session_manager_cb(self, success, message):
        self.ui.indicator.hide()
        self.ui_update_session()
        if not success:
            msg_box(message)

    # Button slots #############################################################
    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.goto_location(self.history[-1], history=False)

    def reload(self):
        self.goto_location(self.location)

    def home(self):
        self.history = [Location.home()]
        self.goto_location(self.history[0])

    def on_deck(self):
        self.goto_location(Location.on_deck())

    def recently_added(self):
        self.goto_location(Location.recently_added())

    def channels(self):
        self.goto_location(Location.channels())

    def toggle_metadata_panel(self):
        self.ui.metadata_panel.setVisible(not self.ui.metadata_panel.isVisible())
        self.ui.btn_metadata.setText('v' if self.ui.btn_metadata.text() == '^' else '^')

    # UI Updates ###############################################################
    def ui_update_servers(self):
        self.ui.servers.currentIndexChanged.disconnect()
        self.ui.servers.clear()
        session = self.session_manager.session
        for server in session.servers:
            self.ui.servers.addItem('{} - {}'.format(server.name, server.product),
                                    server.client_identifier)
        self.ui.servers.currentIndexChanged.connect(self.action_change_server)

    def ui_update_users(self):
        self.ui.users.currentIndexChanged.disconnect()
        self.ui.users.clear()
        session = self.session_manager.session
        for user in session.users:
            self.ui.users.addItem(user['title'], user['id'])
            logger.debug('{} {}'.format(user['title'], user['id']))
        self.ui.users.currentIndexChanged.connect(self.action_change_user)
        self.ui.users.setVisible(self.ui.users.count() > 0)

    def ui_update_path(self, t1, t2):
        self.ui.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def ui_update_title(self):
        self.setWindowTitle('plexdesktop - ' + self.session_manager.server.name)

    def ui_update_metadata_panel(self, media_object):
        elements = ['title', 'summary', 'year', 'duration', 'rating', 'view_offset']
        data = {x: getattr(media_object, x) for x in elements if hasattr(media_object, x)}
        if 'duration' in data:
            if data['duration'] > 0:
                data['duration'] = timestamp_from_ms(int(data['duration']))
                if data['view_offset'] > 0:
                    data['duration'] = (timestamp_from_ms(data['view_offset']) +
                                        ' / ' + data['duration'])
            else:
                del data['duration']
            del data['view_offset']
        if 'year' in data and not data['year']:
            del data['year']
        txt = ['{}: {}'.format(k, str(v)) for k, v in sorted(data.items())]
        self.ui.lbl_metadata.setText('\n'.join(txt))

    def ui_update_sort_no_signal(self, index):
        self.ui.sort.currentIndexChanged.disconnect()
        self.ui.sort.setCurrentIndex(index)
        self.ui.sort.currentIndexChanged.connect(self.reload)

    def ui_update_users_no_signal(self, index):
        self.ui.users.currentIndexChanged.disconnect()
        self.ui.users.setCurrentIndex(index)
        self.ui.users.currentIndexChanged.connect(self.action_change_user)

    def ui_update_servers_no_signal(self, index):
        self.ui.servers.currentIndexChanged.disconnect()
        self.ui.servers.setCurrentIndex(index)
        self.ui.servers.currentIndexChanged.connect(self.action_change_server)

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
        self.worker_thread.quit()
        self.worker_thread.wait()

    def mousePressEvent(self, event):
        if event.buttons() & Qt.BackButton:
            self.back()
            event.accept()

    # Context Menu #############################################################
    def context_menu(self, pos):
        item = self.ui.list.currentItem()

        menu = QMenu(self)
        actions = []

        if isinstance(item, plexdevices.MediaItem):
            if isinstance(item, (plexdevices.Movie, plexdevices.Episode,
                                 plexdevices.VideoClip, plexdevices.Track)):
                main_action = QAction('Play', menu)
                main_action.triggered.connect(self.cm_play)
                actions.append(main_action)
                if self.mpvplayer is not None and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)
            elif isinstance(item, plexdevices.Photo):
                main_action = QAction('View Photo', menu)
                main_action.triggered.connect(self.cm_play_photo)
                save_action = QAction('Save', menu)
                save_action.triggered.connect(self.cm_save_photo)
                actions.append(main_action)
                actions.append(save_action)
            copy_action = QAction('Copy url', menu)
            copy_action.triggered.connect(self.cm_copy)
            actions.append(copy_action)
        elif isinstance(item, plexdevices.Directory):
            if isinstance(item, plexdevices.PreferencesDirectory):
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.cm_settings)
                actions.append(main_action)
            else:
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.cm_open)
                actions.append(main_action)
            if isinstance(item, (plexdevices.Show, plexdevices.Season,
                                 plexdevices.Album, plexdevices.Artist)):
                action = QAction('Play all', menu)
                action.triggered.connect(self.cm_play)
                actions.append(action)
                if self.mpvplayer is not None and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.cm_queue)
                    actions.append(append_action)

        if item.markable:
            mark_action = QAction('Mark unwatched', menu)
            mark_action.triggered.connect(self.cm_mark_unwatched)
            mark_action2 = QAction('Mark watched', menu)
            mark_action2.triggered.connect(self.cm_mark_watched)
            actions.append(mark_action)
            actions.append(mark_action2)

        if item.has_parent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.parent_type), menu)
            open_action.triggered.connect(self.cm_open_parent)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.grandparent_type), menu)
            open_action.triggered.connect(self.cm_open_grandparent)
            menu.addAction(open_action)
            actions.append(open_action)

        for action in actions:
            action.setData(item)
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def cm_queue(self):
        self.mpvplayer.playlist_queue_item(self.sender().data())

    def cm_copy(self):
        url = self.sender().data().resolve_url()
        QApplication.clipboard().setText(url)

    def cm_settings(self):
        self.preferences_prompt(self.sender().data())

    def cm_play(self):
        self.play_list_item(self.sender().data())

    def cm_play_photo(self):
        self.play_list_item_photo(self.sender().data())

    def cm_open(self):
        self.goto_location(Location(self.sender().data().key))

    def cm_open_parent(self):
        self.goto_location(Location(self.sender().data().parent_key + '/children'))

    def cm_open_grandparent(self):
        self.goto_location(Location(self.sender().data().grandparent_key + '/children'))

    def cm_mark_watched(self):
        self.sender().data().mark_watched()

    def cm_mark_unwatched(self):
        self.sender().data().mark_unwatched()

    def cm_save_photo(self):
        item = self.sender().data()
        url = item.resolve_url()
        ext = url.split('?')[0].split('/')[-1].split('.')[-1]
        fname = '{}.{}'.format(''.join([x if x.isalnum() else "_" for x in item.title]), ext)
        logger.debug(('Browser: save_photo: item={}, url={}, ext={}, '
                      'fname={}').format(item, url, ext, fname))
        save_file, filtr = QFileDialog.getSaveFileName(self, 'Open Directory',
                                                       fname,
                                                       'Images (*.{})'.format(ext))
        if save_file:
            self.ui.indicator.show()
            t = Thread(target=self.write_image, args=(item, url, save_file))
            t.start()

    def write_image(self, item, url, file):
        try:
            data = DB_IMAGE[url]
            if data is None:
                logger.debug('Browser: write_image: downloading image')
                data = item.container.server.image(url)
            else:
                logger.debug('Browser: write_image: image was in the cache')
        except Exception as e:
            logger.error('Browser: write_image: ' + str(e))
        else:
            with open(os.path.abspath(file), 'wb') as f:
                logger.info('Browser: write_image: writing to: {}'.format(file))
                f.write(data)
        self.ui.indicator.hide()
