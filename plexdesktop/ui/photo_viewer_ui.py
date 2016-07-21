# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'plexdesktop\ui\photo_viewer.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_PhotoViewer(object):
    def setupUi(self, PhotoViewer):
        PhotoViewer.setObjectName("PhotoViewer")
        PhotoViewer.resize(473, 414)
        self.centralwidget = QtWidgets.QWidget(PhotoViewer)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.view = GraphicsView(self.centralwidget)
        self.view.setInteractive(False)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.SmoothPixmapTransform|QtGui.QPainter.TextAntialiasing)
        self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.view.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.view.setObjectName("view")
        self.verticalLayout.addWidget(self.view)
        PhotoViewer.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(PhotoViewer)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 473, 21))
        self.menubar.setObjectName("menubar")
        PhotoViewer.setMenuBar(self.menubar)
        self.toolBar = QtWidgets.QToolBar(PhotoViewer)
        self.toolBar.setObjectName("toolBar")
        PhotoViewer.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionBack = QtWidgets.QAction(PhotoViewer)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/light/glyphicons-chevron-left.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionBack.setIcon(icon)
        self.actionBack.setObjectName("actionBack")
        self.actionForward = QtWidgets.QAction(PhotoViewer)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/images/light/glyphicons-chevron-right.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionForward.setIcon(icon1)
        self.actionForward.setObjectName("actionForward")
        self.actionRotateLeft = QtWidgets.QAction(PhotoViewer)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/images/light/glyphicons-rotate-left.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRotateLeft.setIcon(icon2)
        self.actionRotateLeft.setObjectName("actionRotateLeft")
        self.actionRotateRight = QtWidgets.QAction(PhotoViewer)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/images/light/glyphicons-rotate-right.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRotateRight.setIcon(icon3)
        self.actionRotateRight.setObjectName("actionRotateRight")
        self.actionRefresh = QtWidgets.QAction(PhotoViewer)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/images/light/glyphicons-refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRefresh.setIcon(icon4)
        self.actionRefresh.setObjectName("actionRefresh")
        self.toolBar.addAction(self.actionBack)
        self.toolBar.addAction(self.actionForward)
        self.toolBar.addAction(self.actionRotateLeft)
        self.toolBar.addAction(self.actionRotateRight)
        self.toolBar.addAction(self.actionRefresh)

        self.retranslateUi(PhotoViewer)
        QtCore.QMetaObject.connectSlotsByName(PhotoViewer)

    def retranslateUi(self, PhotoViewer):
        _translate = QtCore.QCoreApplication.translate
        PhotoViewer.setWindowTitle(_translate("PhotoViewer", "Photo Viewer"))
        self.toolBar.setWindowTitle(_translate("PhotoViewer", "toolBar"))
        self.actionBack.setText(_translate("PhotoViewer", "Back"))
        self.actionForward.setText(_translate("PhotoViewer", "Forward"))
        self.actionRotateLeft.setText(_translate("PhotoViewer", "RotateLeft"))
        self.actionRotateRight.setText(_translate("PhotoViewer", "RotateRight"))
        self.actionRefresh.setText(_translate("PhotoViewer", "Refresh"))

from plexdesktop.extra_widgets import GraphicsView
