# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'player.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Player(object):
    def setupUi(self, Player):
        Player.setObjectName("Player")
        Player.resize(301, 35)
        self.verticalLayout = QtWidgets.QVBoxLayout(Player)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.player_widget = QtWidgets.QWidget(Player)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.player_widget.sizePolicy().hasHeightForWidth())
        self.player_widget.setSizePolicy(sizePolicy)
        self.player_widget.setObjectName("player_widget")
        self.verticalLayout.addWidget(self.player_widget)
        self.control_bar = QtWidgets.QWidget(Player)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.control_bar.sizePolicy().hasHeightForWidth())
        self.control_bar.setSizePolicy(sizePolicy)
        self.control_bar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.control_bar.setObjectName("control_bar")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.control_bar)
        self.horizontalLayout.setContentsMargins(4, 1, 4, 1)
        self.horizontalLayout.setSpacing(4)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_play = QtWidgets.QPushButton(self.control_bar)
        self.btn_play.setObjectName("btn_play")
        self.horizontalLayout.addWidget(self.btn_play)
        self.slider_progress = QtWidgets.QSlider(self.control_bar)
        self.slider_progress.setMinimumSize(QtCore.QSize(100, 0))
        self.slider_progress.setOrientation(QtCore.Qt.Horizontal)
        self.slider_progress.setObjectName("slider_progress")
        self.horizontalLayout.addWidget(self.slider_progress)
        self.lbl_current_time = QtWidgets.QLabel(self.control_bar)
        self.lbl_current_time.setText("")
        self.lbl_current_time.setObjectName("lbl_current_time")
        self.horizontalLayout.addWidget(self.lbl_current_time)
        self.lbl_divider = QtWidgets.QLabel(self.control_bar)
        self.lbl_divider.setObjectName("lbl_divider")
        self.horizontalLayout.addWidget(self.lbl_divider)
        self.lbl_total_time = QtWidgets.QLabel(self.control_bar)
        self.lbl_total_time.setText("")
        self.lbl_total_time.setObjectName("lbl_total_time")
        self.horizontalLayout.addWidget(self.lbl_total_time)
        self.slider_volume = QtWidgets.QSlider(self.control_bar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slider_volume.sizePolicy().hasHeightForWidth())
        self.slider_volume.setSizePolicy(sizePolicy)
        self.slider_volume.setMaximum(100)
        self.slider_volume.setOrientation(QtCore.Qt.Horizontal)
        self.slider_volume.setInvertedAppearance(False)
        self.slider_volume.setObjectName("slider_volume")
        self.horizontalLayout.addWidget(self.slider_volume)
        self.verticalLayout.addWidget(self.control_bar)

        self.retranslateUi(Player)
        QtCore.QMetaObject.connectSlotsByName(Player)

    def retranslateUi(self, Player):
        _translate = QtCore.QCoreApplication.translate
        Player.setWindowTitle(_translate("Player", "Form"))
        self.btn_play.setText(_translate("Player", "pp"))
        self.lbl_divider.setText(_translate("Player", "/"))

