# plexdesktop
a basic plex client using pyqt5, libmpv, [python-mpv](https://github.com/jaseg/python-mpv).

![img](http://i.imgur.com/tRlcLpX.png)

### Windows:
Dependencies:
 * python 3.4
 * pyqt5
 * [plexdevices](https://github.com/coryo/plexdevices)

##### Run
```
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

git clone https://github.com/coryo/plexdevices.git
cd plexdevices
pip3 install .

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

git clone https://github.com/coryo/plexdevices.git
cd plexdevices
pip3 install .

python3 main.py
```
