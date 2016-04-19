from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtCore import QFile


class About(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setWindowTitle('About')
        self.setOpenExternalLinks(True)
        file = QFile(':/resources/about.html')
        file.open(QFile.ReadOnly)
        html = bytes(file.readAll()).decode('utf-8')
        self.insertHtml(html)
