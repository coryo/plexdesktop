import sys
from cx_Freeze import setup, Executable
import requests.certs

base = None
if sys.platform == "win32":
    base = "Win32GUI"

options = {
    'build_exe': {
        "include_files": [
            (requests.certs.where(),'cacert.pem'),
            ('mpv', 'mpv')
        ],
        'optimize': 2
    }
}

executables = [
    Executable('main.py', base=base, targetName='plexdesktop.exe')
]

setup(
    name="plexdesktop",
    version="0.1",
    description="Plex Desktop Client",
    options=options,
    executables=executables
)
