import sys
from cx_Freeze import setup, Executable
import requests.certs

NAME = 'plexdesktop'
VERSION = '0.0.3'
DESCRIPTION = 'Plex Desktop Client'
EXE = NAME

base = None

if sys.platform == "win32":
    base = "Win32GUI"
    EXE += '.exe'

options = {
    'build_exe': {
        "include_files": [
            (requests.certs.where(), 'cacert.pem'),
            ('mpv', 'mpv'),
            ('plexdesktop.qss', 'plexdesktop.qss')
        ],
        'optimize': 2
    }
}

executables = [
    Executable('main.py', base=base, targetName=EXE)
]

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    options=options,
    executables=executables
)
