@ECHO off
SET PYRCC=C:\Python35\Lib\site-packages\PyQt5\pyrcc5

CALL %PYRCC% -o plexdesktop\ui\resources_rc.py plexdesktop\resources.qrc
