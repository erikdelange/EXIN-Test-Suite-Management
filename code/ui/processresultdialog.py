"""" Dialog to show process results.

Used to display process results (stdout, stderr, resultcode) from
running a script alongside the expected results. Update content by
calling slot showResult. Read-only dialog.
"""
import os

from PyQt5.QtCore import QEvent, QSettings, Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QWidget

import config
import ui


class ProcessResultDialog(QDialog):
    """" Dialog to display process results. """

    def __init__(self, parent: QWidget = None, testresult: config.TestResult = None):
        super().__init__(parent)

        ui.loadUi(__file__, self)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Actual Results")

        self.load_window_geometry()

        if testresult:
            self.set_fields(testresult)

    def closeEvent(self, event: QEvent):
        """" Event triggered at window close. """
        self.save_window_geometry()

        super().closeEvent(event)

    def load_window_geometry(self):
        """ Load previous window size and position from settings. """
        geometry = QSettings().value(self.__class__.__name__ + "/geometry")
        if geometry:
            self.setGeometry(geometry)

        splitter = QSettings().value(self.__class__.__name__ + "/splitter")
        if splitter:
            self.splitter.restoreState(splitter)

    def save_window_geometry(self):
        """ Store current window size and position to settings. """
        QSettings().setValue(self.__class__.__name__ + "/geometry", self.geometry())
        QSettings().setValue(self.__class__.__name__ + "/splitter", self.splitter.saveState())

    def set_fields(self, testresult: config.TestResult):
        """" Populate dialog fields from testresult. """
        self.lineScriptName.setText(os.path.relpath(testresult.script, config.scriptroot))
        self.textStdout.document().setPlainText(testresult.processresult.stdout)
        self.textStderr.document().setPlainText(testresult.processresult.stderr)
        self.lineReturnCode.setText(testresult.processresult.returncode)

    # ---- Slots ----

    @pyqtSlot(config.TestResult)
    def showResult(self, testresult: config.TestResult):
        """ Slot for changing content of dialog to testresult. """
        self.set_fields(testresult)
