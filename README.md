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
pip install PyQt5
pip install plexdevices
pip install git+https://github.com/coryo/python-mpv
python main.py
```

##### Build
```
pip install cx_Freeze
python setup.py build
```


Ubuntu 16.04
============

##### Build libmpv
```
sudo apt install git devscripts equivs
git clone https://github.com/mpv-player/mpv-build.git
cd mpv-build
mk-build-deps -s sudo -i
echo --enable-libmpv-shared > mpv_options
./rebuild -j4
sudo ./install
```

##### Run
```
sudo apt install python3-pip
pip3 install PyQt5
pip3 install plexdevices
pip3 install git+https://github.com/coryo/python-mpv

python3 main.py
```


OSX
===

  * [Python 3](https://www.python.org/downloads/mac-osx)
  * libmpv is available through [Homebrew](http://brew.sh).

```
brew install mpv --with-shared

pip3 install PyQt5
pip3 install plexdevices
pip3 install git+https://github.com/coryo/python-mpv

python3 main.py
```
