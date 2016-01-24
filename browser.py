import math
import logging
import os
from PyQt5.QtWidgets import QWidget, QAction, QMenu, QInputDialog, QFileDialog, QApplication
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QCoreApplication
from PyQt5.QtGui import QCursor
import browser_ui
from settings import Settings
from player import MPVPlayer
from photo_viewer import PhotoViewer
import plexdevices
import utils
from extra_widgets import PreferencesObjectDialog
from sqlcache import DB_IMAGE
logger = logging.getLogger('plexdesktop')


class Browser(QWidget):
    new_image_selection = pyqtSignal(plexdevices.MediaObject)
    new_metadata_selection = pyqtSignal(plexdevices.MediaObject)
    operate = pyqtSignal(plexdevices.Device, str, int, int, str, dict)

    def __init__(self, session, server, parent=None):
        super(self.__class__, self).__init__(parent)
        self.ui = browser_ui.Ui_Browser()
        self.ui.setupUi(self)
        self.ui.indicator.hide()

        self.session = session
        for i, item in enumerate(self.session.servers):
            self.ui.servers.addItem('{} - {}'.format(item.name, item.product), i)
        self.ui.servers.setCurrentIndex(self.session.servers.index(server))

        self.mpvplayer = None
        self.image_viewer = None
        self.container_size = 50

        self.ui.list.model.working.connect(self.ui.indicator.show)
        self.ui.list.model.done.connect(self.ui.indicator.hide)
        self.ui.list.model.done.connect(self.update_path)

        self.new_metadata_selection.connect(self.update_metadata_panel)

        self.ui.btn_back.clicked.connect(self.back)
        self.ui.btn_on_deck.clicked.connect(self.on_deck)
        self.ui.btn_recently_added.clicked.connect(self.recently_added)
        self.ui.btn_home.clicked.connect(self.home)
        self.ui.btn_channels.clicked.connect(self.channels)
        self.ui.btn_view_mode.pressed.connect(self.ui.list.toggle_view_mode)
        self.ui.btn_test.pressed.connect(self.reload_stylesheet)

        self.ui.zoom.valueChanged.connect(self.ui.list.icon_size)

        self.ui.list.itemDoubleClicked.connect(self.item_double_clicked)
        self.ui.list.customContextMenuRequested.connect(self.context_menu)
        self.ui.list.itemSelectionChanged.connect(self.selection_changed)

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

        self.ui.servers.currentIndexChanged.connect(self.change_server)

        self.initialize(server)
        self.ui.metadata_panel.hide()
        self.ui.btn_metadata.pressed.connect(self.toggle_metadata_panel)
        self.show()

    def reload_stylesheet(self):
        app = QCoreApplication.instance()
        with open('plexdesktop.qss', 'r') as f:
            app.setStyleSheet(f.read())

    def initialize(self, server):
        logger.info('Browser: initializing browser on server={}'.format(server))
        settings = Settings()
        settings.setValue('last_server', server.client_identifier)
        self.server = server
        self.location = '/library/sections'
        self.history = [(self.location, 0)]
        self.data(key=self.location)

    def change_server(self, index):
        self.initialize(self.session.servers[index])

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

    def selection_changed(self):
        if self.ui.list.currentItem() is None:
            return
        m = self.ui.list.currentItem()
        if m.is_photo:
            self.new_image_selection.emit(m)
        if m.is_photo or m.is_video or m.is_audio or m.is_directory:
            self.new_metadata_selection.emit(m)
        else:
            self.update_metadata_panel(None)

    def update_metadata_panel(self, media_object):
        if media_object is None:
            self.ui.lbl_metadata.clear()
            return
        elements = ['title', 'summary', 'year', 'duration', 'rating', 'viewOffset']
        data = {k: v for k, v in media_object.data.items() if k in elements}
        if 'duration' in data:
            d = utils.timestamp_from_ms(int(data['duration']))
            if 'viewOffset' in data:
                vo = utils.timestamp_from_ms(int(data['viewOffset']))
                d = vo + " / " + d
                del data['viewOffset']
            data['duration'] = d
        txt = ["{}: {}".format(k, v) for k, v in data.items()]
        self.ui.lbl_metadata.setText('\n'.join(txt))

    def toggle_metadata_panel(self):
        if self.ui.metadata_panel.isVisible():
            self.ui.metadata_panel.hide()
            self.ui.btn_metadata.setText("v")
        else:
            self.ui.metadata_panel.show()
            self.ui.btn_metadata.setText("^")

    def context_menu(self, pos):
        item = self.ui.list.currentItem()

        menu = QMenu(self)
        actions = []
        if item.is_video or item.is_audio:
            main_action = QAction('Play', menu)
            main_action.triggered.connect(self.action_play)
            copy_action = QAction('Copy url', menu)
            copy_action.triggered.connect(self.action_copy)
            actions.append(main_action)
            actions.append(copy_action)
            if self.mpvplayer is not None:
                append_action = QAction('Add to Queue', menu)
                append_action.triggered.connect(self.action_queue)
                actions.append(append_action)
        elif item.is_photo:
            main_action = QAction('View Photo', menu)
            main_action.triggered.connect(self.action_play_photo)
            copy_action = QAction('Copy url', menu)
            copy_action.triggered.connect(self.action_copy)
            actions.append(main_action)
            actions.append(copy_action)
        elif item.is_settings:
            main_action = QAction('Open', menu)
            main_action.triggered.connect(self.action_settings)
            actions.append(main_action)
        else:
            main_action = QAction('Open', menu)
            main_action.triggered.connect(self.action_open)
            actions.append(main_action)

        if item.is_album:
            action = QAction('Play all', menu)
            action.triggered.connect(self.action_play)
            actions.append(action)
            if self.mpvplayer is not None:
                append_action = QAction('Add to Queue', menu)
                append_action.triggered.connect(self.action_queue)
                actions.append(append_action)

        if item.is_photo:
            save_action = QAction('Save', menu)
            save_action.triggered.connect(self.action_save_photo)
            # menu.addAction(save_action)
            actions.append(save_action)

        if item.has_parent:
            open_action = QAction('goto: ' + item.parent_name, menu)
            open_action.triggered.connect(self.action_open_parent)
            # menu.addAction(open_action)
            actions.append(open_action)
        if item.has_grandparent:
            open_action = QAction('goto: ' + item.grandparent_name, menu)
            open_action.triggered.connect(self.action_open_grandparent)
            menu.addAction(open_action)
            actions.append(open_action)

        if item.markable:
            if item.watched:
                mark_action = QAction('Mark unwatched', menu)
                mark_action.triggered.connect(self.action_mark_unwatched)
            else:
                mark_action = QAction('Mark watched', menu)
                mark_action.triggered.connect(self.action_mark_watched)
            # menu.addAction(mark_action)
            actions.append(mark_action)

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
        self.data(item=self.ui.list.currentItem())

    def action_open_parent(self):
        self.data(key=self.ui.list.currentItem()['parentKey'] + '/children')

    def action_open_grandparent(self):
        self.data(key=self.ui.list.currentItem()['grandparentKey'] + '/children')

    def action_mark_watched(self):
        item = self.ui.list.currentItem()
        if item.markable:
            item.mark_watched()

    def action_mark_unwatched(self):
        item = self.ui.list.currentItem()
        if item.markable:
            item.mark_unwatched()

    def action_save_photo(self):
        item = self.ui.list.currentItem()
        url = item.resolve_url()
        ext = url.split('?')[0].split('/')[-1].split('.')[-1]
        fname = '{}.{}'.format(''.join([x if x.isalnum() else "_" for x in item['title']]), ext)
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
                data = item.parent.server.image(url)
            else:
                logger.debug('Browser: save_photo: image was in the cache')
        except Exception:
            return
        with open(os.path.abspath(save_file), 'wb') as f:
            logger.info('Browser: save_photo: writing to: {}'.format(save_file))
            f.write(data)

    def select_next(self):
        self.ui.list.next_item()

    def select_prev(self):
        self.ui.list.prev_item()

    def closeEvent(self, event):
        self.ui.list.close()

    def channels(self):
        self.data(key='/channels/all')

    def home(self):
        self.history = [('/library/sections', 0)]
        self.data(key='/library/sections')

    def on_deck(self):
        self.data(key='/library/onDeck')

    def recently_added(self):
        self.data(key='/library/recentlyAdded')

    def reload(self):
        key, sort = self.location
        self.data(key=key, sort=self.ui.sort.currentIndex())

    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            key, sort = self.history[-1]
            self.data(key=key, sort=sort, history=False)

    def play_list_item(self, item):
        if self.mpvplayer is not None:
            self.mpvplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        # self.mpvplayer.player_stopped.connect(item.update_offset)
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
            self.data(key=item['key'], params={'query': text})

    def item_double_clicked(self, item):
        if item.is_video or item.is_audio:
            self.play_list_item(item)
        elif item.is_photo:
            self.play_list_item_photo(item)
        elif item.is_input:
            self.search_prompt(item)
        elif item.is_settings:
            self.preferences_prompt(item)
        else:
            self.data(item=item)

    def data(self, item=None, key=None, history=True, sort=0, params={}):
        key = key if item is None else item['key']
        if not key.startswith('/'):
            key = self.location[0] + '/' + key
        logger.info('Browser: key=' + key)

        self.ui.sort.currentIndexChanged.disconnect()
        self.ui.sort.setCurrentIndex(sort)
        self.ui.sort.currentIndexChanged.connect(self.reload)
        self.ui.sort.setEnabled(key.startswith('/library'))

        self.location = (key, sort)
        self.params = params

        self.ui.list.add_container(self.server, key, 0, self.container_size,
                                   self.ui.sort.itemData(sort), params)

        if history and self.history[-1] != (key, sort):
            if self.history[-1][0] == key:
                self.history[-1] = (key, self.ui.sort.currentIndex())
            else:
                self.history.append((key, self.ui.sort.currentIndex()))

    def update_path(self, t1, t2):
        self.ui.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location[0]))

    def mousePressEvent(self, event):
        if event.buttons() & Qt.BackButton:
            self.back()
            event.accept()
