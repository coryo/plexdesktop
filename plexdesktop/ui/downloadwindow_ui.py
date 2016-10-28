# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'plexdesktop\ui\downloadwindow.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_DownloadWindow(object):
    def setupUi(self, DownloadWindow):
        DownloadWindow.setObjectName("DownloadWindow")
        DownloadWindow.resize(314, 284)
        self.centralwidget = QtWidgets.QWidget(DownloadWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.list = QtWidgets.QScrollArea(self.centralwidget)
        self.list.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.list.setFrameShadow(QtWidgets.QFrame.Plain)
        self.list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.list.setWidgetResizable(True)
        self.list.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.list.setObjectName("list")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 314, 284))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.layout = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.layout.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        self.layout.setObjectName("layout")
        self.list.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.list)
        DownloadWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(DownloadWindow)
        QtCore.QMetaObject.connectSlotsByName(DownloadWindow)

    def retranslateUi(self, DownloadWindow):
        _translate = QtCore.QCoreApplication.translate
        DownloadWindow.setWindowTitle(_translate("DownloadWindow", "MainWindow"))

