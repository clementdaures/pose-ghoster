"""Qt compatibility layer: Qt.py first, direct PySide6/PySide2 as fallback.
"""

# region Imports & Config

# pyside modules
try:
    from Qt import QtCompat, QtCore, QtGui, QtWidgets

    wrap_instance = QtCompat.wrapInstance
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        from shiboken6 import wrapInstance as wrap_instance
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets
        from shiboken2 import wrapInstance as wrap_instance

# QAction moved from QtWidgets (Qt 5) to QtGui (Qt 6).
QAction = getattr(QtGui, "QAction", None) or QtWidgets.QAction

__all__ = ["QAction", "QtCore", "QtGui", "QtWidgets", "wrap_instance"]

# endregion
