# plexdesktop
a basic plex client using [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5), [libmpv](https://mpv.io), [python-mpv](https://github.com/coryo/python-mpv).

![img](http://i.imgur.com/aKYFTZH.png)
![img](http://i.imgur.com/fL7AIhA.png)

Dependencies
------------

 * python 3.5
 * [libmpv](https://mpv.io/installation)
 * [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
 * [plexdevices](https://github.com/coryo/plexdevices)
 * [python-mpv](https://github.com/coryo/python-mpv)


Windows
=======

[libmpv builds](https://mpv.srsfckn.biz)

##### Run
```
pip install pyqt5
pip install plexdevices
pip install git+https://github.com/coryo/python-mpv
python main.py
```

##### Build
```
pip install cx_Freeze
python setup.py build
```


Ubuntu 15.10
============

```
sudo apt-get install python3-pyqt5
sudo apt-get install libmpv1

pip3 install plexdevices
pip3 install git+https://github.com/coryo/python-mpv

python3 main.py
```


OSX
===

libmpv is available through [Homebrew](http://brew.sh).

```
brew install python3
pip3 install pyqt5

brew tap mpv-player/mpv
brew install mpv --with-shared

pip3 install plexdevices
pip3 install git+https://github.com/coryo/python-mpv

python3 main.py
```
