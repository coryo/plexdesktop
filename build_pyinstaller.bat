@setlocal
PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python35-32\Lib\site-packages\PyQt5\Qt\bin
CALL pyinstaller --onefile --windowed --icon=icon.ico --name=plexdesktop main.py
xcopy resources dist\resources /S /I
xcopy mpv dist\mpv /S /I
xcopy D:\tools\lib\mpv-1.dll dist