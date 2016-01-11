import math
import time
from PyQt5.QtWidgets import QWidget, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QSettings, QThread, QPoint
from PyQt5.QtGui import QCursor
import browser_ui
from browserlist import BrowserList, BrowserListItem
from settings import Settings
from player import MPVPlayer
from photo_viewer import PhotoViewer
import plexdevices

class ContainerWorker(QObject):
    done = pyqtSignal(plexdevices.MediaContainer)
    finished = pyqtSignal(str)

    def __init__(self, server, key, page=0, size=20, sort=None):
        super().__init__()
        self.server = server
        self.key = key
        self.page = page
        self.size = size
        self.sort = sort

    def run(self):
        container = self.server.media_container(self.key, page=self.page,
                                                size=self.size,
                                                params=(None if self.sort is None
                                                        else {'sort': self.sort}))
        self.done.emit(container)
        self.finished.emit(self.key)


class Browser(QWidget, browser_ui.Ui_Browser):
    operate = pyqtSignal()

    def __init__(self, session, server, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)
        self.indicator.hide()

        self.session = session
        self.server = server
        self.location = '/library/sections'
        self.history = [self.location]
        self.mpvplayer = None
        self.image_viewer = None
        self.cur_page = 0
        self.total_pages = 0
        self.container_size = 20
        self.playing = None
        self.thread = QThread()
        self.thread.start()
        self.workers = {}

        self.btn_back.clicked.connect(self.back)
        self.btn_on_deck.clicked.connect(self.on_deck)
        self.btn_recently_added.clicked.connect(self.recently_added)
        self.btn_home.clicked.connect(self.home)
        self.btn_channels.clicked.connect(self.channels)
        self.list.itemDoubleClicked.connect(self.item_double_clicked)
        self.list.verticalScrollBar().valueChanged.connect(self.endless_scroll)
        self.zoom.valueChanged.connect(self.list.icon_size)

        self.list.customContextMenuRequested.connect(self.context_menu)

        self.sort.addItem('', None)
        self.sort.addItem('added (new)', 'addedAt:desc')
        self.sort.addItem('added (old)', 'addedAt:asc')
        self.sort.addItem('release (new)', 'originallyAvailableAt:desc')
        self.sort.addItem('release (old)', 'originallyAvailableAt:asc')
        self.sort.addItem('a-z', 'titleSort:asc')
        self.sort.addItem('z-a', 'titleSort:desc')
        self.sort.addItem('rating (high)', 'rating:desc')
        self.sort.addItem('rating (low)', 'rating:asc')
        self.sort.addItem('resolution (low)', 'mediaHeight:asc')
        self.sort.addItem('resolution (high)', 'mediaHeight:desc')
        self.sort.addItem('duration (long)', 'duration:desc')
        self.sort.addItem('duration (short)', 'duration:asc')
        self.sort.currentIndexChanged.connect(self.reload)

        self.data(key=self.location)
        self.show()

    def context_menu(self, pos):
        item = self.list.currentItem()
        # print('[{}] {}: {}'.format(item.media['_elementType'],
        #                            item.media.parent.get('identifier'),
        #                            item.media['title']))
        menu = QMenu(self)
        if item.media.is_playable:
            play_action = QAction('play', menu)
            play_action.triggered.connect(self.action_play)
            menu.addAction(play_action)
        elif item.media.is_photo:
            play_action = QAction('view photo', menu)
            play_action.triggered.connect(self.action_play_photo)
            menu.addAction(play_action)
        elif item.media.is_photo_album:
            play_action = QAction('view album', menu)
            play_action.triggered.connect(self.action_play_photo_album)
            menu.addAction(play_action)
            open_action = QAction('open', menu)
            open_action.triggered.connect(self.action_open)
            menu.addAction(open_action)
        else:
            open_action = QAction('open', menu)
            open_action.triggered.connect(self.action_open)
            menu.addAction(open_action)

        if item.media.has_parent:
            open_action = QAction('goto parent', menu)
            open_action.triggered.connect(self.action_open_parent)
            menu.addAction(open_action)
        if item.media.has_grandparent:
            open_action = QAction('goto grandparent', menu)
            open_action.triggered.connect(self.action_open_grandparent)
            menu.addAction(open_action)

        if item.media.markable:
            watched_action = QAction('mark watched', menu)
            unwatched_action = QAction('mark unwatched', menu)
            watched_action.triggered.connect(self.action_mark_watched)
            unwatched_action.triggered.connect(self.action_mark_unwatched)
            menu.addAction(watched_action)
            menu.addAction(unwatched_action)

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def action_play(self):
        self.play_list_item(self.list.currentItem())

    def action_play_photo(self):
        self.play_list_item_photo(self.list.currentItem())

    def action_play_photo_album(self):
        self.play_list_item_photo_album(self.list.currentItem())        

    def action_open(self):
        self.data(item=self.list.currentItem())

    def action_open_parent(self):
        self.data(key=self.list.currentItem().media['parentKey'] + '/children')

    def action_open_grandparent(self):
        self.data(key=self.list.currentItem().media['grandparentKey'] + '/children')

    def action_mark_watched(self):
        item = self.list.currentItem()
        if item.media.markable:
            item.media.mark_watched()
            item.clear_bg()

    def action_mark_unwatched(self):
        item = self.list.currentItem()
        if item.media.markable:
            item.media.mark_unwatched()
            item.clear_bg()

    def create_player(self):
        self.mpvplayer = MPVPlayer()

    def destroy_player(self):
        self.mpvplayer = None

    def closeEvent(self, event):
        self.thread.quit()
        while self.thread.isRunning():
            time.sleep(0.1)

    def channels(self):
        self.data(key='/channels/all')

    def home(self):
        self.history = ['/library/sections']
        self.data(key='/library/sections')

    def on_deck(self):
        self.data(key='/library/onDeck')

    def recently_added(self):
        self.data(key='/library/recentlyAdded')

    def reload(self):
        self.data(key=self.location)

    def back(self):
        print(self.history)
        if len(self.history) > 1:
            self.history.pop()
            self.data(key=self.history[-1], history=False)

    def play_list_item(self, item):
        if self.mpvplayer is not None:
            self.mpvplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        self.mpvplayer.player_stopped.connect(item.update_offset)
        self.mpvplayer.play(item.media)
        # self.layout().addWidget(self.mpvplayer)

    def play_list_item_photo(self, item):
        if self.image_viewer is not None:
            self.image_viewer.close()
        self.image_viewer = PhotoViewer()
        self.image_viewer.closed.connect(self._remove_photo_viewer)
        self.image_viewer.load_image(item.media)
        self.image_viewer.show()

    def play_list_item_photo_album(self, item):
        self.image_viewer = PhotoViewer()
        self.image_viewer.closed.connect(self._remove_photo_viewer)
        self.image_viewer.hide()
        worker = ContainerWorker(self.server, item.media['key'])
        worker.done.connect(self.image_viewer.load_gallery)
        worker.done.connect(self.indicator.hide)
        worker.done.connect(self.image_viewer.show)
        worker.finished.connect(self._remove_worker)
        worker.moveToThread(self.thread)
        self.operate.connect(worker.run)
        self.operate.connect(self.indicator.show)
        self.workers[item.media['key']] = worker
        self.operate.emit()

    def item_double_clicked(self, item):
        if item.media.is_playable:
            self.play_list_item(item)
        elif item.media.is_photo:
            self.play_list_item_photo(item)
        elif item.media.is_photo_album:
            self.play_list_item_photo_album(item)
        else:
            self.data(item=item)

    def data(self, item=None, key=None, history=True):
        if item is not None:
            key = item.media['key'] if item.media['key'].startswith('/') else self.location+'/'+item.media['key']
        print(key)

        self.list.clear()
        self.cur_page = 0
        self.location = key
        
        if key.startswith('/library'):
            self.sort.setEnabled(True)
            sort = self.sort.itemData(self.sort.currentIndex())
        else:
            self.sort.setEnabled(False)
            sort = None

        self.page(key, self.cur_page, self.container_size, sort=sort)
       
        if history and self.history[-1] != key:
            self.history.append(key)

        if not self.list.verticalScrollBar().isVisible() and self.cur_page < self.total_pages:
            self.page(self.location, self.cur_page, self.container_size, sort=sort)

    def endless_scroll(self, value):
        if value >= self.list.verticalScrollBar().maximum() * 0.9:
            if self.cur_page < self.total_pages:
                sort = self.sort.itemData(self.sort.currentIndex())
                self.page(self.location, self.cur_page, sort=sort)

    def page(self, key, page=0, size=20, sort=None):
        self.cur_page += 1
        worker = ContainerWorker(self.server, key, page, size, sort)
        worker.done.connect(self.update_list)
        worker.done.connect(self.indicator.hide)
        worker.finished.connect(self._remove_worker)
        worker.moveToThread(self.thread)
        self.operate.connect(worker.run)
        self.operate.connect(self.indicator.show)
        self.workers[key] = worker
        self.operate.emit()

    def _remove_worker(self, key):
        try:
            del self.workers[key]
        except KeyError:
            pass

    def _remove_photo_viewer(self):
        self.image_viewer.close()
        self.image_viewer = None

    def update_list(self, container):
        self.list.add_container(container)
        self.total_pages = math.ceil(container['totalSize']/self.container_size)
        self.list.refresh_icons()
        self.update_title()
        self.update_path(container.get('title1', self.location.split('/')[-2]),
                         container.get('title2', self.location.split('/')[-1]))

    def update_path(self, t1, t2):
        self.lbl_path.setText('{} / {}'.format(t1[:25], t2[:25]))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location))
