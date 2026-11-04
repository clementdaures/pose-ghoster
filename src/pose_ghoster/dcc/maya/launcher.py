"""Launches the Pose Ghoster window inside Maya.
"""

# region Imports & Config

# dcc import
import maya.OpenMayaUI as omui

# pyside modules
from pose_ghoster.ui.qt_compat import QtWidgets, wrap_instance

# pose_ghoster modules
from pose_ghoster.dcc.maya.controller import MayaPanelController
from pose_ghoster.ui.main_window import OBJECT_NAME, PoseGhosterWindow

# endregion

# ==========

# region Main Logic


def maya_main_window() -> QtWidgets.QWidget:
    """Return Maya's main window as a QWidget.

    Returns:
        QtWidgets.QWidget: Parent suitable for Maya-owned windows.

    """
    return wrap_instance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def launch() -> PoseGhosterWindow:
    """Open the panel, closing any previous instance first.

    Returns:
        PoseGhosterWindow: The displayed panel.

    """
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == OBJECT_NAME:
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass
    panel = PoseGhosterWindow(MayaPanelController(), maya_main_window())
    panel.show()
    return panel


# endregion

if __name__ == "__main__":
    launch()
