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
        Browser.resize(473, 459)
        self.gridLayout = QtWidgets.QGridLayout(Browser)
        self.gridLayout.setObjectName("gridLayout")
        self.list = BrowserList(Browser)
        self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list.setObjectName("list")
        self.gridLayout.addWidget(self.list, 10, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_back = QtWidgets.QPushButton(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_back.sizePolicy().hasHeightForWidth())
        self.btn_back.setSizePolicy(sizePolicy)
        self.btn_back.setMaximumSize(QtCore.QSize(50, 16777215))
        self.btn_back.setObjectName("btn_back")
        self.horizontalLayout.addWidget(self.btn_back)
        self.btn_home = QtWidgets.QPushButton(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_home.sizePolicy().hasHeightForWidth())
        self.btn_home.setSizePolicy(sizePolicy)
        self.btn_home.setMaximumSize(QtCore.QSize(50, 16777215))
        self.btn_home.setObjectName("btn_home")
        self.horizontalLayout.addWidget(self.btn_home)
        self.btn_on_deck = QtWidgets.QPushButton(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_on_deck.sizePolicy().hasHeightForWidth())
        self.btn_on_deck.setSizePolicy(sizePolicy)
        self.btn_on_deck.setMaximumSize(QtCore.QSize(50, 16777215))
        self.btn_on_deck.setObjectName("btn_on_deck")
        self.horizontalLayout.addWidget(self.btn_on_deck)
        self.btn_recently_added = QtWidgets.QPushButton(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_recently_added.sizePolicy().hasHeightForWidth())
        self.btn_recently_added.setSizePolicy(sizePolicy)
        self.btn_recently_added.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.btn_recently_added.setObjectName("btn_recently_added")
        self.horizontalLayout.addWidget(self.btn_recently_added)
        self.btn_channels = QtWidgets.QPushButton(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_channels.sizePolicy().hasHeightForWidth())
        self.btn_channels.setSizePolicy(sizePolicy)
        self.btn_channels.setMaximumSize(QtCore.QSize(50, 16777215))
        self.btn_channels.setObjectName("btn_channels")
        self.horizontalLayout.addWidget(self.btn_channels)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.sort = QtWidgets.QComboBox(Browser)
        self.sort.setObjectName("sort")
        self.horizontalLayout.addWidget(self.sort)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem1)
        self.zoom = QtWidgets.QSlider(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.zoom.sizePolicy().hasHeightForWidth())
        self.zoom.setSizePolicy(sizePolicy)
        self.zoom.setMinimum(16)
        self.zoom.setMaximum(256)
        self.zoom.setSliderPosition(32)
        self.zoom.setOrientation(QtCore.Qt.Horizontal)
        self.zoom.setObjectName("zoom")
        self.horizontalLayout_4.addWidget(self.zoom)
        self.gridLayout.addLayout(self.horizontalLayout_4, 13, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lbl_path = QtWidgets.QLabel(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_path.sizePolicy().hasHeightForWidth())
        self.lbl_path.setSizePolicy(sizePolicy)
        self.lbl_path.setText("")
        self.lbl_path.setObjectName("lbl_path")
        self.horizontalLayout_2.addWidget(self.lbl_path)
        self.indicator = QtWidgets.QProgressBar(Browser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.indicator.sizePolicy().hasHeightForWidth())
        self.indicator.setSizePolicy(sizePolicy)
        self.indicator.setMaximumSize(QtCore.QSize(30, 16777215))
        self.indicator.setMaximum(0)
        self.indicator.setProperty("value", -1)
        self.indicator.setTextVisible(False)
        self.indicator.setObjectName("indicator")
        self.horizontalLayout_2.addWidget(self.indicator)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

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
