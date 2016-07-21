@ECHO off
SET PYUIC=C:\Python35\Scripts\pyuic5.bat

CALL %PYUIC% plexdesktop\ui\mainwindow.ui -o plexdesktop\ui\mainwindow_ui.py
CALL %PYUIC% plexdesktop\ui\browser.ui -o plexdesktop\ui\browser_ui.py --from-imports
CALL %PYUIC% plexdesktop\ui\remote.ui -o plexdesktop\ui\remote_ui.py
CALL %PYUIC% plexdesktop\ui\player.ui -o plexdesktop\ui\player_ui.py --from-imports
CALL %PYUIC% plexdesktop\ui\photo_viewer.ui -o plexdesktop\ui\photo_viewer_ui.py  --from-imports
CALL %PYUIC% plexdesktop\ui\login.ui -o plexdesktop\ui\login_ui.py
CALL %PYUIC% plexdesktop\ui\downloadwindow.ui -o plexdesktop\ui\downloadwindow_ui.py
