# plexdesktop
# Copyright (c) 2016 Cory Parsons <parsons.cory@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import random

import plexdevices

from PyQt5 import QtWidgets, QtCore, QtGui

from plexdesktop import __version__

import plexdesktop.components
import plexdesktop.ui.browser_ui
import plexdesktop.extra_widgets
import plexdesktop.style
import plexdesktop.utils
import plexdesktop.sqlcache
import plexdesktop.sessionmanager
import plexdesktop.about
import plexdesktop.photo_viewer
import plexdesktop.player
import plexdesktop.player_default
import plexdesktop.remote
import plexdesktop.browserlist

logger = logging.getLogger('plexdesktop')


class Browser(plexdesktop.components.ComponentWindow):
    create_session = QtCore.pyqtSignal(str, str)
    refresh_devices = QtCore.pyqtSignal()
    refresh_users = QtCore.pyqtSignal()
    change_user = QtCore.pyqtSignal(object, str)
    manual_add_server = QtCore.pyqtSignal(str, str, str, str)
    new_hub_search = QtCore.pyqtSignal(plexdevices.device.Server, str)
    location_changed = QtCore.pyqtSignal(plexdesktop.utils.Location)

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.ui = plexdesktop.ui.browser_ui.Ui_Browser()
        self.ui.setupUi(self)


        self.session_manager = plexdesktop.sessionmanager.SessionManager()
        self.sm_thread = QtCore.QThread(self)
        self.session_manager.moveToThread(self.sm_thread)
        self.session_manager.working.connect(self.ui.indicator.show)
        self.sm_thread.start()

        self.ui.tabs.currentChanged.connect(self.tab_changed)

        self.photo_viewer = None

        # Register actions with style, assign their icon name.
        style = plexdesktop.style.Style.Instance()
        style.widget.register(self.ui.actionBack, 'glyphicons-chevron-left')
        style.widget.register(self.ui.actionForward, 'glyphicons-chevron-right')
        style.widget.register(self.ui.actionRefresh, 'glyphicons-refresh')
        style.widget.register(self.ui.actionFind, 'glyphicons-search')
        style.widget.register(self.ui.actionHome, 'glyphicons-home')
        style.widget.register(self.ui.actionOn_Deck, 'glyphicons-play')
        style.widget.register(self.ui.actionRecently_Added,
                              'glyphicons-folder-new')
        style.widget.register(self.ui.actionChannels, 'channels')
        style.widget.register(self.ui.actionMetadata, 'glyphicons-list')
        style.widget.register(self.ui.actionAdd_Shortcut, 'glyphicons-plus',
                              'glyphicons-minus')
        style.refresh()

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

        # Hide things
        self.ui.hub_dock.hide()
        self.ui.hub_search.hide()
        self.ui.indicator.hide()
        self.ui.metadata_panel.hide()

        # Make connections
        self._connections()

        # Initialize
        self.initial_load()
        # self.run_later(0, self.initial_load)

    def tab_changed(self, index):
        tab = self.ui.tabs.widget(index)
        if not tab:
            return
        self.ui.actionView_Mode.disconnect()
        self.ui.actionView_Mode.triggered.connect(tab.toggle_view_mode)
        self.ui.zoom.disconnect()
        self.ui.zoom.valueChanged.connect(tab.icon_size)

        self.ui.zoom.setMinimum(tab.min_icon_size)
        self.ui.zoom.setMaximum(tab.max_icon_size)

        server_index = self.ui.servers.findData(tab.current_server)
        if server_index >= 0:
            self.ui_update_servers_no_signal(server_index)

        self.session_manager.shortcuts = plexdesktop.sessionmanager.Shortcuts(tab.current_server)
        self.session_manager.shortcuts.shortcuts_changed.connect(self.session_manager.shortcuts_changed.emit)
        self.session_manager.shortcuts.shortcuts_loaded.connect(self.session_manager.shortcuts_loaded.emit)
        self.session_manager.shortcuts.load()

    def _connections(self):
        cm = plexdesktop.components.ComponentManager.Instance()
        # Session Manager
        self.session_manager.active.connect(self.ui.actionLogout.setEnabled)
        self.session_manager.active.connect(
            self.ui.actionRefresh_Devices.setEnabled)
        self.session_manager.active.connect(
            self.ui.actionRefresh_Users.setEnabled)
        self.session_manager.active.connect(self.ui.menuRemotes.setEnabled)
        self.session_manager.active.connect(self.ui.actionInfo.setEnabled)
        self.create_session.connect(self.session_manager.create_session)
        self.refresh_devices.connect(self.session_manager.refresh_devices)
        self.refresh_users.connect(self.session_manager.refresh_users)
        self.change_user.connect(self.session_manager.switch_user)
        self.manual_add_server.connect(self.session_manager.manual_add_server)
        self.session_manager.done.connect(self._session_manager_cb)
        self.session_manager.shortcuts_loaded.connect(self.ui_load_shortcuts)
        self.session_manager.shortcuts_changed.connect(self.ui_load_shortcuts)
        # Server Switcher
        self.ui.servers.currentIndexChanged.connect(self.action_change_server)
        # User Switcher
        self.ui.users.currentIndexChanged.connect(self.action_change_user)
        # Shortcuts
        # self.ui.shortcuts.activated.connect(self.goto_shortcut)
        self.location_changed.connect(self.ui_toggle_shortcut_button)
        # Menu
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionLogin_Refresh.triggered.connect(self.action_login)
        self.ui.actionLogout.triggered.connect(self.action_logout)
        self.ui.actionReload_Stylesheet.triggered.connect(
            self.action_reload_stylesheet)
        self.ui.actionAdd_Server.triggered.connect(
            self.action_manual_add_server)
        # self.ui.actionTrim_Image_Cache.triggered.connect(
        #     self.action_trim_image_cache)
        # self.ui.actionTrim_Thumb_Cache.triggered.connect(
        #     self.action_trim_thumb_cache)
        self.ui.actionRefresh_Devices.triggered.connect(
            self.action_refresh_devices)
        self.ui.actionRefresh_Users.triggered.connect(
            self.action_refresh_users)
        self.ui.actionFind.triggered.connect(self.ui_toggle_search_bar)
        self.ui.actionFind.triggered.connect(self.ui.hub_search.setFocus)
        self.ui.actionAbout.triggered.connect(self.about)
        self.ui.actionPreferences.triggered.connect(self.preferences)
        self.ui.actionBookmarks_Bar.triggered.connect(self.ui_toggle_bookmarks_bar)
        self.ui.actionNew_Tab.triggered.connect(self.action_new_tab)
        self.ui.actionClose_Tab.triggered.connect(self.action_close_tab)
        self.ui.actionDownloads.triggered.connect(
            self.download_manager.toggle_visible)
        self.ui.actionNew_Browser.triggered.connect(cm.create_browser)
        # Buttons
        self.ui.actionBack.triggered.connect(self.back)
        self.ui.actionForward.triggered.connect(self.forward)
        self.ui.actionRefresh.triggered.connect(self.reload)
        self.ui.actionHome.triggered.connect(self.home)
        self.ui.actionOn_Deck.triggered.connect(self.on_deck)
        self.ui.actionRecently_Added.triggered.connect(self.recently_added)
        self.ui.actionChannels.triggered.connect(self.channels)
        self.ui.actionHubs.triggered.connect(self.load_hubs)
        self.ui.actionMetadata.triggered.connect(self.ui_toggle_metadata_panel)
        self.ui.actionAdd_Shortcut.toggled.connect(self.add_remove_shortcut)
        # Sort
        self.ui.sort.currentIndexChanged.connect(self.sort)
        # Hub Search
        self.new_hub_search.connect(self.ui.hub_tree.search)
        self.new_hub_search.connect(self.ui.indicator.show)
        self.ui.hub_search.returnPressed.connect(self.hub_search)
        self.ui.hub_search.cancel.connect(self.ui.hub_search.hide)
        # Hub Tree
        self.ui.hub_tree.goto_location.connect(self.goto_location)
        self.ui.hub_tree.finished.connect(self.ui.indicator.hide)
        self.ui.hub_tree.finished.connect(self.ui.hub_dock.show)
        self.ui.hub_tree.play.connect(self.create_player)
        self.ui.hub_tree.play_photo.connect(self.create_photo_viewer)

    def run_later(self, time, cb):
        QtCore.QTimer.singleShot(time, cb)

    @property
    def download_manager(self):
        return plexdesktop.components.ComponentManager.Instance().get(
            'download_manager')

    def goto_location(self, location):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.goto_location(location)
        else:
            self.ui.tabs.new_tab(location)

    @QtCore.pyqtSlot()
    def initial_load(self):
        self.session_manager.load_session()
        self.ui_update_session()

    @QtCore.pyqtSlot()
    def preferences(self):
        dialog = plexdesktop.extra_widgets.SettingsDialog()

    @QtCore.pyqtSlot()
    def about(self):
        self._about = plexdesktop.about.About()
        self._about.show()

    def initialize(self, server, location=None):
        """load the given server into the browser."""
        if server is None:
            return
        logger.info(
            'Browser: initializing browser on server={}'.format(server))
        self.session_manager.switch_server(server)
        # Default location and reset history

        location = location if location else plexdesktop.utils.Location.home()
        cur_tab = self.ui.tabs.currentWidget()
        if not cur_tab:
            self.ui.tabs.new_tab(location, server)
        else:
            cur_tab.goto_location(location, server)

        self.ui_update_title()

    def server_changed(self, server):
        index = self.ui.servers.findData(server)
        self.ui_update_servers_no_signal(index)

    def goto_bookmark(self, checked):
        location = self.sender().data()
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.goto_location(location)

    @QtCore.pyqtSlot()
    def hub_search(self):
        query = self.ui.hub_search.text()
        tab = self.ui.tabs.currentWidget()
        if tab:
            s = tab.current_server
            if s is not None:
                self.new_hub_search.emit(s, query)

    @QtCore.pyqtSlot()
    def load_hubs(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            self.ui.hub_tree.goto(tab.current_server, '/hubs')

    @QtCore.pyqtSlot(bool)
    def add_remove_shortcut(self, state):
        if state:
            name, ok = QtWidgets.QInputDialog.getText(self, 'Add Shortcut',
                                                      'name:')
            if ok:
                self.session_manager.shortcuts.add(name, self.ui.tabs.currentWidget().location)
        else:
            self.session_manager.shortcuts.remove(self.ui.tabs.currentWidget().location)

    @QtCore.pyqtSlot()
    def ui_load_shortcuts(self):
        self.ui.bookmarksToolBar.clear()
        for i, (name, loc) in enumerate(self.session_manager.shortcuts.items()):
            action = QtWidgets.QAction(name, self.ui.bookmarksToolBar)
            action.setData(loc)
            action.triggered.connect(self.goto_bookmark)
            action.setShortcut('ALT+{}'.format(i + 1))
            self.ui.bookmarksToolBar.addAction(action)

    def ui_toggle_bookmarks_bar(self):
        self.ui.bookmarksToolBar.setVisible(not self.ui.bookmarksToolBar.isVisible())

    @QtCore.pyqtSlot(int)
    def action_change_server(self, index):
        try:
            server = self.session_manager.session.servers[index]
        except Exception as e:
            logger.error('Browser: unable to switch server. ' + str(e))
        else:
            self.initialize(server)

    def action_change_server2(self, state):
        server = self.sender().data()
        self.initialize(server)

    @QtCore.pyqtSlot(int)
    def action_change_user(self, index):
        logger.info('Browser: switching user -> {}'.format(
            self.ui.users.currentText()))
        try:
            last_index = self.ui.users.findData(self.session_manager.user)
        except (ValueError, IndexError):
            last_index = 0
        try:
            user = self.ui.users.itemData(index)
        except Exception as e:
            logger.error('Browser: unable to switch user. ' + str(e))
            self.ui_update_users_no_signal(last_index)
            return
        print(last_index, self.session_manager.user, index, user)
        pin = None
        if user.protected:
            text, ok = QtWidgets.QInputDialog.getText(
                self, 'Switch User', 'PIN:', QtWidgets.QLineEdit.Password)
            if ok:
                pin = text
            else:
                self.ui_update_users_no_signal(last_index)
                return
        logger.debug('Browser: userid={}'.format(user.id))

        # self.initialized = False
        self.ui.tabs.quit()
        self.change_user.emit(user, str(pin))

    def create_player(self, item):
        cm = plexdesktop.components.ComponentManager.Instance()
        player = cm.create_component(plexdesktop.player_default.MPVPlayer)
        player.working.connect(self.ui.indicator.show)
        player.finished.connect(self.ui.indicator.hide)
        player.play(item)

    def create_photo_viewer(self, item):
        cm = plexdesktop.components.ComponentManager.Instance()
        if cm.exists(self.photo_viewer):
            viewer = cm.get(self.photo_viewer)
        else:
            viewer = cm.create_component(plexdesktop.photo_viewer.PhotoViewer)
            self.photo_viewer = viewer.name
            viewer.next_button.connect(self.ui.tabs.currentWidget().next_item)
            viewer.prev_button.connect(self.ui.tabs.currentWidget().prev_item)
            self.ui.hub_tree.play_photo.connect(viewer.load_image)
            self.ui.tabs.currentWidget().image_selection.connect(viewer.load_image)
        viewer.show()
        viewer.raise_()
        viewer.load_image(item)

    # Menu Actions ############################################################
    @QtCore.pyqtSlot()
    def action_launch_remote(self):
        player = self.sender().data()
        port = random.randint(8000, 9000)
        logger.info('Browser: creating remote on port {}. player={}'.format(
            port, player))
        try:
            cm = plexdesktop.components.ComponentManager.Instance()
            cm.create_component(plexdesktop.remote.Remote,
                                session=self.session_manager.session,
                                player=player, port=port)
        except plexdevices.DeviceConnectionsError as e:
            logger.error('Browser: action_launch_remote: {}'.format(str(e)))
            plexdesktop.utils.msg_box(str(e))

    @QtCore.pyqtSlot()
    def action_login(self):
        d = plexdesktop.extra_widgets.LoginDialog(
            session=self.session_manager.session)
        if d.exec_() == QtWidgets.QDialog.Accepted:
            # self.initialized = False
            username, password = d.data()
            self.create_session.emit(username.strip(), password.strip())

    @QtCore.pyqtSlot()
    def action_logout(self):
        self.session_manager.delete_session()
        self.ui_update_session()
        self.ui.tabs.currentWidget().clear()
        self.ui.hub_tree.clear()
        # self.initialized = False

    @QtCore.pyqtSlot()
    def action_manual_add_server(self):
        d = plexdesktop.extra_widgets.ManualServerDialog()
        if d.exec_() == QtWidgets.QDialog.Accepted:
            protocol, address, port, token = d.data()
            self.manual_add_server.emit(protocol, address, port, token)

    @QtCore.pyqtSlot()
    def action_reload_stylesheet(self):
        style = plexdesktop.style.Style.Instance()
        style.refresh()

    # @QtCore.pyqtSlot()
    # def action_trim_image_cache(self):
    #     plexdesktop.sqlcache.DB_IMAGE.remove()

    # @QtCore.pyqtSlot()
    # def action_trim_thumb_cache(self):
    #     plexdesktop.sqlcache.DB_THUMB.remove()

    @QtCore.pyqtSlot()
    def action_refresh_devices(self):
        self.refresh_devices.emit()

    @QtCore.pyqtSlot()
    def action_refresh_users(self):
        self.refresh_users.emit()

    @QtCore.pyqtSlot(bool, str)
    def _session_manager_cb(self, success, message):
        self.ui.indicator.hide()
        self.ui_update_session()
        if not success:
            plexdesktop.utils.msg_box(message)

    def action_new_tab(self):
        current = self.ui.tabs.currentWidget()
        if current:
            self.ui.tabs.new_tab(current.location, current.current_server)
        else:
            self.ui.tabs.new_tab(plexdesktop.utils.Location.home(), self.ui.servers.currentData())

    def action_close_tab(self):
        current = self.ui.tabs.currentIndex()
        self.ui.tabs.close_tab(current)

    # Button slots ############################################################
    @QtCore.pyqtSlot()
    def back(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.go_back()

    @QtCore.pyqtSlot()
    def forward(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.go_forward()

    @QtCore.pyqtSlot()
    def reload(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.reload()

    @QtCore.pyqtSlot()
    def sort(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.sort(self.ui.sort.currentData())

    @QtCore.pyqtSlot()
    def home(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.go_home()

    @QtCore.pyqtSlot()
    def on_deck(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.goto_location(plexdesktop.utils.Location.on_deck())

    @QtCore.pyqtSlot()
    def recently_added(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.goto_location(plexdesktop.utils.Location.recently_added())

    @QtCore.pyqtSlot()
    def channels(self):
        tab = self.ui.tabs.currentWidget()
        if tab:
            tab.goto_location(plexdesktop.utils.Location.channels())

    @QtCore.pyqtSlot()
    def ui_toggle_metadata_panel(self):
        self.ui.metadata_panel.setVisible(
            not self.ui.metadata_panel.isVisible())

    @QtCore.pyqtSlot()
    def ui_toggle_search_bar(self):
        self.ui.hub_search.setVisible(not self.ui.hub_search.isVisible())
        self.ui.hub_search.clear()

    @QtCore.pyqtSlot()
    def ui_toggle_shortcut_button(self):
        self.ui.actionAdd_Shortcut.blockSignals(True)
        tab = self.ui.tabs.currentWidget()
        if tab:
            self.ui.actionAdd_Shortcut.setChecked(
                tab.location in self.session_manager.shortcuts)
        self.ui.actionAdd_Shortcut.blockSignals(False)

    # UI Updates ##############################################################
    def ui_update_servers(self):
        self.ui.servers.blockSignals(True)
        self.ui.servers.clear()
        self.ui.menuServers.clear()
        session = self.session_manager.session
        for i, server in enumerate(session.servers):
            self.ui.servers.addItem(server.name, server)
            action = QtWidgets.QAction(server.name, self.ui.menuServers)
            action.setData(server)
            action.triggered.connect(self.action_change_server2)
            action.setShortcut('CTRL+{}'.format(i + 1))
            self.ui.menuServers.addAction(action)
        self.ui.servers.blockSignals(False)

    def ui_update_users(self):
        self.ui.users.blockSignals(True)
        self.ui.users.clear()
        session = self.session_manager.session
        with plexdesktop.sqlcache.db_thumb() as cache:
            for index, user in enumerate(session.users):
                self.ui.users.addItem(user.title, user)
                if user.thumb in cache:
                    img = QtGui.QPixmap()
                    img.loadFromData(cache[user.thumb])
                    icon = QtGui.QIcon(img)
                    self.ui.users.setItemIcon(index, icon)
                logger.debug('{} {}'.format(user.title, user))
        self.ui.users.blockSignals(False)
        self.ui.users.setVisible(self.ui.users.count() > 0)

    def ui_update_title(self):
        self.setWindowTitle('{name} - plexdesktop v{v}'.format(
            v=__version__, name=self.ui.tabs.currentWidget().current_server.name))

    @QtCore.pyqtSlot(plexdevices.media.BaseObject)
    def ui_update_metadata_panel(self, media_object):
        # TODO: make this good or remove it.
        elements = ['title', 'summary', 'year', 'duration', 'rating',
                    'view_offset']
        data = {x: getattr(media_object, x) for x in elements
                if hasattr(media_object, x) and getattr(media_object, x)}
        if 'summary' in data:
            data['summary'] = data['summary'][:500]
        if 'view_offset' in data:
            data['view_offset'] = plexdesktop.utils.timestamp_from_ms(
                data['view_offset'])
        if 'duration' in data:
            data['duration'] = plexdesktop.utils.timestamp_from_ms(
                data['duration'])
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
        sm = self.session_manager

        self.ui.menuRemotes.clear()
        self.ui_update_servers()
        self.ui_update_users()

        current_tab = self.ui.tabs.currentWidget()

        if current_tab:
            last_server = [x for x in range(self.ui.servers.count()) if
                           self.ui.servers.itemData(x) == current_tab.current_server]
            self.ui_update_servers_no_signal(last_server[0] if last_server else -1)

        last_user = [x for x in range(self.ui.users.count()) if
                     self.ui.users.itemData(x) == sm.user]
        self.ui_update_users_no_signal(last_user[0] if last_user else -1)

        for player in sm.session.players:
            action = QtWidgets.QAction(str(player), self.ui.menuRemotes)
            action.setData(player)
            action.triggered.connect(self.action_launch_remote)
            self.ui.menuRemotes.addAction(action)

        # if not self.initialized:
        if not current_tab:
            self.initialize(sm.current_server)

    def ui_update_zoom(self, size):
        self.ui.zoom.blockSignals(True)
        self.ui.zoom.setSliderPosition(size.height())
        self.ui.zoom.blockSignals(False)

    # QT Events ###############################################################
    def closeEvent(self, event):
        self.ui.tabs.quit()
        self.ui.hub_tree.quit()
        self.sm_thread.quit()
        self.sm_thread.wait()
        self._shutdown()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.buttons() & QtCore.Qt.BackButton:
            self.back()
            event.accept()

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            degrees = event.angleDelta().y() / 8
            steps = int(degrees / 15)
            self.ui.zoom.setSliderPosition(self.ui.zoom.value() + steps * 20)
            event.accept()
        else:
            super().wheelEvent(event)
