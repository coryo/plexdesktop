import os
import subprocess
import math
import threading
from PyQt5.QtWidgets import QWidget, QAction
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QSettings, QThread, QPoint
import browser_ui
from browserlist import BrowserList, BrowserListItem
from settings import Settings
from player import MPVPlayer

class ContainerWorker(QObject):
    done = pyqtSignal(dict)
    finished = pyqtSignal(str)

    def __init__(self, server, key, page=0, size=20):
        super().__init__()
        self.server = server
        self.key = key
        self.page = page
        self.size = size

    def run(self):
        data = self.server.container(self.key, page=self.page, size=self.size)
        # print(data)
        self.done.emit(data)
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

        self.watched_action = QAction('mark watched', self)
        self.unwatched_action = QAction('mark unwatched', self)
        self.watched_action.triggered.connect(self.mark_watched)
        self.unwatched_action.triggered.connect(self.mark_unwatched)
        self.list.addAction(self.watched_action)
        self.list.addAction(self.unwatched_action)

        self.data(key=self.location)
        self.show()

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

    def data(self, item=None, key=None, history=True):
        if item is not None:
            key = item['key'] if item['key'].startswith('/') else self.location+'/'+item['key']
        print(key)

        if item is not None and item['_elementType'] in ['Video', 'Track']:
            self.play_item(item)
            self.playing = item
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

    def update_list(self, data):
        for item in data['_children']:
            self.list.addItem(BrowserListItem(self.server, data, item, self.list))

        self.total_pages = math.ceil(data['totalSize']/self.container_size)
        self.title1 = data.get('title1', self.location.split('/')[-2])
        self.title2 = data.get('title2', self.location.split('/')[-1])
        self.list.refresh_icons()
        self.update_title()
        self.update_path()

    def update_path(self):
        self.lbl_path.setText('{} / {}'.format(self.title1, self.title2))

    def update_title(self):
        self.setWindowTitle('{}: {}'.format(self.server.name, self.location))

    def play_item(self, item):
        parts = [part['key'] for part in item['_children'][0]['_children']]
        offset = int(item.get('viewOffset', 0))
        key = parts[0]

        if key.startswith('/system/services/'):
            data = self.server.container(key)
            key = data['_children'][0]['key']

        if key.startswith('/:/'):
            data = self.server.container(key)
            print(data)
            key = data['_children'][0]['key']
            print(key)
            url = key
        else:
            url = '{}{}?X-Plex-Token={}'.format(self.server.active.url, key, self.server.access_token)

        item.data['key'] = key
        self.mpvplayer = MPVPlayer()
        self.mpvplayer.player_stopped.connect(self.player_done)
        self.mpvplayer._play(url, item)

    def player_done(self, offset):
        print('player_done')
        if 'ratingKey' in self.playing.data:
            self.server.set_view_offset(self.playing['ratingKey'], offset)
        self.playing.update_offset(offset)
        self.playing = None
        del self.mpvplayer
        self.mpvplayer = None

    def mark_watched(self):
        items = self.list.selectedItems()
        for item in items:
            if 'ratingKey' not in item.data:
                continue
            self.server.mark_watched(item['ratingKey'])
            item.clear_bg()

    def mark_unwatched(self):
        items = self.list.selectedItems()
        for item in items:
            if 'ratingKey' not in item.data:
                continue
            self.server.mark_unwatched(item['ratingKey'])
            item.clear_bg()
