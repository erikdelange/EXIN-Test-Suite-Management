#### EXIN Testing
Test suite management for the EXIN interpreter
##### Summary
EXIN is a home-brewn programming language and an interpreter for it can be found 
[here](https://github.com/erikdelange/EXIN-AST-The-Experimental-Interpreter).
The interpreter is a complex piece of software and adding new features can easily break existing code. By running 
regression tests after each change these bugs are spotted quickly. As the EXIN programming language contains many 
elements which can be combined in multiple ways many tests are needed. This project enables you to record and manage 
these tests and run (parts of) them with just a few mouse clicks. 

Although I use it to test EXIN this solution is universally applicable for testing any separate executable for which 
you can pipe stdin and capture stdout and stderr.

##### Basics
Testing the interpreter is done by having it interpret EXIN code, capturing the output and comparing it with the 
expected output. So when creating a test not only the code must be recorded but also the correct output. 
This output consists of three elements; characters written to the standard output stream (stdout), the standard error 
stream (stderr) and a program return code (always an integer). You don't need to enter this output yourself because when 
developing the test code after a run the output is captured and stored in the testcase.

Testcases are recorded as *.json* files. Each test contains one or more EXIN scripts. At least one of them is called 
*main.x*. By recording multiple scripts in a test the *import* statement can be tested easily. For testing the *input* 
statement you can record characters which are piped to the standard input stream (stdin).

##### User Interface
The main window consists of two panels separated by a vertical splitter. The left child widget contains a file explorer 
like tree view on the directory with the test scripts. The right widget, which is normally collapsed, displays a table 
with test results. After running tests the right widget is automatically made visible. 
Double clicking on a test script in the tree opens the script edit dialog. Single click moves to another script.
Double clicking on a test results opens both the script edit dialog and the process result dialog. Single click here 
moves to another test result.
Context menus (so right click) are used on in the filesystem tree to create new files and folders, and run tests.
In the test results table with a right mouseclick you can clear and collapse the table. 
A right click on the tab-bar with filenames in the script dialog allows you to add or remove files.

![Main Window](/mainwindow.png)
*Main window with test results visible and context menu activated in file tree*

![Script and Result Dialog](/dialog.png)
*Script and detail dialog with context menu activated for tab-bar in script edit dialog*

##### Software Architecture
The program is started by running *main.py* which opens the main window. Every window or dialog is a separate module 
within package *ui*. All global variables and constants are kept in [config.py](/code/config.py). Code to actually run 
the interpreter and capture the output is in [runner.py](/code/runner.py). 

###### Communication between dialogs
The main window communicates with the script- and result dialogs by sending signals to slots in these two dialogs. To 
be able to maintain this link the last two dialogs inform the main window whenever they are destroyed, thus cutting
the link (using the destroyed signal). 

###### JSON Schema
Because a test script contains many different components it is stored as a JSON file. Loading incorrectly formatted 
JSON files can cause a program crash. Therefore the correct layout is described using 
[JSON Schema](https://json-schema.org/), and checked whenever a file is  loaded. The definition for a test 
script can be found in [config.py](/code/config.py).

###### Loading the UI
The user interface is created in Qt Designer and stored as XML code in *.ui* files. There are two ways to render 
the UI. The first one is by compiling the XML code into a Python object using PyQt5's utility *pyuic5*.
However I have chosen to load the ui dynamically (see [loadui.py](/code/ui/loadui.py)). This avoids having to compile 
the *.ui* files  every time you make a change. The downside is that the names of the form elements are not known during 
coding, so your IDE cannot check them. To easily find naming errors during development run your code in debug mode; in 
case of a crash the name of the variable you've missed is written to the console. 

###### Window geometry
The window position and size, and the place of the various splitters which separate the panes are saved when
closing a dialog and restored when opening the dialog again. On Windows these settings are stored in an *.ini* file. 
The name of this file is written to the logger when starting the application.  

###### Qt Designer
Package pyqt5-tools contains the Qt Designer executable. It can be found in the Scripts directory of your Python 
installation. See [pypi](https://pypi.org/project/pyqt5-tools/) for the exact name of the designer executable.

![Qt Desginer](/qtdesigner.png)
*Qt Designer open for all three dialogs*

###### Universal?
The approach is universal as long as you want to test a separate executable for which you can pipe stdin and capture 
stdout and stderr (if needed). If you need to specify more files when starting the executable then small changes to 
function *runner.run_single_script* might be needed.
