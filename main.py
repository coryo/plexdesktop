import os
import sys
from PyQt5.QtWidgets import QApplication
from settings import Settings
from mainwindow import PlexApp
# for cx_Freeze and requests ssl issues
os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(os.getcwd(), "cacert.pem")
os.environ["LC_NUMERIC"] = "C"
def main():
    app = QApplication(sys.argv)
    settings = Settings()
    settings.set_defaults()
    del settings
    form = PlexApp()
    form.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
