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

import PyQt5.QtCore
import PyQt5.QtWidgets


class About(PyQt5.QtWidgets.QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setWindowTitle('About')
        self.setOpenExternalLinks(True)
        file = PyQt5.QtCore.QFile('resources/about.html')
        file.open(PyQt5.QtCore.QFile.ReadOnly)
        html = bytes(file.readAll()).decode('utf-8')
        self.insertHtml(html)
