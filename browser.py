import os
import subprocess
import math
import threading
from PyQt5.QtWidgets import QWidget, QAction, QMenu
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QSettings, QThread, QPoint
import browser_ui
from browserlist import BrowserList, BrowserListItem
from settings import Settings
from player import MPVPlayer
import plexdevices

class ContainerWorker(QObject):
    done = pyqtSignal(plexdevices.MediaContainer)
    finished = pyqtSignal(str)

    def __init__(self, server, key, page=0, size=20):
        super().__init__()
        self.server = server
        self.key = key
        self.page = page
        self.size = size

    def run(self):
        container = self.server.media_container(self.key, page=self.page, size=self.size)
        self.done.emit(container)
        self.finished.emit(self.key)


class Browser(QWidget, browser_ui.Ui_Browser):
    operate = pyqtSignal()

    def __init__(self, session, server, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)
        self.session = session
        self.server = server
        self.location = '/library/sections'
        self.history = [self.location]
        self.mpvplayer = None
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
        self.list.itemDoubleClicked.connect(self.data)
        self.list.verticalScrollBar().valueChanged.connect(self.endless_scroll)
        self.zoom.sliderMoved.connect(self.list.icon_size)

        self.list.customContextMenuRequested.connect(self.context_menu)

        self.data(key=self.location)
        self.show()

    def context_menu(self, pos):
        item = self.list.currentItem()
        print('[{}] {}: {}'.format(item.media['_elementType'],
                                   item.media.parent.get('identifier'),
                                   item.media['title']))
        menu = QMenu(self)
        if item.media.playable:
            play_action = QAction('play', menu)
            play_action.triggered.connect(self.action_play)
            menu.addAction(play_action)
        else:
            open_action = QAction('open', menu)
            open_action.triggered.connect(self.action_open)
            menu.addAction(open_action)
        if item.media.markable:
            watched_action = QAction('mark watched', menu)
            unwatched_action = QAction('mark unwatched', menu)
            watched_action.triggered.connect(self.action_mark_watched)
            unwatched_action.triggered.connect(self.action_mark_unwatched)
            menu.addAction(watched_action)
            menu.addAction(unwatched_action)

        if not menu.isEmpty():
            menu.popup(self.mapToGlobal(pos))

    def action_play(self):
        self.play_list_item(self.list.currentItem())

    def action_open(self):
        self.data(item=self.list.currentItem())

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
            self.mvpplayer.close()
        self.create_player()
        self.mpvplayer.player_stopped.connect(self.destroy_player)
        self.mpvplayer.player_stopped.connect(item.update_offset)
        self.mpvplayer.play(item.media)

    def data(self, item=None, key=None, history=True):
        if item is not None:
            key = item.media['key'] if item.media['key'].startswith('/') else self.location+'/'+item.media['key']
        print(key)

        if item is not None and item.media['_elementType'] in ['Video', 'Track']:
            self.play_list_item(item)
            return

        self.list.clear()
        self.cur_page = 0
        self.location = key
        self.page(key, self.cur_page, self.container_size)
       
        if history and self.history[-1] != key:
            self.history.append(key)

        if not self.list.verticalScrollBar().isVisible() and self.cur_page < self.total_pages:
            self.page(self.location, self.cur_page, self.container_size)

    def endless_scroll(self, value):      
        if value >= self.list.verticalScrollBar().maximum() * 0.9:
            if self.cur_page < self.total_pages:
                self.page(self.location, self.cur_page)

    def page(self, key, page=0, size=20):
        self.cur_page += 1
        worker = ContainerWorker(self.server, key, page, size)
        worker.done.connect(self.update_list)
        worker.finished.connect(self._remove_worker)
        worker.moveToThread(self.thread)
        self.operate.connect(worker.run)
        self.workers[key] = worker
        self.operate.emit()

    def _remove_worker(self, key):
        try:
            del self.workers[key]
        except KeyError:
            pass

    def update_list(self, container):
        self.list.add_container(container)
        self.total_pages = math.ceil(container['totalSize']/self.container_size)
        self.list.refresh_icons()
        self.update_title()
        self.update_path(container.get('title1', self.location.split('/')[-2]),
                         container.get('title2', self.location.split('/')[-1]))

    def update_path(self, t1, t2):
        self.lbl_path.setText('{} / {}'.format(t1, t2))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location))
