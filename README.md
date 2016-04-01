# plexdesktop
a basic plex client using [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5), [libmpv](https://mpv.io), [python-mpv](https://github.com/jaseg/python-mpv).

![img](http://i.imgur.com/tRlcLpX.png)

### Windows:
Dependencies:
 * python 3.4
 * [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
 * [plexdevices](https://github.com/coryo/plexdevices)

##### Run
```
pip install plexdevices
python main.py
```

##### Build
```
pip install cx_Freeze
python setup.py build
```

### Ubuntu 15.10:
```
sudo apt-get install python3-pyqt5
sudo apt-get install libmpv1

pip3 install plexdevices

python3 main.py
```

### Mac OS X:
```
brew install python3
brew install pyqt5

mkdir -p /Users/{username}/Library/Python/3.5/lib/python/site-packages
echo 'import site; site.addsitedir("/usr/local/lib/python3.5/site-packages")' >> /Users/{username}/Library/Python/3.5/lib/python/site-packages/homebrew.pth

brew tap mpv-player/mpv
brew install mpv --with-shared

pip3 install plexdevices

python3 main.py
```
