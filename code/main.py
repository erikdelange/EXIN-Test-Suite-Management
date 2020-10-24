import logging
import os

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

import config
import ui

if __name__ == "__main__":
    import sys

    if getattr(sys, "frozen", False):
        config.appdir = os.path.normpath(os.path.dirname(sys.executable))
    else:
        config.appdir = os.path.normpath(os.path.dirname(__file__))

    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    app.setApplicationName("Testing")
    app.setOrganizationName("ErikDeLange")

    QSettings.setDefaultFormat(QSettings.IniFormat)

    logging.info("application directory is {}".format(config.appdir))
    logging.info("reading QSettings from {}".format(os.path.normpath(QSettings().fileName())))

    window = ui.MainWindow()
    window.show()
    app.exec_()
