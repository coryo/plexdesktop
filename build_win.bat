SET OLDPATH=%PATH%
CALL "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x86
rmdir /S /Q build
pyqtdeploycli --project plexdesktop-win.pdy build
cd build
qmake
nmake
del release\*.obj
del release\*.cpp
del release\*.exp
del release\*.lib
del release\*.res
cd ..
xcopy cacert.pem build\release
xcopy mpv-1.dll build\release
SET PATH=%OLDPATH%
