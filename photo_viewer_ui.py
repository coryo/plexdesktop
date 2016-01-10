# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'photo_viewer.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_PhotoViewer(object):
    def setupUi(self, PhotoViewer):
        PhotoViewer.setObjectName("PhotoViewer")
        PhotoViewer.resize(422, 465)
        self.verticalLayout = QtWidgets.QVBoxLayout(PhotoViewer)
        self.verticalLayout.setContentsMargins(0, 2, 0, 0)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalWidget = QtWidgets.QWidget(PhotoViewer)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalWidget.sizePolicy().hasHeightForWidth())
        self.horizontalWidget.setSizePolicy(sizePolicy)
        self.horizontalWidget.setObjectName("horizontalWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalWidget)
        self.horizontalLayout.setContentsMargins(-1, 0, 1, 0)
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_prev = QtWidgets.QPushButton(self.horizontalWidget)
        self.btn_prev.setObjectName("btn_prev")
        self.horizontalLayout.addWidget(self.btn_prev)
        self.btn_next = QtWidgets.QPushButton(self.horizontalWidget)
        self.btn_next.setObjectName("btn_next")
        self.horizontalLayout.addWidget(self.btn_next)
        self.indicator = QtWidgets.QProgressBar(self.horizontalWidget)
        self.indicator.setEnabled(True)
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
        self.horizontalLayout.addWidget(self.indicator)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.horizontalWidget)
        self.verticalWidget = QtWidgets.QWidget(PhotoViewer)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalWidget.sizePolicy().hasHeightForWidth())
        self.verticalWidget.setSizePolicy(sizePolicy)
        self.verticalWidget.setObjectName("verticalWidget")
        self.viewer = QtWidgets.QVBoxLayout(self.verticalWidget)
        self.viewer.setContentsMargins(0, 0, 0, 0)
        self.viewer.setSpacing(0)
        self.viewer.setObjectName("viewer")
        self.verticalLayout.addWidget(self.verticalWidget)

        self.retranslateUi(PhotoViewer)
        QtCore.QMetaObject.connectSlotsByName(PhotoViewer)

    def retranslateUi(self, PhotoViewer):
        _translate = QtCore.QCoreApplication.translate
        PhotoViewer.setWindowTitle(_translate("PhotoViewer", "Form"))
        self.btn_prev.setText(_translate("PhotoViewer", "<"))
        self.btn_next.setText(_translate("PhotoViewer", ">"))

