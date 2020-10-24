""" Script edit and run dialog.

A script consists of one or more code files, where at least one has
the name specified in config.mainfile. Optionally keyboard input can
be recorded in field stdin. When the script is run its output (the
stdout, stderr and program returncode) is displayed. When closing the
dialog, or reloading it with new content the user is asked if the old
content must be saved (but only if the old content has been modified).

If the dialog is open reloading the content is done via two slots,
one to load another script and one to create a new script.
"""
import json
import logging
import os
from typing import Optional

import jsonschema
from PyQt5.Qsci import QsciScintilla
from PyQt5.QtCore import QEvent, QModelIndex, QPoint, QRegExp, QSettings, Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDialog, QInputDialog, QMdiSubWindow, QMenu, QMessageBox, QTabBar, QWidget

import config
import runner
import ui


class ScriptDialog(QDialog):
    """" Script edit and run dialog. """

    regexp = QRegExp("^[\w]+\{}$".format(config.extension))  # rules for valid file name

    def __init__(self, parent: QWidget = None, script: str = None, folder: str = ""):
        super().__init__(parent)

        ui.loadUi(__file__, self)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Edit Script")

        self.load_window_geometry()

        self.script = script
        self.folder = folder

        self.tabBar = self.mdiArea.findChild(QTabBar)
        self.tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabBar.customContextMenuRequested.connect(self.on_tabBar_customContextMenuRequested)

        self.mdiArea.setContextMenuPolicy(Qt.CustomContextMenu)

        if script:
            self.show()  # early show() required for ui manipulation in load_script_from_json() to work
            self.load_script_from_json(script)
        else:
            self.addSubWindow(config.mainfile)

    def closeEvent(self, event: QEvent):
        """" Event triggered at window close. """
        self.save_if_modified()

        self.save_window_geometry()

        super().closeEvent(event)

    def load_window_geometry(self):
        """ Load previous window size and position from settings. """
        geometry = QSettings().value(self.__class__.__name__ + "/geometry")
        if geometry:
            self.setGeometry(geometry)

        splitter = QSettings().value(self.__class__.__name__ + "/splitter_1")
        if splitter:
            self.splitter_1.restoreState(splitter)
        splitter = QSettings().value(self.__class__.__name__ + "/splitter_2")

        if splitter:
            self.splitter_2.restoreState(splitter)
        splitter = QSettings().value(self.__class__.__name__ + "/splitter_3")

        if splitter:
            self.splitter_3.restoreState(splitter)
        splitter = QSettings().value(self.__class__.__name__ + "/splitter_4")

        if splitter:
            self.splitter_4.restoreState(splitter)

    def save_window_geometry(self):
        """ Save current window size and position to settings. """
        QSettings().setValue(self.__class__.__name__ + "/geometry", self.geometry())
        QSettings().setValue(self.__class__.__name__ + "/splitter_1", self.splitter_1.saveState())
        QSettings().setValue(self.__class__.__name__ + "/splitter_2", self.splitter_2.saveState())
        QSettings().setValue(self.__class__.__name__ + "/splitter_3", self.splitter_3.saveState())
        QSettings().setValue(self.__class__.__name__ + "/splitter_4", self.splitter_4.saveState())

    def clear_fields(self):
        """ Clear all dialog fields and reset them to their initial values. """
        self.lineScriptName.setEnabled(True)
        self.lineScriptName.clear()
        self.lineDescription.clear()
        self.textStdin.document().clear()
        self.textStdout.document().clear()
        self.textStderr.document().clear()
        self.lineReturnCode.clear()
        self.set_modified(False)

    def is_modified(self):
        """" Check if any of the dialogs fields has been changed. """
        modified = self.lineDescription.isModified() or \
                   self.textStdin.document().isModified() or \
                   self.textStdout.document().isModified() or \
                   self.textStderr.document().isModified() or \
                   self.lineReturnCode.isModified()

        if not modified:
            for window in self.mdiArea.subWindowList():
                if window.widget().isModified():
                    modified = True
                    break

        return modified

    def set_modified(self, changed: bool):
        """ Set the modified flag of all dialog fields to 'changed'. """
        self.lineDescription.setModified(changed)
        self.textStdin.document().setModified(changed)
        self.textStdout.document().setModified(changed)
        self.textStderr.document().setModified(changed)
        self.lineReturnCode.setModified(changed)

        for window in self.mdiArea.subWindowList():
            window.widget().setModified(changed)

    def save_if_modified(self):
        """ Save script if dialog fields have been modified.

        If the script is new the user is asked what the new filename must be.
        """
        if self.is_modified():
            if QMessageBox.question(self, self.windowTitle(), "Modifications have not been saved. Save modifications?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
                if self.script:
                    self.save_script_to_json(self.script)
                else:  # this is a new script - validate filename
                    name = self.lineScriptName.text().strip()
                    while True:
                        name, ok = QInputDialog.getText(self, "Enter name", "Name", text=name)
                        if ok is False:
                            if QMessageBox.warning(self, "Abort Save", "File will not be saved. Is this OK?",
                                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                                break  # no save
                        name = name.strip()
                        if self.regexp.exactMatch(name) is False:
                            box = QMessageBox(QMessageBox.Warning, "Filename Error", "", QMessageBox.Retry)
                            box.setText("Filename {} is not allowed.".format(name))
                            box.setDetailedText(
                                "Filename must comply to regular expression pattern {}. "
                                "Valid examples are file.json and file_name.json.".format(self.regexp.pattern()))
                            box.exec_()
                        else:
                            if os.path.exists(os.path.join(self.folder, name)):
                                box = QMessageBox(QMessageBox.Warning, "Save Error", "", QMessageBox.Retry)
                                box.setText("Name {} is already in use".format(name))
                                box.exec_()
                            else:
                                self.save_script_to_json(os.path.join(self.folder, name))
                                self.lineScriptName.setEnabled(False)
                                self.lineScriptName.setText(name)
                                break

    def load_script_from_json(self, filename: str = None):
        """ Load the dialog fields from filename. """
        if filename:
            self.clear_fields()
            try:
                with open(filename, "r") as file:
                    data = json.load(file)

                jsonschema.validate(data, config.testschema)  # check if JSON complies to definition
            except (OSError, json.JSONDecodeError, jsonschema.ValidationError, jsonschema.SchemaError) as e:
                logging.error("{} while loading {}: {}".format(type(e).__name__, filename, e))
                box = QMessageBox(QMessageBox.Critical, "Exception", "", QMessageBox.Ok)
                text = "{} while loading {}".format(type(e).__name__, os.path.relpath(filename, config.scriptroot))
                box.setText(text)
                box.setInformativeText(str(e))
                box.exec_()
            else:
                self.lineScriptName.setText(os.path.relpath(filename, config.scriptroot))
                self.lineScriptName.setEnabled(False)
                self.lineDescription.setText(data["description"])
                self.textStdin.document().setPlainText(data["stdin"])
                self.textStdout.document().setPlainText(data["expected"]["stdout"])
                self.textStderr.document().setPlainText(data["expected"]["stderr"])
                self.lineReturnCode.setText(data["expected"]["returncode"])

                for code in data["code"]:
                    self.addSubWindow(code["name"], code["code"])

                self.set_modified(False)

                for i in range(0, self.tabBar.count() - 1):
                    if self.tabBar.tabText(i) == config.mainfile:
                        self.tabBar.setCurrentIndex(i)
                        break

    def save_script_to_json(self, filename: str = None):
        """" Save the dialog fields to file 'filename'. """
        code = []
        for window in self.mdiArea.subWindowList():
            file = {"name": window.windowTitle(), "code": window.widget().text()}
            code.append(file)

        data = {
            "description": self.lineDescription.text().strip(),
            "code": code,
            "stdin": self.textStdin.toPlainText(),
            "expected": {
                "stdout": self.textStdout.toPlainText(),
                "stderr": self.textStderr.toPlainText(),
                "returncode": self.lineReturnCode.text()
            },
        }

        if filename:
            try:
                with open(filename, "w") as file:
                    json.dump(data, file, indent=4)
            except (OSError, OverflowError, ValueError, TypeError) as e:
                logging.error("{} while saving {}: {}".format(type(e).__name__, filename, e))
            else:
                self.set_modified(False)

    # ---- Slots ----

    @pyqtSlot(str)
    def showScript(self, script: str = None):
        """" Replace current script with 'script'. First save current script if modified. """
        if script:
            self.save_if_modified()

            for window in self.mdiArea.subWindowList():
                window.close()

            self.folder = ""
            self.script = script
            self.load_script_from_json(self.script)

    @pyqtSlot(str)
    def newScript(self, folder: str = ""):
        """ Clear all fields. First save current script if modified. """
        self.save_if_modified()

        for window in self.mdiArea.subWindowList():
            window.close()

        self.addSubWindow(config.mainfile)

        self.clear_fields()

        self.folder = folder
        self.script = ""

    # ---- mdiArea and tabBar events

    @pyqtSlot(QPoint)
    def on_mdiArea_customContextMenuRequested(self, point: QPoint):
        """ Context menu when clicking on an empty spot in the mdiArea."""
        NEW = "New"

        menu = QMenu(self)
        menu.addAction(NEW)

        action = menu.exec_(self.mdiArea.viewport().mapToGlobal(point))

        if action is not None:
            if action.text() == NEW:
                self.addSubWindow(config.mainfile)

    @pyqtSlot(QPoint)
    def on_tabBar_customContextMenuRequested(self, point: QPoint):
        """ Context menu when clicking on a tab in the mdiArea. """
        NEW = "New"
        DELETE = "Delete"

        menu = QMenu(self)
        menu.addAction(NEW)
        menu.addAction(DELETE)

        index = self.tabBar.tabAt(point)
        action = menu.exec_(self.mdiArea.viewport().mapToGlobal(point))

        if action is not None:
            if action.text() == NEW:
                self.on_tabBar_actionNew()
            elif action.text() == DELETE:
                self.on_tabBar_actionDelete(index)

    def on_tabBar_actionNew(self):
        """ Create a window for a new file, adding it to the script. """
        while True:
            name, ok = QInputDialog.getText(self, "Enter name of new file", "Filename")
            if ok:
                if self.findSubWindow(name):
                    QMessageBox.warning(self, "New File", "Filename {} is already in use".format(name))
                else:
                    self.addSubWindow(name)
                    break
            else:
                break

    def on_tabBar_actionDelete(self, index: QModelIndex):
        """ Delete a window for a file, removing the file from the script. """
        window = self.findSubWindow(self.tabBar.tabText(index))
        if window:
            if window.windowTitle() == config.mainfile:
                QMessageBox.warning(self, "Delete File", "Main code cannot be deleted")
            else:
                if index == self.tabBar.currentIndex():
                    if self.tabBar.count() > 1:
                        newIndex = index - 1
                        if newIndex < 0:
                            newIndex = self.tabBar.count() - 1
                        self.tabBar.setCurrentIndex(newIndex)
                self.mdiArea.removeSubWindow(window)

                # mark mainfile as modified to force save
                window = self.findSubWindow(config.mainfile)
                window.widget().setModified(True)

    # ---- Button events ----

    @pyqtSlot()
    def on_buttonRun_clicked(self):
        """ Run script button: execute the interpreter for this script. """
        code = []
        for window in self.mdiArea.subWindowList():
            # file = {"name": window.windowTitle(), "code": window.widget().text()}
            file = config.SourceCodeFile(name=window.windowTitle(), code=window.widget().text())
            code.append(file)

        ok, result = runner.run_single_script(code, self.textStdin.toPlainText())

        if ok is True:
            self.textStdout.document().setPlainText(result.stdout)
            self.textStderr.document().setPlainText(result.stderr)
            self.lineReturnCode.setText(result.returncode)
        else:
            box = QMessageBox(QMessageBox.Critical, "Error during execution", "", QMessageBox.Ok)
            box.setText(result.exception)
            box.setInformativeText(result.exceptiondetail)
            box.exec_()

    @pyqtSlot()
    def on_buttonClose_clicked(self):
        """" (Dialog) Close button. """
        self.close()

    # ---- Utility functions ----

    def findSubWindow(self, name: str) -> Optional[QMdiSubWindow]:
        """ Search subwindow by name. """
        for window in self.mdiArea.subWindowList():
            if window.windowTitle() == name:
                return window
        return None

    def addSubWindow(self, name: str, content=None) -> None:
        """ Add a new subwindow to the mdiArea. """
        widget = createQScintillaWidget(self, name)
        if content:
            widget.setText(content)
        subwindow = self.mdiArea.addSubWindow(widget)
        subwindow.showMaximized()


def createQScintillaWidget(parent: QWidget, name: str) -> QsciScintilla:
    """" Create a new initialized QScintilla widget. """
    widget = QsciScintilla(parent)
    widget.setWindowTitle(name)
    setupQScintillaWidget(widget)
    return widget


def setupQScintillaWidget(widget: QsciScintilla) -> None:
    """ Initialize a QsciScintilla widget. """
    widget.setMarginType(0, QsciScintilla.NumberMargin)
    widget.setMarginWidth(0, "0000")
    widget.setMarginsForegroundColor(QColor("#ff888888"))
    widget.setEolMode(QsciScintilla.EolUnix)
    widget.setIndentationsUseTabs(False)
    widget.setTabWidth(4)
    widget.setIndentationGuides(True)
    widget.setAutoIndent(True)
    widget.setTabIndents(True)
