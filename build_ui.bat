@ECHO off
CALL pyuic5 mainwindow.ui -o mainwindow_ui.py
CALL pyuic5 browser.ui -o browser_ui.py
CALL pyuic5 remote.ui -o remote_ui.py
CALL pyuic5 player.ui -o player_ui.py