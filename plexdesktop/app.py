import os
os.environ['LC_NUMERIC'] = 'C'
import sys
import logging
import pickle
from logging.config import dictConfig
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QObject
from PyQt5.QtGui import QFontDatabase, QFont
from plexdesktop.browser import Browser
from plexdesktop.player import MPVPlayer
from plexdesktop.photo_viewer import PhotoViewer
from plexdesktop.style import STYLE
from plexdesktop.settings import Settings
import plexdevices
import plexdesktop.ui.resources_rc


def run():
    # for cx_Freeze and requests ssl issues
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.getcwd(), 'cacert.pem')

    # Logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'f': {'format': '%(asctime)s %(name)-20s %(levelname)-8s %(message)s'}
        },
        'handlers': {
            'h': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'plexdesktop.log',
                'formatter': 'f',
                'backupCount': 1,
                'level': logging.DEBUG
            }
        },
        'loggers': {
            'plexdesktop': {
                'handlers': ['h'],
                'level': logging.DEBUG
            },
            'plexdesktop.mpv': {
                'handlers': ['h'],
                'level': logging.INFO,
                'propagate': False
            },
            'plexdevices.device': {
                'handlers': ['h'],
                'level': logging.DEBUG,
                'propagate': True
            },
            'plexdevices.session': {
                'handlers': ['h'],
                'level': logging.DEBUG,
                'propagate': True
            },
            'plexdevices.media': {
                'handlers': ['h'],
                'level': logging.DEBUG,
                'propagate': True
            },
        }
    }
    dictConfig(logging_config)
    logger = logging.getLogger('plexdesktop')
    try:
        logger.handlers[0].doRollover()
    except Exception:
        pass
    logger.info('Application Started')
    app = QApplication(sys.argv)

    s = Settings()
    STYLE.theme(s.value('theme', 'dark'))

    qfd = QFontDatabase()
    qfd.addApplicationFont(':/fonts/OpenSans-Regular.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-Italic.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-Bold.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-BoldItalic.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-ExtraBold.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-Light.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-ExtraBoldItalic.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-Semibold.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-SemiboldItalic.ttf')
    qfd.addApplicationFont(':/fonts/OpenSans-LightItalic.ttf')

    browser = Browser()
    browser.show()

    exit_code = app.exec_()

    import gc
    gc.collect()

    sys.exit(exit_code)
