""" Loader for .ui files created in Qt Designer. """

import os
import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QWidget

import config


def loadUi(module_path: str, widget: QWidget, basename: str = None):
    """Load the ui file associated with the module path and widget class.

    For example: if the widget's class is called MyWidget then ui file
    mywidget.ui will be loaded. Optional parameter basename overrides
    the derivation of the ui filename from the class name.

    Usage: loadUi(__file__, self)

    :param str module_path:
    :param QWidget widget:
    :param str basename:
    """

    if getattr(sys, 'frozen', False):
        # If script is frozen read the ui files from a directory named 'ui'.
        # BEWARE: this directory-name is hard-coded. So for a frozen script
        # do not forget to copy all *.ui files to 'ui' in the build directory.
        basepath = os.path.join(config.appdir, "ui")
    else:
        basepath = os.path.dirname(module_path)

    if basename is None:
        basename = widget.__class__.__name__.lower()

    uifile = os.path.join(basepath, "{}.ui".format(basename))

    # raise FileNotFoundError if uifile cannot be found to avoid mysterious Qt errors
    with open(uifile, mode="r"):
        pass

    uic.loadUi(uifile, widget)
