# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(280, 143)
        self.centralWidget = QtWidgets.QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralWidget)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setContentsMargins(11, 11, 11, 11)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.btn_browser = QtWidgets.QPushButton(self.centralWidget)
        self.btn_browser.setEnabled(False)
        self.btn_browser.setObjectName("btn_browser")
        self.gridLayout.addWidget(self.btn_browser, 0, 1, 1, 1)
        self.players = QtWidgets.QComboBox(self.centralWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.players.sizePolicy().hasHeightForWidth())
        self.players.setSizePolicy(sizePolicy)
        self.players.setObjectName("players")
        self.gridLayout.addWidget(self.players, 1, 0, 1, 1)
        self.btn_remote = QtWidgets.QPushButton(self.centralWidget)
        self.btn_remote.setEnabled(False)
        self.btn_remote.setObjectName("btn_remote")
        self.gridLayout.addWidget(self.btn_remote, 1, 1, 1, 1)
        self.servers = QtWidgets.QComboBox(self.centralWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.servers.sizePolicy().hasHeightForWidth())
        self.servers.setSizePolicy(sizePolicy)
        self.servers.setObjectName("servers")
        self.gridLayout.addWidget(self.servers, 0, 0, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setContentsMargins(11, 11, 11, 11)
        self.formLayout_2.setSpacing(0)
        self.formLayout_2.setObjectName("formLayout_2")
        self.user = QtWidgets.QLineEdit(self.centralWidget)
        self.user.setObjectName("user")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.user)
        self.password = QtWidgets.QLineEdit(self.centralWidget)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setObjectName("password")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.password)
        self.btn_login = QtWidgets.QPushButton(self.centralWidget)
        self.btn_login.setObjectName("btn_login")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.btn_login)
        self.verticalLayout.addLayout(self.formLayout_2)
        MainWindow.setCentralWidget(self.centralWidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "plexdesktop"))
        self.btn_browser.setText(_translate("MainWindow", "Launch Browser"))
        self.btn_remote.setText(_translate("MainWindow", "Launch Remote"))
        self.user.setPlaceholderText(_translate("MainWindow", "username"))
        self.password.setPlaceholderText(_translate("MainWindow", "password"))
        self.btn_login.setText(_translate("MainWindow", "Login / Refresh"))

