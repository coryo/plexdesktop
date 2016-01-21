import os
import sys
import logging
from logging.config import dictConfig
from PyQt5.QtWidgets import QApplication
from settings import Settings
from mainwindow import PlexApp
import plexdevices

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
            'backupCount': 0,
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
            'level': logging.INFO
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
logger.handlers[0].doRollover()


def main():
    logger.info("Application Started")
    app = QApplication(sys.argv)
    with open('plexdesktop.qss', 'r') as stylesheet:
        app.setStyleSheet(stylesheet.read())
    settings = Settings()
    settings.set_defaults()
    del settings
    form = PlexApp()
    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
