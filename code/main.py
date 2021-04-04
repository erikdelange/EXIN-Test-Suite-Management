import logging
import os

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

import config
import ui

if __name__ == "__main__":
    import sys

    logging.basicConfig(format="%(levelname)-8s: %(asctime)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                        level=logging.INFO)

    if getattr(sys, "frozen", False):
        config.appdir = os.path.normpath(os.path.dirname(sys.executable))
    else:
        config.appdir = os.path.normpath(os.path.dirname(__file__))

    logging.info("application directory is {}".format(config.appdir))

    app = QApplication(sys.argv)
    app.setApplicationName("Testing")
    app.setOrganizationName("Erik de Lange")
    app.setOrganizationDomain("https://github.com/erikdelange/EXIN-Test-Suite-Management")

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    logging.info("reading QSettings from {}".format(os.path.normpath(QSettings().fileName())))

    window = ui.MainWindow()
    window.show()
    r = app.exec()

    logging.info("program exit with return code {}".format(r))

    sys.exit(r)
