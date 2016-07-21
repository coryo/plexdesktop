# plexdesktop
# Copyright (c) 2016 Cory Parsons <parsons.cory@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
os.environ['LC_NUMERIC'] = 'C'
import sys
import logging
import logging.config

import PyQt5.QtWidgets
import PyQt5.QtGui

import plexdesktop.ui
import plexdesktop.browser
import plexdesktop.style
import plexdesktop.settings
import plexdesktop.extra_widgets
import plexdesktop.sqlcache
import plexdesktop.components


def run(log_level=logging.INFO):
    # for cx_Freeze and requests ssl issues
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.getcwd(), 'cacert.pem')

    # Logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'f': {
                'format': '%(asctime)s %(name)-20s %(levelname)-8s %(message)s'
            }
        },
        'handlers': {
            'h': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'plexdesktop.log',
                'formatter': 'f',
                'backupCount': 1,
                'level': log_level
            }
        },
        'loggers': {
            'plexdesktop': {
                'handlers': ['h'],
                'level': log_level
            },
            'plexdesktop.mpv': {
                'handlers': ['h'],
                'level': logging.INFO,
                'propagate': False
            },
            'plexdevices.device': {
                'handlers': ['h'],
                'level': log_level,
                'propagate': True
            },
            'plexdevices.session': {
                'handlers': ['h'],
                'level': log_level,
                'propagate': True
            },
            'plexdevices.media': {
                'handlers': ['h'],
                'level': log_level,
                'propagate': True
            },
        }
    }
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('plexdesktop')
    try:
        logger.handlers[0].doRollover()
    except Exception:
        pass
    logger.info('Application Started')
    app = PyQt5.QtWidgets.QApplication(sys.argv)

    s = plexdesktop.settings.Settings()
    plexdesktop.style.Style.Instance().theme(s.value('theme', 'dark'))

    qfd = PyQt5.QtGui.QFontDatabase()
    qfd.addApplicationFont('resources/fonts/OpenSans-Regular.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-Italic.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-Bold.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-BoldItalic.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-ExtraBold.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-Light.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-ExtraBoldItalic.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-Semibold.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-SemiboldItalic.ttf')
    qfd.addApplicationFont('resources/fonts/OpenSans-LightItalic.ttf')

    cm = plexdesktop.components.ComponentManager.Instance()
    cm.create_component(plexdesktop.extra_widgets.DownloadManager, 'download_manager')
    cm.create_browser()

    exit_code = app.exec_()

    plexdesktop.sqlcache.DB_THUMB.commit()

    sys.exit(exit_code)


if __name__ == '__main__':
    run()
