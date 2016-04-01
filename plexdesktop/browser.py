import math
import logging
import os
from PyQt5.QtWidgets import QWidget, QAction, QMenu, QInputDialog, QFileDialog, QApplication, QLineEdit
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QCoreApplication
from PyQt5.QtGui import QCursor
from plexdesktop.ui.browser_ui import Ui_Browser
from plexdesktop.settings import Settings
from plexdesktop.player import MPVPlayer
from plexdesktop.photo_viewer import PhotoViewer
from plexdesktop.utils import *
from plexdesktop.extra_widgets import PreferencesObjectDialog
from plexdesktop.sqlcache import DB_IMAGE

import plexdevices
# import utils

logger = logging.getLogger('plexdesktop')


class Browser(QWidget):
    new_image_selection = pyqtSignal(plexdevices.BaseObject)
    new_metadata_selection = pyqtSignal(plexdevices.BaseObject)
    operate = pyqtSignal(plexdevices.Device, str, int, int, str, dict)

    def __init__(self, session, server, parent=None):
        super().__init__(parent)
        self.ui = Ui_Browser()
        self.ui.setupUi(self)
        self.ui.indicator.hide()
        self.ui.metadata_panel.hide()

        self.session = session
        self.mpvplayer = None
        self.image_viewer = None
        self.container_size = 50

        self.shortcuts = {}

        # Servers combo box
        self.update_servers()
        self.ui.servers.setCurrentIndex(self.session.servers.index(server))
        self.ui.servers.currentIndexChanged.connect(self.change_server)
        # Users combo box
        self.update_users()
        try:
            self.ui.users.setCurrentIndex(self.ui.users.findText(self.session.user))
        except Exception as e:
            logger.debug(str(e))
        self.ui.users.currentIndexChanged.connect(self.change_user)
        self.current_user = self.ui.users.currentText()
        # List signals
        self.ui.list.itemDoubleClicked.connect(self.item_double_clicked)
        self.ui.list.customContextMenuRequested.connect(self.context_menu)
        self.ui.list.itemSelectionChanged.connect(self.selection_changed)
        self.ui.list.model().working.connect(self.ui.indicator.show)
        self.ui.list.model().done.connect(self.ui.indicator.hide)
        self.ui.list.model().done.connect(self.update_path)
        # Buttons
        self.ui.btn_back.clicked.connect(self.back)
        self.ui.btn_on_deck.clicked.connect(self.on_deck)
        self.ui.btn_recently_added.clicked.connect(self.recently_added)
        self.ui.btn_home.clicked.connect(self.home)
        self.ui.btn_channels.clicked.connect(self.channels)
        self.ui.btn_view_mode.pressed.connect(self.ui.list.toggle_view_mode)
        self.ui.btn_test.pressed.connect(self.reload_stylesheet)
        self.ui.btn_reload.pressed.connect(self.reload)
        self.ui.btn_metadata.pressed.connect(self.toggle_metadata_panel)
        self.ui.btn_add_shortcut.pressed.connect(self.add_shortcut)
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

        self.new_metadata_selection.connect(self.update_metadata_panel)

        self.initialize(server)
        self.show()

    def initialize(self, server):
        """ bring the browser to its default state on the given server """
        logger.info('Browser: initializing browser on server={}'.format(server))
        settings = Settings()
        settings.setValue('last_server', server.client_identifier)
        self.server = server
        self.location = ('/library/sections', 0, None)
        self.history = [self.location]
        self.shortcuts = {}

        self.load_shortcuts()
        try:
            self.data(key=self.location[0])
        except Exception as e:
            logger.error('Browser: initialize: ' + str(e))

    def data(self, media_object=None, key=None, history=True, sort=0, params=None):
        key = key if media_object is None else media_object.key
        if not key.startswith('/'):
            key = self.location[0] + '/' + key
        logger.info('Browser: key=' + key)

        self.update_sort_no_signal(sort)
        self.ui.sort.setEnabled(key.startswith('/library'))

        self.location = (key, sort, params)
        self.ui.list.add_container(self.server, key, 0, self.container_size,
                                   self.ui.sort.itemData(sort), params)

        self.toggle_shortcut_button()

        if history and self.history[-1] != self.location:
            if self.history[-1][0] == key:
                self.history.pop()
            self.history.append(self.location)

    def toggle_shortcut_button(self):
        self.ui.btn_add_shortcut.disconnect()
        if self.location in self.shortcuts.values():
            self.ui.btn_add_shortcut.setText('- shortcut')
            self.ui.btn_add_shortcut.pressed.connect(self.remove_shortcut)
        else:
            self.ui.btn_add_shortcut.setText('+ shortcut')
            self.ui.btn_add_shortcut.pressed.connect(self.add_shortcut)

    def remove_shortcut(self):
        try:
            k = [x for x in self.shortcuts if self.shortcuts[x] == self.location][0]
        except Exception:
            logger.debug('failed to remove shortcut')
        else:
            del self.shortcuts[k]
            self.save_shortcuts()
            self.load_shortcuts()
            self.toggle_shortcut_button()

    def save_shortcuts(self):
        s = Settings()
        s.setValue('shortcuts-{}'.format(self.server.client_identifier), self.shortcuts)

    def add_shortcut(self):
        name, ok = QInputDialog.getText(self, 'Add Shortcut', 'name:')
        if ok:
            self.shortcuts[name] = self.location
            logger.debug(self.shortcuts)
            self.save_shortcuts()
            self.load_shortcuts()
            self.toggle_shortcut_button()

    def load_shortcuts(self):
        self.ui.shortcuts.disconnect()
        self.ui.shortcuts.clear()
        s = Settings()
        f = s.value('shortcuts-{}'.format(self.server.client_identifier))
        logger.debug(f)
        if f:
            self.shortcuts = f
            for name, loc in self.shortcuts.items():
                self.ui.shortcuts.addItem(name, name)
            self.ui.shortcuts.show()
        else:
            self.ui.shortcuts.hide()
        self.ui.shortcuts.activated.connect(self.load_shortcut)

    def load_shortcut(self):
        i = self.ui.shortcuts.currentText()
        logger.debug(self.shortcuts)
        logger.debug(i)
        key, sort, params = self.shortcuts[i]
        self.data(key=key, sort=sort, params=params)

    def change_server(self, index):
        try:
            server = self.session.servers[index]
        except Exception as e:
            logger.error('Browser: unable to switch server. ' + str(e))
        else:
            self.initialize(server)

    def change_user(self, index):
        last_user, new_user = self.current_user, self.ui.users.currentText()
        last_index = self.ui.users.findText(last_user)
        logger.info('Browser: switching user. {} -> {}'.format(last_user, new_user))
        try:
            user = self.session.users[index]
            user_id, user_auth = user['id'], bool(int(user['protected']))
        except Exception as e:
            logger.error('Browser: unable to switch user. ' + str(e))
            self.update_users_no_signal(last_index)
        else:
            pin = None
            if user_auth:
                text, ok = QInputDialog.getText(self, 'Switch User', 'PIN:',
                                                QLineEdit.Password)
                if ok:
                    pin = text
                else:
                    self.update_users_no_signal(last_index)
                    return
            logger.debug('Browser: userid={}'.format(user_id))
            try:
                self.session.switch_user(user_id, pin=pin)
            except plexdevices.PlexTVError as e:
                logger.error('Browser: ' + str(e))
                msg_box(str(e))
                self.update_users_no_signal(last_index)
            else:
                self.current_user = new_user
                self.update_servers()

    def create_player(self):
        self.mpvplayer = MPVPlayer()
        self.mpvplayer.show()
        self.ui.indicator.show()
        self.mpvplayer.playback_started.connect(self.ui.indicator.hide)
        self.mpvplayer.player_stopped.connect(self.ui.indicator.hide)

    def destroy_player(self):
        self.mpvplayer = None

    def create_photo_viewer(self):
        if self.image_viewer is not None:
            self.image_viewer.close()
        self.image_viewer = PhotoViewer()
        self.image_viewer.closed.connect(self.destroy_photo_viewer)
        self.image_viewer.next_button.connect(self.select_next)
        self.image_viewer.prev_button.connect(self.select_prev)
        self.new_image_selection.connect(self.image_viewer.load_image)

    def destroy_photo_viewer(self):
        self.image_viewer.close()
        self.image_viewer = None

    def select_next(self):
        self.ui.list.next_item()

    def select_prev(self):
        self.ui.list.prev_item()

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
            self.data(media_object=item, params={'query': text})

    def item_double_clicked(self, item):
        if isinstance(item, plexdevices.Directory):
            if isinstance(item, plexdevices.InputDirectory):
                self.search_prompt(item)
            elif isinstance(item, plexdevices.PreferencesDirectory):
                self.preferences_prompt(item)
            else:
                self.data(media_object=item)
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
            self.update_metadata_panel(None)

    # Button slots #############################################################
    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            key, sort, params = self.history[-1]
            self.data(key=key, sort=sort, params=params, history=False)

    def reload(self):
        key, sort, params = self.location
        self.data(key=key, sort=self.ui.sort.currentIndex(), params=params)

    def home(self):
        self.history = [('/library/sections', 0, {})]
        self.data(key='/library/sections')

    def on_deck(self):
        self.data(key='/library/onDeck')

    def recently_added(self):
        self.data(key='/library/recentlyAdded')

    def channels(self):
        self.data(key='/channels/all')

    def toggle_metadata_panel(self):
        if self.ui.metadata_panel.isVisible():
            self.ui.metadata_panel.hide()
            self.ui.btn_metadata.setText("v")
        else:
            self.ui.metadata_panel.show()
            self.ui.btn_metadata.setText("^")

    # UI Updates ###############################################################
    def reload_stylesheet(self):
        app = QCoreApplication.instance()
        with open('resources/plexdesktop.qss', 'r') as f:
            app.setStyleSheet(f.read())

    def update_servers(self):
        self.ui.servers.clear()
        for i, item in enumerate(self.session.servers):
            self.ui.servers.addItem('{} - {}'.format(item.name, item.product), i)

    def update_users(self):
        self.ui.users.clear()
        for i, item in enumerate(self.session.users):
            self.ui.users.addItem(item['title'], i)
            logger.debug('{} {}'.format(item['title'], item['id']))

    def update_path(self, t1, t2):
        self.ui.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location[0]))

    def update_metadata_panel(self, media_object):
        if media_object is None:
            self.ui.lbl_metadata.clear()
            return
        elements = ['title', 'summary', 'year', 'duration', 'rating', 'viewOffset']
        data = {k: v for k, v in media_object.data.items() if k in elements}
        if 'duration' in data:
            d = timestamp_from_ms(int(data['duration']))
            if 'viewOffset' in data:
                vo = timestamp_from_ms(int(data['viewOffset']))
                d = vo + " / " + d
                del data['viewOffset']
            data['duration'] = d
        txt = ["{}: {}".format(k, v) for k, v in data.items()]
        self.ui.lbl_metadata.setText('\n'.join(txt))

    def update_sort_no_signal(self, index):
        self.ui.sort.currentIndexChanged.disconnect()
        self.ui.sort.setCurrentIndex(index)
        self.ui.sort.currentIndexChanged.connect(self.reload)

    def update_users_no_signal(self, index):
        self.ui.users.currentIndexChanged.disconnect()
        self.ui.users.setCurrentIndex(index)
        self.ui.users.currentIndexChanged.connect(self.change_user)

    def update_servers_no_signal(self, index):
        self.ui.servers.currentIndexChanged.disconnect()
        self.ui.servers.setCurrentIndex(index)
        self.ui.servers.currentIndexChanged.connect(self.change_server)

    # QT Events ################################################################
    def closeEvent(self, event):
        self.ui.list.close()

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
                main_action.triggered.connect(self.action_play)
                actions.append(main_action)
                if self.mpvplayer is not None and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.action_queue)
                    actions.append(append_action)
            elif isinstance(item, plexdevices.Photo):
                main_action = QAction('View Photo', menu)
                main_action.triggered.connect(self.action_play_photo)
                save_action = QAction('Save', menu)
                save_action.triggered.connect(self.action_save_photo)
                actions.append(main_action)
                actions.append(save_action)
            copy_action = QAction('Copy url', menu)
            copy_action.triggered.connect(self.action_copy)
            actions.append(copy_action)
        elif isinstance(item, plexdevices.Directory):
            if isinstance(item, plexdevices.PreferencesDirectory):
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.action_settings)
                actions.append(main_action)
            else:
                main_action = QAction('Open', menu)
                main_action.triggered.connect(self.action_open)
                actions.append(main_action)
            if isinstance(item, (plexdevices.Show, plexdevices.Season, plexdevices.Album, plexdevices.Artist)):
                action = QAction('Play all', menu)
                action.triggered.connect(self.action_play)
                actions.append(action)
                if self.mpvplayer is not None and item.container.is_library:
                    append_action = QAction('Add to Queue', menu)
                    append_action.triggered.connect(self.action_queue)
                    actions.append(append_action)

        if item.markable:
            mark_action = QAction('Mark unwatched', menu)
            mark_action.triggered.connect(self.action_mark_unwatched)
            mark_action2 = QAction('Mark watched', menu)
            mark_action2.triggered.connect(self.action_mark_watched)
            actions.append(mark_action)
            actions.append(mark_action2)

        if item.has_parent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.parent_type), menu)
            open_action.triggered.connect(self.action_open_parent)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = QAction('goto: ' + plexdevices.get_type_string(item.grandparent_type), menu)
            open_action.triggered.connect(self.action_open_grandparent)
            menu.addAction(open_action)
            actions.append(open_action)

        for action in actions:
            menu.addAction(action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def action_queue(self):
        item = self.ui.list.currentItem()
        self.mpvplayer.playlist_queue_item(item)

    def action_copy(self):
        item = self.ui.list.currentItem()
        url = item.resolve_url()
        clipboard = QApplication.clipboard()
        clipboard.setText(url)

    def action_settings(self):
        self.preferences_prompt(self.ui.list.currentItem())

    def action_play(self):
        self.play_list_item(self.ui.list.currentItem())

    def action_play_photo(self):
        self.play_list_item_photo(self.ui.list.currentItem())

    def action_open(self):
        self.data(media_object=self.ui.list.currentItem())

    def action_open_parent(self):
        self.data(key=self.ui.list.currentItem().parent_key + '/children')

    def action_open_grandparent(self):
        self.data(key=self.ui.list.currentItem().grandparent_key + '/children')

    def action_mark_watched(self):
        item = self.ui.list.currentItem()
        item.mark_watched()

    def action_mark_unwatched(self):
        item = self.ui.list.currentItem()
        item.mark_unwatched()

    def action_save_photo(self):
        item = self.ui.list.currentItem()
        url = item.resolve_url()
        ext = url.split('?')[0].split('/')[-1].split('.')[-1]
        fname = '{}.{}'.format(''.join([x if x.isalnum() else "_" for x in item.title]), ext)
        logger.debug(('Browser: save_photo: item={}, url={}, ext={}, '
                      'fname={}').format(item, url, ext, fname))
        save_file, filtr = QFileDialog.getSaveFileName(self, 'Open Directory',
                                                       fname,
                                                       'Images (*.{})'.format(ext))
        if not save_file:
            return
        try:
            data = DB_IMAGE[url]
            if data is None:
                logger.debug('Browser: save_photo: downloading image')
                data = item.container.server.image(url)
            else:
                logger.debug('Browser: save_photo: image was in the cache')
        except Exception:
            return
        with open(os.path.abspath(save_file), 'wb') as f:
            logger.info('Browser: save_photo: writing to: {}'.format(save_file))
            f.write(data)
