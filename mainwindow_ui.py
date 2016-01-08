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
        MainWindow.resize(463, 212)
        self.centralWidget = QtWidgets.QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralWidget)
        self.gridLayout_2.setContentsMargins(11, 11, 11, 11)
        self.gridLayout_2.setSpacing(6)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.btn_login = QtWidgets.QPushButton(self.centralWidget)
        self.btn_login.setObjectName("btn_login")
        self.gridLayout_2.addWidget(self.btn_login, 0, 2, 1, 1)
        self.user = QtWidgets.QLineEdit(self.centralWidget)
        self.user.setObjectName("user")
        self.gridLayout_2.addWidget(self.user, 0, 0, 1, 1)
        self.btn_launch = QtWidgets.QPushButton(self.centralWidget)
        self.btn_launch.setEnabled(False)
        self.btn_launch.setObjectName("btn_launch")
        self.gridLayout_2.addWidget(self.btn_launch, 3, 2, 1, 1)
        self.players = QtWidgets.QComboBox(self.centralWidget)
        self.players.setObjectName("players")
        self.gridLayout_2.addWidget(self.players, 3, 0, 1, 2)
        self.password = QtWidgets.QLineEdit(self.centralWidget)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setObjectName("password")
        self.gridLayout_2.addWidget(self.password, 0, 1, 1, 1)
        self.servers = QtWidgets.QComboBox(self.centralWidget)
        self.servers.setObjectName("servers")
        self.gridLayout_2.addWidget(self.servers, 4, 0, 1, 2)
        self.btn_browser = QtWidgets.QPushButton(self.centralWidget)
        self.btn_browser.setEnabled(False)
        self.btn_browser.setObjectName("btn_browser")
        self.gridLayout_2.addWidget(self.btn_browser, 4, 2, 1, 1)
        MainWindow.setCentralWidget(self.centralWidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "DesktopClient for Plex"))
        self.btn_login.setText(_translate("MainWindow", "Login"))
        self.user.setPlaceholderText(_translate("MainWindow", "username"))
        self.btn_launch.setText(_translate("MainWindow", "Remote"))
        self.password.setPlaceholderText(_translate("MainWindow", "password"))
        self.btn_browser.setText(_translate("MainWindow", "Browser"))

