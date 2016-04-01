import sys
from cx_Freeze import setup, Executable
import requests.certs
from plexdesktop import __version__

NAME = 'plexdesktop'
VERSION = __version__
DESCRIPTION = 'Plex Desktop Client'
EXE = NAME

base = None

if sys.platform == "win32":
    base = "Win32GUI"
    EXE += '.exe'

options = {
    'build_exe': {
        "include_files": [
            (requests.certs.where(), 'resources/cacert.pem'),
            ('mpv-1.dll', 'mpv-1.dll'),
            ('resources/plexdesktop.qss', 'resources/plexdesktop.qss')
        ],
        'optimize': 2
    }
}

executables = [
    Executable('main.py', base=base, targetName=EXE, icon='resources/icon.ico')
]

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    options=options,
    executables=executables
)
