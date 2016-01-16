import math
from PyQt5.QtWidgets import QWidget, QAction, QMenu, QInputDialog, QListView
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QSettings, QThread, QPoint
from PyQt5.QtGui import QCursor
import browser_ui
from settings import Settings
from player import MPVPlayer
from photo_viewer import PhotoViewer
import plexdevices
import utils


class ContainerWorker(QObject):
    done = pyqtSignal(plexdevices.MediaContainer)
    finished = pyqtSignal()

    def run(self, server, key, page=0, size=20, sort="", params={}):
        p = {} if not sort else {'sort': sort}
        if params:
            p.update(params)
        try:
            data = server.container(key, page=page, size=size, params=p)
        except (plexdevices.exceptions.DeviceConnectionsError, TypeError) as e:
            print(str(e))
        else:
            container = plexdevices.MediaContainer(server, data)
            self.done.emit(container)
        self.finished.emit()


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

        self._worker_thread = QThread()
        self._worker = ContainerWorker()
        self._worker.moveToThread(self._worker_thread)
        self.operate.connect(self._worker.run)
        self.operate.connect(self.ui.indicator.show)
        self._worker.done.connect(self._update_list)
        self._worker.finished.connect(self.ui.indicator.hide)
        self._worker_thread.start()

        self.new_metadata_selection.connect(self.update_metadata_panel)

        self.ui.btn_back.clicked.connect(self.back)
        self.ui.btn_on_deck.clicked.connect(self.on_deck)
        self.ui.btn_recently_added.clicked.connect(self.recently_added)
        self.ui.btn_home.clicked.connect(self.home)
        self.ui.btn_channels.clicked.connect(self.channels)
        self.ui.btn_sort.pressed.connect(self.reload)
        self.ui.btn_view_mode.pressed.connect(self.ui.list.toggle_view_mode)

        self.ui.zoom.valueChanged.connect(self.ui.list.icon_size)

        self.ui.list.itemDoubleClicked.connect(self.item_double_clicked)
        self.ui.list.verticalScrollBar().valueChanged.connect(self._endless_scroll)
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

        self.ui.servers.currentIndexChanged.connect(self.change_server)

        self.initialize(server)
        self.ui.metadata_panel.hide()
        self.ui.btn_metadata.pressed.connect(self.toggle_metadata_panel)
        self.show()

    def initialize(self, server):
        self.server = server
        self.location = '/library/sections'
        self.history = [(self.location, 0)]
        self.cur_page = 0
        self.total_pages = 0
        self.data(key=self.location)

    def change_server(self, index):
        self.initialize(self.session.servers[index])

    def create_player(self):
        self.mpvplayer = MPVPlayer()
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
        m = self.ui.list.currentItem().media
        if m.is_photo:
            self.new_image_selection.emit(m)
        if m.is_photo or m.is_video or m.is_audio:
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
        if item.media.is_video or item.media.is_audio:
            main_action = QAction('Play', menu)
            main_action.triggered.connect(self.action_play)
        elif item.media.is_photo:
            main_action = QAction('View Photo', menu)
            main_action.triggered.connect(self.action_play_photo)
        else:
            main_action = QAction('Open', menu)
            main_action.triggered.connect(self.action_open)
        menu.addAction(main_action)

        if item.media.has_parent:
            open_action = QAction('goto: ' + item.media.parent_name, menu)
            open_action.triggered.connect(self.action_open_parent)
            menu.addAction(open_action)
        if item.media.has_grandparent:
            open_action = QAction('goto: ' + item.media.grandparent_name, menu)
            open_action.triggered.connect(self.action_open_grandparent)
            menu.addAction(open_action)

        if item.media.markable:
            if item.media.watched:
                mark_action = QAction('Mark unwatched', menu)
                mark_action.triggered.connect(self.action_mark_unwatched)
            else:
                mark_action = QAction('Mark watched', menu)
                mark_action.triggered.connect(self.action_mark_watched)
            menu.addAction(mark_action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def action_play(self):
        self.play_list_item(self.ui.list.currentItem())

    def action_play_photo(self):
        self.play_list_item_photo(self.ui.list.currentItem())

    def action_open(self):
        self.data(item=self.ui.list.currentItem())

    def action_open_parent(self):
        self.data(key=self.ui.list.currentItem().media['parentKey'] + '/children')

    def action_open_grandparent(self):
        self.data(key=self.ui.list.currentItem().media['grandparentKey'] + '/children')

    def action_mark_watched(self):
        item = self.ui.list.currentItem()
        if item.media.markable:
            item.media.mark_watched()
            item.clear_bg()

    def action_mark_unwatched(self):
        item = self.ui.list.currentItem()
        if item.media.markable:
            item.media.mark_unwatched()
            item.clear_bg()

    def select_next(self):
        cur_row = self.ui.list.currentRow()
        if cur_row >= self.ui.list.count() - 1:
            return
        self.ui.list.setCurrentRow(cur_row + 1)

    def select_prev(self):
        cur_row = self.ui.list.currentRow()
        if cur_row < 1:
            return
        self.ui.list.setCurrentRow(cur_row - 1)

    def closeEvent(self, event):
        self.ui.list.close()
        self._worker_thread.quit()
        self._worker_thread.wait()

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
        print(self.history)
        if len(self.history) > 1:
            self.history.pop()
            key, sort = self.history[-1]
            self.data(key=key, sort=sort, history=False)

    def play_list_item(self, item):
        if self.mpvplayer is not None:
            self.mpvplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        self.mpvplayer.player_stopped.connect(item.update_offset)
        self.mpvplayer.play(item.media)

    def play_list_item_photo(self, item):
        self.create_photo_viewer()
        self.image_viewer.load_image(item.media)
        self.image_viewer.show()

    def search_prompt(self, item):
        text, ok = QInputDialog.getText(self, 'Search', 'query:')
        if ok:
            self.data(key=item.media['key'], params={'query': text})

    def item_double_clicked(self, item):
        if item.media.is_video or item.media.is_audio:
            self.play_list_item(item)
        elif item.media.is_photo:
            self.play_list_item_photo(item)
        elif item.media.is_input:
            self.search_prompt(item)
        else:
            self.data(item=item)

    def data(self, item=None, key=None, history=True, sort=0, params={}):
        key = key if item is None else item.media['key']
        if not key.startswith('/'):
            key = self.location[0] + '/' + key
        print(key)

        self.ui.sort.setCurrentIndex(sort)
        if key.startswith('/library'):
            self.ui.sort.setEnabled(True)
            self.ui.btn_sort.setEnabled(True)
        else:
            self.ui.sort.setEnabled(False)
            self.ui.btn_sort.setEnabled(False)

        self.ui.list.clear()
        self.cur_page = 0
        self.location = (key, sort)
        self.params = params

        self._page(key, self.cur_page, self.container_size, sort=sort, params=params)

        if history and self.history[-1] != (key, sort):
            if self.history[-1][0] == key:
                self.history[-1] = (key, self.ui.sort.currentIndex())
            else:
                self.history.append((key, self.ui.sort.currentIndex()))

        if not self.ui.list.verticalScrollBar().isVisible() and self.cur_page < self.total_pages:
            self._page(key, self.cur_page, self.container_size, sort=sort, params=params)

    def _endless_scroll(self, value):
        if value >= self.ui.list.verticalScrollBar().maximum() * 0.9:
            if self.cur_page < self.total_pages:
                key, sort = self.location
                self._page(key, self.cur_page, self.container_size, sort=sort, params=self.params)

    def _page(self, key, page=0, size=20, sort=0, params={}):
        self.cur_page += 1
        self.operate.emit(self.server, key, page, size, self.ui.sort.itemData(sort), params)

    def _update_list(self, container):
        if self.ui.list.count() > 0:
            self.ui.list.reset()
        self.ui.list.add_container(container)
        self.total_pages = math.ceil(container['totalSize'] / self.container_size)
        self.update_title()
        self.update_path(container.get('title1', self.location[0].split('/')[-2]),
                         container.get('title2', self.location[0].split('/')[-1]))

    def update_path(self, t1, t2):
        self.ui.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location[0]))

    def mousePressEvent(self, event):
        if event.buttons() & Qt.BackButton:
            self.back()
            event.accept()
