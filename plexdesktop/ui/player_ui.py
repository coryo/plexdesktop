# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'plexdesktop\ui\player.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Player(object):
    def setupUi(self, Player):
        Player.setObjectName("Player")
        Player.resize(530, 62)
        self.verticalLayout = QtWidgets.QVBoxLayout(Player)
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.player_widget = QtWidgets.QWidget(Player)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.player_widget.sizePolicy().hasHeightForWidth())
        self.player_widget.setSizePolicy(sizePolicy)
        self.player_widget.setObjectName("player_widget")
        self.verticalLayout.addWidget(self.player_widget)
        self.control_bar = QtWidgets.QWidget(Player)
        self.control_bar.setObjectName("control_bar")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.control_bar)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(6, 0, 6, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lbl_current_time = QtWidgets.QLabel(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.lbl_current_time.setFont(font)
        self.lbl_current_time.setText("")
        self.lbl_current_time.setObjectName("lbl_current_time")
        self.horizontalLayout_2.addWidget(self.lbl_current_time)
        self.lbl_divider = QtWidgets.QLabel(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.lbl_divider.setFont(font)
        self.lbl_divider.setObjectName("lbl_divider")
        self.horizontalLayout_2.addWidget(self.lbl_divider)
        self.lbl_total_time = QtWidgets.QLabel(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.lbl_total_time.setFont(font)
        self.lbl_total_time.setText("")
        self.lbl_total_time.setObjectName("lbl_total_time")
        self.horizontalLayout_2.addWidget(self.lbl_total_time)
        self.slider_progress = QtWidgets.QSlider(self.control_bar)
        self.slider_progress.setMinimumSize(QtCore.QSize(100, 0))
        self.slider_progress.setOrientation(QtCore.Qt.Horizontal)
        self.slider_progress.setObjectName("slider_progress")
        self.horizontalLayout_2.addWidget(self.slider_progress)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.btn_play = QtWidgets.QPushButton(self.control_bar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_play.sizePolicy().hasHeightForWidth())
        self.btn_play.setSizePolicy(sizePolicy)
        self.btn_play.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(7)
        self.btn_play.setFont(font)
        self.btn_play.setText("")
        self.btn_play.setCheckable(True)
        self.btn_play.setObjectName("btn_play")
        self.horizontalLayout_3.addWidget(self.btn_play)
        self.btn_prev = QtWidgets.QPushButton(self.control_bar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_prev.sizePolicy().hasHeightForWidth())
        self.btn_prev.setSizePolicy(sizePolicy)
        self.btn_prev.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(7)
        self.btn_prev.setFont(font)
        self.btn_prev.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_prev.setText("")
        self.btn_prev.setObjectName("btn_prev")
        self.horizontalLayout_3.addWidget(self.btn_prev)
        self.btn_next = QtWidgets.QPushButton(self.control_bar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_next.sizePolicy().hasHeightForWidth())
        self.btn_next.setSizePolicy(sizePolicy)
        self.btn_next.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(7)
        self.btn_next.setFont(font)
        self.btn_next.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_next.setText("")
        self.btn_next.setObjectName("btn_next")
        self.horizontalLayout_3.addWidget(self.btn_next)
        self.video_tracks = TrackSelector(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.video_tracks.setFont(font)
        self.video_tracks.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.video_tracks.setObjectName("video_tracks")
        self.horizontalLayout_3.addWidget(self.video_tracks)
        self.audio_tracks = TrackSelector(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.audio_tracks.setFont(font)
        self.audio_tracks.setFocusPolicy(QtCore.Qt.NoFocus)
        self.audio_tracks.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.audio_tracks.setObjectName("audio_tracks")
        self.horizontalLayout_3.addWidget(self.audio_tracks)
        self.sub_tracks = TrackSelector(self.control_bar)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.sub_tracks.setFont(font)
        self.sub_tracks.setFocusPolicy(QtCore.Qt.NoFocus)
        self.sub_tracks.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.sub_tracks.setObjectName("sub_tracks")
        self.horizontalLayout_3.addWidget(self.sub_tracks)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
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
        self.horizontalLayout_3.addWidget(self.slider_volume)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout.addWidget(self.control_bar)
        spacerItem1 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)

        self.retranslateUi(Player)
        QtCore.QMetaObject.connectSlotsByName(Player)

    def retranslateUi(self, Player):
        _translate = QtCore.QCoreApplication.translate
        Player.setWindowTitle(_translate("Player", "Form"))
        self.lbl_divider.setText(_translate("Player", "/"))

from plexdesktop.extra_widgets import TrackSelector
