@ECHO off
SET PYUIC=C:\Python34\Lib\site-packages\PyQt5\pyuic5.bat

CALL %PYUIC% plexdesktop\ui\mainwindow.ui -o plexdesktop\ui\mainwindow_ui.py
CALL %PYUIC% plexdesktop\ui\browser.ui -o plexdesktop\ui\browser_ui.py
CALL %PYUIC% plexdesktop\ui\remote.ui -o plexdesktop\ui\remote_ui.py
CALL %PYUIC% plexdesktop\ui\player.ui -o plexdesktop\ui\player_ui.py
CALL %PYUIC% plexdesktop\ui\photo_viewer.ui -o plexdesktop\ui\photo_viewer_ui.py
CALL %PYUIC% plexdesktop\ui\login.ui -o plexdesktop\ui\login_ui.py
