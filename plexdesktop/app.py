import os
import sys
import logging
import pickle
from logging.config import dictConfig
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile
from plexdesktop.browser import Browser
import plexdevices
import plexdesktop.ui.resources_rc


def run():
    # for cx_Freeze and requests ssl issues
    os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(os.getcwd(), "cacert.pem")
    # mpv on ubuntu
    os.environ["LC_NUMERIC"] = "C"
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
    logger.info("Application Started")
    app = QApplication(sys.argv)
    file = QFile(':/resources/plexdesktop.qss')
    file.open(QFile.ReadOnly)
    ss = bytes(file.readAll()).decode('latin-1')
    app.setStyleSheet(ss)
    form = Browser()
    form.show()
    sys.exit(app.exec_())
