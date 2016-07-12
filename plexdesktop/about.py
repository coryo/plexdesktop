import PyQt5.QtCore
import PyQt5.QtWidgets


class About(PyQt5.QtWidgets.QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setWindowTitle('About')
        self.setOpenExternalLinks(True)
        file = PyQt5.QtCore.QFile(':/resources/about.html')
        file.open(PyQt5.QtCore.QFile.ReadOnly)
        html = bytes(file.readAll()).decode('utf-8')
        self.insertHtml(html)
