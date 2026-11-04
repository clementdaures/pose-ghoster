"""Pinned ghosts section.
"""

# region Imports & Config

# pyside modules
from ..qt_compat import QtWidgets

# pose_ghoster modules
from ..controller import PanelController
from .factory import make_button, make_check

# endregion

# ==========

# region PinsBox


class PinsBox(QtWidgets.QGroupBox):
    """Card with the pin, navigation and delete buttons.

    Args:
        ctl (PanelController): Host backend.
        parent (QtWidgets.QWidget, optional): Parent widget.

    """

    def __init__(self, ctl: PanelController, parent=None) -> None:
        super().__init__("Pinned ghosts", parent)
        s = ctl.get_settings()
        layout = QtWidgets.QVBoxLayout(self)
        for pair in (
            (("Pin Pose", ctl.pin, None), ("Update Pin", ctl.update_pin, None)),
            (
                ("<<< Previous Pin", lambda: ctl.go_to_pin(-1), None),
                ("Next Pin >>>", lambda: ctl.go_to_pin(1), None),
            ),
            (
                ("Delete Current Pin", ctl.unpin, "dangerButton"),
                ("Delete All Pins", ctl.clear_pins, "dangerButton"),
            ),
        ):
            line = QtWidgets.QHBoxLayout()
            for text, fn, role in pair:
                line.addWidget(make_button(text, fn, role))
            layout.addLayout(line)
        layout.addWidget(make_check(ctl, "Show pins", "show_pins", s.show_pins))


# endregion
