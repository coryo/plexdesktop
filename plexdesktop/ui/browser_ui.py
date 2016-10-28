# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'plexdesktop\ui\browser.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Browser(object):
    def setupUi(self, Browser):
        Browser.setObjectName("Browser")
        Browser.resize(639, 536)
        self.centralwidget = QtWidgets.QWidget(Browser)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(4, 4, 4, 4)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.hub_search = HubSearch(self.centralwidget)
        self.hub_search.setObjectName("hub_search")
        self.verticalLayout.addWidget(self.hub_search)
        self.tabs = BrowserTabs(self.centralwidget)
        self.tabs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setTabBarAutoHide(False)
        self.tabs.setObjectName("tabs")
        self.verticalLayout.addWidget(self.tabs)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.servers = QtWidgets.QComboBox(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.servers.setFont(font)
        self.servers.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.servers.setObjectName("servers")
        self.horizontalLayout_4.addWidget(self.servers)
        self.users = QtWidgets.QComboBox(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.users.setFont(font)
        self.users.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.users.setObjectName("users")
        self.horizontalLayout_4.addWidget(self.users)
        self.indicator = QtWidgets.QProgressBar(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.indicator.sizePolicy().hasHeightForWidth())
        self.indicator.setSizePolicy(sizePolicy)
        self.indicator.setMaximumSize(QtCore.QSize(30, 16777215))
        self.indicator.setMaximum(0)
        self.indicator.setProperty("value", -1)
        self.indicator.setTextVisible(False)
        self.indicator.setInvertedAppearance(False)
        self.indicator.setObjectName("indicator")
        self.horizontalLayout_4.addWidget(self.indicator)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem)
        self.sort = QtWidgets.QComboBox(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.sort.setFont(font)
        self.sort.setObjectName("sort")
        self.horizontalLayout_4.addWidget(self.sort)
        self.zoom = QtWidgets.QSlider(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.zoom.sizePolicy().hasHeightForWidth())
        self.zoom.setSizePolicy(sizePolicy)
        self.zoom.setMinimumSize(QtCore.QSize(125, 0))
        self.zoom.setMinimum(24)
        self.zoom.setMaximum(300)
        self.zoom.setProperty("value", 32)
        self.zoom.setSliderPosition(32)
        self.zoom.setOrientation(QtCore.Qt.Horizontal)
        self.zoom.setObjectName("zoom")
        self.horizontalLayout_4.addWidget(self.zoom)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.metadata_panel = QtWidgets.QWidget(self.centralwidget)
        self.metadata_panel.setEnabled(True)
        self.metadata_panel.setObjectName("metadata_panel")
        self.grid_layout_2 = QtWidgets.QGridLayout(self.metadata_panel)
        self.grid_layout_2.setContentsMargins(0, 0, 0, 0)
        self.grid_layout_2.setSpacing(0)
        self.grid_layout_2.setObjectName("grid_layout_2")
        self.lbl_metadata = QtWidgets.QLabel(self.metadata_panel)
        self.lbl_metadata.setText("")
        self.lbl_metadata.setWordWrap(True)
        self.lbl_metadata.setObjectName("lbl_metadata")
        self.grid_layout_2.addWidget(self.lbl_metadata, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.metadata_panel)
        Browser.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(Browser)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 639, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuSession = QtWidgets.QMenu(self.menubar)
        self.menuSession.setObjectName("menuSession")
        self.menuRemotes = QtWidgets.QMenu(self.menuSession)
        self.menuRemotes.setObjectName("menuRemotes")
        self.menuServers = QtWidgets.QMenu(self.menuSession)
        self.menuServers.setObjectName("menuServers")
        self.menu_Help = QtWidgets.QMenu(self.menubar)
        self.menu_Help.setObjectName("menu_Help")
        self.menuWindow = QtWidgets.QMenu(self.menubar)
        self.menuWindow.setObjectName("menuWindow")
        self.menu_View = QtWidgets.QMenu(self.menubar)
        self.menu_View.setObjectName("menu_View")
        Browser.setMenuBar(self.menubar)
        self.navToolBar = QtWidgets.QToolBar(Browser)
        self.navToolBar.setIconSize(QtCore.QSize(16, 16))
        self.navToolBar.setFloatable(False)
        self.navToolBar.setObjectName("navToolBar")
        Browser.addToolBar(QtCore.Qt.TopToolBarArea, self.navToolBar)
        self.locationToolBar = QtWidgets.QToolBar(Browser)
        self.locationToolBar.setIconSize(QtCore.QSize(16, 16))
        self.locationToolBar.setFloatable(False)
        self.locationToolBar.setObjectName("locationToolBar")
        Browser.addToolBar(QtCore.Qt.TopToolBarArea, self.locationToolBar)
        self.hub_dock = QtWidgets.QDockWidget(Browser)
        self.hub_dock.setObjectName("hub_dock")
        self.dockWidgetContents_3 = QtWidgets.QWidget()
        self.dockWidgetContents_3.setObjectName("dockWidgetContents_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.hub_tree = TreeView(self.dockWidgetContents_3)
        self.hub_tree.setObjectName("hub_tree")
        self.verticalLayout_2.addWidget(self.hub_tree)
        self.hub_dock.setWidget(self.dockWidgetContents_3)
        Browser.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.hub_dock)
        self.bookmarksToolBar = QtWidgets.QToolBar(Browser)
        self.bookmarksToolBar.setObjectName("bookmarksToolBar")
        Browser.addToolBar(QtCore.Qt.TopToolBarArea, self.bookmarksToolBar)
        Browser.insertToolBarBreak(self.bookmarksToolBar)
        self.actionPreferences = QtWidgets.QAction(Browser)
        self.actionPreferences.setObjectName("actionPreferences")
        self.actionLogin_Refresh = QtWidgets.QAction(Browser)
        self.actionLogin_Refresh.setEnabled(True)
        self.actionLogin_Refresh.setObjectName("actionLogin_Refresh")
        self.actionQuit = QtWidgets.QAction(Browser)
        self.actionQuit.setObjectName("actionQuit")
        self.actionInfo = QtWidgets.QAction(Browser)
        self.actionInfo.setEnabled(True)
        self.actionInfo.setObjectName("actionInfo")
        self.actionLogout = QtWidgets.QAction(Browser)
        self.actionLogout.setObjectName("actionLogout")
        self.actionAbout = QtWidgets.QAction(Browser)
        self.actionAbout.setObjectName("actionAbout")
        self.actionReload_Stylesheet = QtWidgets.QAction(Browser)
        self.actionReload_Stylesheet.setObjectName("actionReload_Stylesheet")
        self.actionAdd_Server = QtWidgets.QAction(Browser)
        self.actionAdd_Server.setObjectName("actionAdd_Server")
        self.actionTrim_Image_Cache = QtWidgets.QAction(Browser)
        self.actionTrim_Image_Cache.setObjectName("actionTrim_Image_Cache")
        self.actionTrim_Thumb_Cache = QtWidgets.QAction(Browser)
        self.actionTrim_Thumb_Cache.setObjectName("actionTrim_Thumb_Cache")
        self.actionRefresh_Devices = QtWidgets.QAction(Browser)
        self.actionRefresh_Devices.setObjectName("actionRefresh_Devices")
        self.actionRefresh_Users = QtWidgets.QAction(Browser)
        self.actionRefresh_Users.setObjectName("actionRefresh_Users")
        self.actionSearch = QtWidgets.QAction(Browser)
        self.actionSearch.setObjectName("actionSearch")
        self.actionFind = QtWidgets.QAction(Browser)
        self.actionFind.setIconVisibleInMenu(False)
        self.actionFind.setObjectName("actionFind")
        self.actionBack = QtWidgets.QAction(Browser)
        self.actionBack.setObjectName("actionBack")
        self.actionRefresh = QtWidgets.QAction(Browser)
        self.actionRefresh.setObjectName("actionRefresh")
        self.actionHome = QtWidgets.QAction(Browser)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.actionHome.setFont(font)
        self.actionHome.setObjectName("actionHome")
        self.actionOn_Deck = QtWidgets.QAction(Browser)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.actionOn_Deck.setFont(font)
        self.actionOn_Deck.setObjectName("actionOn_Deck")
        self.actionRecently_Added = QtWidgets.QAction(Browser)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.actionRecently_Added.setFont(font)
        self.actionRecently_Added.setObjectName("actionRecently_Added")
        self.actionChannels = QtWidgets.QAction(Browser)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.actionChannels.setFont(font)
        self.actionChannels.setObjectName("actionChannels")
        self.actionHubs = QtWidgets.QAction(Browser)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.actionHubs.setFont(font)
        self.actionHubs.setObjectName("actionHubs")
        self.actionMetadata = QtWidgets.QAction(Browser)
        self.actionMetadata.setObjectName("actionMetadata")
        self.actionAdd_Shortcut = QtWidgets.QAction(Browser)
        self.actionAdd_Shortcut.setCheckable(True)
        self.actionAdd_Shortcut.setObjectName("actionAdd_Shortcut")
        self.actionView_Mode = QtWidgets.QAction(Browser)
        self.actionView_Mode.setObjectName("actionView_Mode")
        self.actionDownloads = QtWidgets.QAction(Browser)
        self.actionDownloads.setObjectName("actionDownloads")
        self.actionNew_Browser = QtWidgets.QAction(Browser)
        self.actionNew_Browser.setObjectName("actionNew_Browser")
        self.actionBookmarks_Bar = QtWidgets.QAction(Browser)
        self.actionBookmarks_Bar.setObjectName("actionBookmarks_Bar")
        self.actionNew_Tab = QtWidgets.QAction(Browser)
        self.actionNew_Tab.setObjectName("actionNew_Tab")
        self.actionClose_Tab = QtWidgets.QAction(Browser)
        self.actionClose_Tab.setObjectName("actionClose_Tab")
        self.actionForward = QtWidgets.QAction(Browser)
        self.actionForward.setObjectName("actionForward")
        self.menuFile.addAction(self.actionNew_Browser)
        self.menuFile.addAction(self.actionQuit)
        self.menuFile.addAction(self.actionNew_Tab)
        self.menuFile.addAction(self.actionClose_Tab)
        self.menuEdit.addAction(self.actionFind)
        self.menuEdit.addAction(self.actionPreferences)
        self.menuEdit.addAction(self.actionReload_Stylesheet)
        self.menuRemotes.addSeparator()
        self.menuServers.addSeparator()
        self.menuSession.addAction(self.actionLogin_Refresh)
        self.menuSession.addAction(self.actionInfo)
        self.menuSession.addAction(self.actionLogout)
        self.menuSession.addAction(self.menuServers.menuAction())
        self.menuSession.addAction(self.menuRemotes.menuAction())
        self.menuSession.addAction(self.actionAdd_Server)
        self.menuSession.addAction(self.actionRefresh_Devices)
        self.menuSession.addAction(self.actionRefresh_Users)
        self.menu_Help.addAction(self.actionAbout)
        self.menuWindow.addAction(self.actionDownloads)
        self.menu_View.addAction(self.actionBookmarks_Bar)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menu_View.menuAction())
        self.menubar.addAction(self.menuSession.menuAction())
        self.menubar.addAction(self.menuWindow.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())
        self.navToolBar.addAction(self.actionBack)
        self.navToolBar.addAction(self.actionForward)
        self.navToolBar.addAction(self.actionRefresh)
        self.navToolBar.addAction(self.actionFind)
        self.navToolBar.addAction(self.actionView_Mode)
        self.navToolBar.addAction(self.actionMetadata)
        self.locationToolBar.addAction(self.actionHome)
        self.locationToolBar.addAction(self.actionOn_Deck)
        self.locationToolBar.addAction(self.actionRecently_Added)
        self.locationToolBar.addAction(self.actionChannels)
        self.locationToolBar.addAction(self.actionHubs)
        self.locationToolBar.addAction(self.actionAdd_Shortcut)

        self.retranslateUi(Browser)
        QtCore.QMetaObject.connectSlotsByName(Browser)

    def retranslateUi(self, Browser):
        _translate = QtCore.QCoreApplication.translate
        Browser.setWindowTitle(_translate("Browser", "plexdesktop"))
        self.menuFile.setTitle(_translate("Browser", "&File"))
        self.menuEdit.setTitle(_translate("Browser", "&Edit"))
        self.menuSession.setTitle(_translate("Browser", "&Session"))
        self.menuRemotes.setTitle(_translate("Browser", "Remotes"))
        self.menuServers.setTitle(_translate("Browser", "Servers"))
        self.menu_Help.setTitle(_translate("Browser", "&Help"))
        self.menuWindow.setTitle(_translate("Browser", "Window"))
        self.menu_View.setTitle(_translate("Browser", "&View"))
        self.navToolBar.setWindowTitle(_translate("Browser", "Main Menu"))
        self.locationToolBar.setWindowTitle(_translate("Browser", "Locations"))
        self.hub_dock.setWindowTitle(_translate("Browser", "Hubs"))
        self.bookmarksToolBar.setWindowTitle(_translate("Browser", "toolBar"))
        self.actionPreferences.setText(_translate("Browser", "&Preferences"))
        self.actionPreferences.setShortcut(_translate("Browser", "Ctrl+P"))
        self.actionLogin_Refresh.setText(_translate("Browser", "&Login/Refresh..."))
        self.actionQuit.setText(_translate("Browser", "&Quit"))
        self.actionQuit.setShortcut(_translate("Browser", "Ctrl+Q"))
        self.actionInfo.setText(_translate("Browser", "&Info"))
        self.actionLogout.setText(_translate("Browser", "Log&out"))
        self.actionAbout.setText(_translate("Browser", "&About"))
        self.actionReload_Stylesheet.setText(_translate("Browser", "&Reload Stylesheet"))
        self.actionReload_Stylesheet.setShortcut(_translate("Browser", "F12"))
        self.actionAdd_Server.setText(_translate("Browser", "Add Server..."))
        self.actionTrim_Image_Cache.setText(_translate("Browser", "Trim Image Cache"))
        self.actionTrim_Thumb_Cache.setText(_translate("Browser", "Trim Thumb Cache"))
        self.actionRefresh_Devices.setText(_translate("Browser", "Refresh Devices..."))
        self.actionRefresh_Users.setText(_translate("Browser", "Refresh Users..."))
        self.actionSearch.setText(_translate("Browser", "Search"))
        self.actionFind.setText(_translate("Browser", "Find..."))
        self.actionFind.setShortcut(_translate("Browser", "Ctrl+F"))
        self.actionBack.setText(_translate("Browser", "Back"))
        self.actionRefresh.setText(_translate("Browser", "Refresh"))
        self.actionRefresh.setShortcut(_translate("Browser", "F5"))
        self.actionHome.setText(_translate("Browser", "Home"))
        self.actionOn_Deck.setText(_translate("Browser", "Deck"))
        self.actionOn_Deck.setToolTip(_translate("Browser", "On Deck"))
        self.actionOn_Deck.setShortcut(_translate("Browser", "Shift+D"))
        self.actionRecently_Added.setText(_translate("Browser", "New"))
        self.actionRecently_Added.setShortcut(_translate("Browser", "Shift+R"))
        self.actionChannels.setText(_translate("Browser", "Channels"))
        self.actionChannels.setShortcut(_translate("Browser", "Shift+C"))
        self.actionHubs.setText(_translate("Browser", "Hubs"))
        self.actionHubs.setShortcut(_translate("Browser", "Shift+H"))
        self.actionMetadata.setText(_translate("Browser", "Metadata"))
        self.actionMetadata.setShortcut(_translate("Browser", "Shift+M"))
        self.actionAdd_Shortcut.setText(_translate("Browser", "Add Shortcut"))
        self.actionAdd_Shortcut.setShortcut(_translate("Browser", "Ctrl+D"))
        self.actionView_Mode.setText(_translate("Browser", "View Mode"))
        self.actionView_Mode.setShortcut(_translate("Browser", "`"))
        self.actionDownloads.setText(_translate("Browser", "&Downloads"))
        self.actionDownloads.setShortcut(_translate("Browser", "Ctrl+J"))
        self.actionNew_Browser.setText(_translate("Browser", "New &Browser"))
        self.actionNew_Browser.setShortcut(_translate("Browser", "Ctrl+N"))
        self.actionBookmarks_Bar.setText(_translate("Browser", "Bookmarks Bar"))
        self.actionBookmarks_Bar.setShortcut(_translate("Browser", "Ctrl+Shift+B"))
        self.actionNew_Tab.setText(_translate("Browser", "New Tab"))
        self.actionNew_Tab.setShortcut(_translate("Browser", "Ctrl+T"))
        self.actionClose_Tab.setText(_translate("Browser", "Close Tab"))
        self.actionClose_Tab.setShortcut(_translate("Browser", "Ctrl+W"))
        self.actionForward.setText(_translate("Browser", "Forward"))

from plexdesktop.browserlist import BrowserTabs
from plexdesktop.extra_widgets import HubSearch
from plexdesktop.hubtree import TreeView
