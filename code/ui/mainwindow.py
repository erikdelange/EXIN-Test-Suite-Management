""" Main dialog.

File explorer like view on the test script root directory and its
sub-directories. Allows creation of new sub-directories and new test
scripts. Run tests by selecting one or more and opening the context
menu. A table with test results is displayed in a separate pane which
is normally collapsed. A double click on a test result opens both the
script and result dialogs. Once these are open their content is
changed by a single click on a row in the results table.
"""
import logging
import os
from typing import List

from PyQt5.QtCore import QEvent, QModelIndex, QPoint, QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QFileDialog, QFileSystemModel, QInputDialog, QMainWindow, QMenu, \
    QMessageBox, QTableWidgetItem, QWidget

import config
import runner
import ui
from config import TestResultList, TestStatus

QModelIndexList = List[QModelIndex]


class MainWindow(QMainWindow):
    showScript = pyqtSignal(str)
    newScript = pyqtSignal(str)
    showResult = pyqtSignal(config.TestResult)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        ui.loadUi(__file__, self)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(QApplication.applicationName())

        self.load_window_geometry()

        self.testresults = []
        self.scriptDialog = None  # script dialog (if opened)
        self.resultDialog = None  # result dialog (if opened)

        # Get interpreter from settings and if not set then select one
        config.interpreter = QSettings().value("interpreter", None)
        if config.interpreter is None:
            self.on_actionSet_Interpreter_triggered()
        logging.info("interpreter is {}".format(config.interpreter))

        # Setup the directory tree view and model
        self.view = self.treeView  # QTreeView
        self.model = QFileSystemModel()
        self.view.setModel(self.model)
        self.model.rootPathChanged.connect(self.on_QFileSystemModel_rootPathChanged)
        self.model.setNameFilters(["*{}".format(config.extension)])
        self.model.setNameFilterDisables(False)
        self.view.setRootIndex(self.model.index(config.scriptroot))
        self.view.hideColumn(1)  # filesize
        self.view.hideColumn(2)  # type
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(1, Qt.AscendingOrder)  # name
        self.view.setColumnWidth(0, 200)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)

        # Setup the results table
        self.table = self.tableTestResult  # QTableWidget
        self.table.hideColumn(3)  # column 3 is index into self.testresults
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        sizes = self.splitter.sizes()
        self.splitter.setSizes([sizes[0] + sizes[1], 0])  # collapse right panel (= results)

        # Get test script root directory from settings and if not set select one
        config.scriptroot = QSettings().value("scriptroot", None)
        if config.scriptroot is None:
            self.on_actionSet_Root_Directory_triggered()
        else:
            self.model.setRootPath(config.scriptroot)
        logging.info("script root directory is {}".format(config.scriptroot))

    def closeEvent(self, event: QEvent):
        """" Event triggered at window close. """
        if self.resultDialog:  # close child window(s) (if any)
            self.resultDialog.close()

        if self.scriptDialog:
            self.scriptDialog.close()

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
        """ Save current window size and position to settings. """
        QSettings().setValue(self.__class__.__name__ + "/geometry", self.geometry())
        QSettings().setValue(self.__class__.__name__ + "/splitter", self.splitter.saveState())

    # ---- Menubar events ----

    @pyqtSlot()
    def on_actionQuit_triggered(self):
        """ Main menu 'File/Quit' action. """
        self.close()

    @pyqtSlot()
    def on_actionSet_Interpreter_triggered(self):
        """ Main menu 'Settings/Set Interpreter' action. """
        interpreter, _ = QFileDialog.getOpenFileName(self, "Select Interpreter", config.interpreter,
                                                     "Executables (*.exe)")
        if interpreter:
            if os.path.isfile(interpreter):
                config.interpreter = os.path.normpath(interpreter)
                QSettings().setValue("interpreter", config.interpreter)
                logging.info("interpreter set to {}".format(config.interpreter))

    @pyqtSlot()
    def on_actionSet_Root_Directory_triggered(self):
        """ Main menu 'Settings/Set Root Directory' action. """
        scriptroot = QFileDialog.getExistingDirectory(self, "Select Script Root Directory", config.scriptroot)
        if scriptroot:
            if os.path.isdir(scriptroot):
                config.scriptroot = os.path.normpath(scriptroot)
                QSettings().setValue("scriptroot", config.scriptroot)
                logging.info("script root directory set to {}".format(config.scriptroot))
                self.model.setRootPath(config.scriptroot)

    # ---- Button events ----

    @pyqtSlot()
    def on_buttonUp_clicked(self):
        """ Up (directory) button. """
        try:
            if not os.path.samefile(self.model.rootPath(), config.scriptroot):  # in scriptroot directory already?
                self.model.setRootPath(os.path.split(self.model.rootPath())[0])
        except FileNotFoundError:
            pass

    @pyqtSlot()
    def on_buttonHome_clicked(self):
        """ Home (directory) button. """
        self.model.setRootPath(config.scriptroot)

    # ---- file explorer Treeview events ----

    @pyqtSlot(QModelIndex)
    def on_treeView_clicked(self, index: QModelIndex):
        """ If the script dialog is open then show the selected script. """
        if self.model.fileInfo(index).isFile() is True:
            if self.scriptDialog:
                self.showScript.emit(self.model.filePath(index))

    @pyqtSlot(QModelIndex)
    def on_treeView_doubleClicked(self, index: QModelIndex):
        """ Step into a directory, or open the script dialog if it was not yet open. """
        if self.model.fileInfo(index).isDir():
            newpath = os.path.join(self.model.rootPath(), self.model.fileName(index))
            self.model.setRootPath(newpath)
        elif self.model.fileInfo(index).isFile():
            if self.scriptDialog is None:
                self.scriptDialog = ui.ScriptDialog(script=self.model.filePath(index))
                self.showScript.connect(self.scriptDialog.showScript)
                self.newScript.connect(self.scriptDialog.newScript)
                self.scriptDialog.destroyed.connect(self.on_scriptDialogDestroyed)
                self.scriptDialog.show()

    @pyqtSlot(QPoint)
    def on_treeView_customContextMenuRequested(self, point: QPoint):
        TEST = "Test"
        DELETE = "Delete"
        NEWFOLDER = "New Folder"
        NEWFILE = "New File"

        menu = QMenu(self)
        index = self.view.indexAt(point)
        if index.isValid():  # click on row in tree
            menu.addAction(TEST)
            menu.addAction(DELETE)
        else:  # click in empty space
            menu.addAction(NEWFOLDER)
            menu.addAction(NEWFILE)

        action = menu.exec_(self.view.viewport().mapToGlobal(point))

        if action is not None:
            if action.text() == TEST:
                self.on_treeView_actionTest(self.view.selectionModel().selectedRows())
            elif action.text() == DELETE:
                self.on_treeView_actionDelete(self.view.selectionModel().selectedRows())
            elif action.text() == NEWFOLDER:
                self.on_treeView_actionNewFolder()
            elif action.text() == NEWFILE:
                self.on_treeView_actionNewFile()

    def on_treeView_actionTest(self, selectedrows: QModelIndexList):
        """ Run test for the selected rows, visit sub-directories recursively. """
        self.statusbar.showMessage("Busy executing tests ...")
        QApplication.processEvents()  # else statusbar is only updated at end of function
        self.testresults = []
        for index in selectedrows:
            result = runner.run_test(self.model.filePath(index))
            for item in result:
                self.testresults.append(item)

        if self.resultDialog:
            self.resultDialog.close()

        self.table.model().removeRows(0, self.table.rowCount())
        self.set_fields(self.testresults)
        self.table.resizeColumnsToContents()
        fail_count = sum(record.status == TestStatus.FAIL for record in self.testresults)
        self.statusbar.showMessage("{} tests executed, {} failed".format(len(self.testresults), fail_count))

        # show results pane if it was collapsed
        sizes = self.splitter.sizes()
        if sizes[1] == 0:
            self.splitter.setSizes([sizes[0] / 2, sizes[0] / 2])  # divide space 50 / 50

    def on_treeView_actionDelete(self, selectedrows: QModelIndexList):
        """ Delete selected files and/or directories. """
        for index in selectedrows:
            if self.model.fileInfo(index).isDir() is True:
                if not self.model.rmdir(index):
                    QMessageBox.warning(self, "Error", "Failed to delete folder")
            elif self.model.fileInfo(index).isFile() is True:
                if not self.model.remove(index):
                    QMessageBox.warning(self, "Error", "Failed to delete file")

    def on_treeView_actionNewFolder(self):
        """" Create a new folder. """
        name, ok = QInputDialog.getText(self, "New Folder", "Name")
        if ok and len(name) > 0:
            index = self.model.index(self.model.rootPath())
            self.model.mkdir(index, name)

    def on_treeView_actionNewFile(self):
        """ Open an empty script dialog, or clear it is already open. """
        if self.scriptDialog is None:
            self.scriptDialog = ui.ScriptDialog(self, folder=self.model.rootPath())
            self.showScript.connect(self.scriptDialog.showScript)
            self.newScript.connect(self.scriptDialog.newScript)
            self.scriptDialog.destroyed.connect(self.on_scriptDialogDestroyed)
            self.scriptDialog.show()
        else:
            self.newScript.emit(self.model.rootPath())

    @pyqtSlot(str)
    def on_QFileSystemModel_rootPathChanged(self, newpath: str = ""):
        """ Slot for rootPathChanged signal from QFileSystemModel. Update view and UI. """
        self.view.setRootIndex(self.model.index(newpath))
        self.linePath.setText(newpath)

    # ---- results QTableWidget events and functions ----

    def set_fields(self, testresults: TestResultList):
        """ Append all rows from list testresults to tableTestResult (QTableWidget).

        The index into testresults is also copied, but its column (#3) has been hidden. In
        this way even when sorting the results table in the widget the link to the
        testresults list is maintained.
        """
        for i, item in enumerate(testresults):
            row = [os.path.relpath(item.script, config.scriptroot), item.status, item.processresult.exception, str(i)]
            index = self.table.rowCount()
            self.table.insertRow(index)
            for j, field in enumerate(row):
                item = QTableWidgetItem(field)
                self.table.setItem(index, j, item)

    @pyqtSlot(QModelIndex)
    def on_tableTestResult_clicked(self, index: QModelIndex):
        """ If script- and/or detailDialog is open refresh their content from the selected row. """
        row = index.row()
        if self.table.item(row, 1).text() in [TestStatus.PASS, TestStatus.FAIL]:
            idx = int(self.table.item(row, 3).text())
            if self.resultDialog is not None:
                self.showResult.emit(self.testresults[idx])
            if self.scriptDialog is not None:
                self.showScript.emit(self.testresults[idx].script)

    @pyqtSlot(QModelIndex)
    def on_tableTestResult_doubleClicked(self, index: QModelIndex):
        """ Open the script- and detailDialog if they were not open, and populate fields from selected row. """
        row = index.row()
        idx = int(self.table.item(row, 3).text())
        if self.table.item(row, 1).text() in [TestStatus.PASS, TestStatus.FAIL]:
            if self.resultDialog is None:
                self.resultDialog = ui.ProcessResultDialog(testresult=self.testresults[idx])
                self.showResult.connect(self.resultDialog.showResult)
                self.resultDialog.destroyed.connect(self.on_resultDialogDestroyed)
                self.resultDialog.show()
            if self.scriptDialog is None:
                self.scriptDialog = ui.ScriptDialog(script=self.testresults[idx].script)
                self.showScript.connect(self.scriptDialog.showScript)
                self.scriptDialog.destroyed.connect(self.on_scriptDialogDestroyed)
                self.scriptDialog.show()
        else:
            windowtitle = "Exception for {}".format(os.path.relpath(self.testresults[idx].script, config.scriptroot))
            box = QMessageBox(QMessageBox.Warning, windowtitle, "", QMessageBox.Ok)
            box.setText(self.testresults[idx].processresult.exception)
            box.setInformativeText(str(self.testresults[idx].processresult.exceptiondetail))
            box.exec_()

    @pyqtSlot(QPoint)
    def on_tableTestResult_customContextMenuRequested(self, point: QPoint):
        CLEAR = "Clear"
        HIDE = "Hide"

        menu = QMenu(self)
        menu.addAction(CLEAR)
        menu.addAction(HIDE)

        action = menu.exec_(self.table.viewport().mapToGlobal(point))

        if action is not None:
            if action.text() == CLEAR:
                self.table.model().removeRows(0, self.table.rowCount())
                self.table.resizeColumnsToContents()
                self.statusbar.clearMessage()
            elif action.text() == HIDE:
                sizes = self.splitter.sizes()
                self.splitter.setSizes([sizes[0] + sizes[1], 0])  # collapse right panel

    # ---- Other events ----

    @pyqtSlot()
    def on_scriptDialogDestroyed(self):
        """ Slot for destroyed signal from scriptDialog. """
        self.scriptDialog = None

    @pyqtSlot()
    def on_resultDialogDestroyed(self):
        """ Slot for destroyed signal from resultlDialog. """
        self.resultDialog = None
