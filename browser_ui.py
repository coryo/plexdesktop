# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'browser.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Browser(object):
    def setupUi(self, Browser):
        Browser.setObjectName("Browser")
        Browser.resize(424, 314)
        self.gridLayout = QtWidgets.QGridLayout(Browser)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_back = QtWidgets.QPushButton(Browser)
        self.btn_back.setObjectName("btn_back")
        self.horizontalLayout.addWidget(self.btn_back)
        self.btn_home = QtWidgets.QPushButton(Browser)
        self.btn_home.setObjectName("btn_home")
        self.horizontalLayout.addWidget(self.btn_home)
        self.btn_on_deck = QtWidgets.QPushButton(Browser)
        self.btn_on_deck.setObjectName("btn_on_deck")
        self.horizontalLayout.addWidget(self.btn_on_deck)
        self.btn_recently_added = QtWidgets.QPushButton(Browser)
        self.btn_recently_added.setObjectName("btn_recently_added")
        self.horizontalLayout.addWidget(self.btn_recently_added)
        self.btn_channels = QtWidgets.QPushButton(Browser)
        self.btn_channels.setObjectName("btn_channels")
        self.horizontalLayout.addWidget(self.btn_channels)
        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)
        self.list = BrowserList(Browser)
        self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list.setObjectName("list")
        self.gridLayout.addWidget(self.list, 4, 0, 1, 1)
        self.zoom = QtWidgets.QSlider(Browser)
        self.zoom.setMinimum(16)
        self.zoom.setMaximum(256)
        self.zoom.setSliderPosition(32)
        self.zoom.setOrientation(QtCore.Qt.Horizontal)
        self.zoom.setObjectName("zoom")
        self.gridLayout.addWidget(self.zoom, 5, 0, 1, 1)
        self.lbl_path = QtWidgets.QLabel(Browser)
        self.lbl_path.setText("")
        self.lbl_path.setObjectName("lbl_path")
        self.gridLayout.addWidget(self.lbl_path, 3, 0, 1, 1)

        self.retranslateUi(Browser)
        QtCore.QMetaObject.connectSlotsByName(Browser)

    def retranslateUi(self, Browser):
        _translate = QtCore.QCoreApplication.translate
        Browser.setWindowTitle(_translate("Browser", "Browser"))
        self.btn_back.setText(_translate("Browser", "back"))
        self.btn_home.setText(_translate("Browser", "home"))
        self.btn_on_deck.setText(_translate("Browser", "on deck"))
        self.btn_recently_added.setText(_translate("Browser", "recently added"))
        self.btn_channels.setText(_translate("Browser", "channels"))

from browserlist import BrowserList
