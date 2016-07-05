# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'plexdesktop\ui\login.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Login(object):
    def setupUi(self, Login):
        Login.setObjectName("Login")
        Login.resize(234, 101)
        self.verticalLayout = QtWidgets.QVBoxLayout(Login)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setObjectName("formLayout_2")
        self.username = QtWidgets.QLineEdit(Login)
        self.username.setObjectName("username")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.username)
        self.password = QtWidgets.QLineEdit(Login)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setObjectName("password")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.password)
        self.label = QtWidgets.QLabel(Login)
        self.label.setObjectName("label")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label)
        self.label_2 = QtWidgets.QLabel(Login)
        self.label_2.setObjectName("label_2")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(Login)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.buttonBox)
        self.verticalLayout.addLayout(self.formLayout_2)

        self.retranslateUi(Login)
        self.buttonBox.accepted.connect(Login.accept)
        self.buttonBox.rejected.connect(Login.reject)
        QtCore.QMetaObject.connectSlotsByName(Login)

    def retranslateUi(self, Login):
        _translate = QtCore.QCoreApplication.translate
        Login.setWindowTitle(_translate("Login", "Plex.tv Login"))
        self.label.setText(_translate("Login", "Username:"))
        self.label_2.setText(_translate("Login", "Password:"))

