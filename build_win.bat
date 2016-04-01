CALL "C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\vcvarsall.bat" amd64_x86
rmdir /S /Q build
pyqtdeploycli --project plexdesktop-win.pdy build
cd build
qmake
nmake
del release\*.obj
del release\*.cpp
del release\*.exp
del release\*.lib
cd ..
mkdir build\release\resources
xcopy resources build\release\resources
xcopy mpv-1.dll build\release