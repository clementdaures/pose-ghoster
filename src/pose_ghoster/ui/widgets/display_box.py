"""Display section: opacity, fill and wire.
"""

# region Imports & Config

# pyside modules
from ..qt_compat import QtCore, QtWidgets

# pose_ghoster modules
from ..controller import PanelController
from .factory import make_check

# endregion

# ==========

# region DisplayBox


class DisplayBox(QtWidgets.QGroupBox):
    """Card with the ghost appearance settings.

    Args:
        ctl (PanelController): Host backend.
        parent (QtWidgets.QWidget, optional): Parent widget.

    """

    def __init__(self, ctl: PanelController, parent=None) -> None:
        super().__init__("Display", parent)
        s = ctl.get_settings()
        row = QtWidgets.QHBoxLayout(self)
        row.addWidget(QtWidgets.QLabel("Opacity"))
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, 10)
        slider.setValue(int(s.opacity * 10))
        slider.valueChanged.connect(lambda v: ctl.set_settings(opacity=v / 10.0))
        row.addWidget(slider)
        for text, attr in (("Fill", "show_fill"), ("Wire", "show_wire")):
            row.addWidget(make_check(ctl, text, attr, getattr(s, attr)))


# endregion
