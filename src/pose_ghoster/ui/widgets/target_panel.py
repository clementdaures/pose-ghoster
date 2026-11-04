"""Top section: ghosting switch, geo to ghost and follow selection.
"""

# region Imports & Config

# pyside modules
from ..qt_compat import QtWidgets

# pose_ghoster modules
from ..controller import PanelController
from .factory import make_button, split_names

# endregion

# ==========

# region TargetPanel


class TargetPanel(QtWidgets.QWidget):
    """Ghosting on/off button, geometry field and follow-selection option.

    Args:
        ctl (PanelController): Host backend.
        parent (QtWidgets.QWidget, optional): Parent widget.

    """

    def __init__(self, ctl: PanelController, parent=None) -> None:
        super().__init__(parent)
        self.ctl = ctl

        self.toggle_btn = QtWidgets.QPushButton("Ghosting: OFF")
        self.toggle_btn.setProperty("role", "toggleButton")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._toggle)

        self.geo_line = QtWidgets.QLineEdit()
        self.geo_line.editingFinished.connect(self._geo_edited)

        self.follow_cb = QtWidgets.QCheckBox("Follow selection")
        self.follow_cb.setChecked(True)
        self.follow_cb.toggled.connect(self.ctl.set_follow_selection)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Geo to ghost:"))
        row.addWidget(self.geo_line)
        row.addWidget(make_button("Add Geo", self._add_geo))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_btn)
        layout.addLayout(row)
        layout.addWidget(self.follow_cb)

    def sync(self) -> None:
        """Reflect the controller's active state on the toggle button."""
        active = self.ctl.is_active()
        self.toggle_btn.blockSignals(True)
        self.toggle_btn.setChecked(active)
        self.toggle_btn.setText("Ghosting: ON" if active else "Ghosting: OFF")
        self.toggle_btn.blockSignals(False)

    # -- slots
    def _toggle(self, on: bool) -> None:
        if on:
            self.ctl.activate(
                split_names(self.geo_line) or None, self.follow_cb.isChecked()
            )
        else:
            self.ctl.deactivate()

    def _add_geo(self) -> None:
        sel = self.ctl.get_selection()
        if not sel:
            return
        self.geo_line.setText(",".join(sel))
        self.follow_cb.setChecked(False)
        self._geo_edited()

    def _geo_edited(self) -> None:
        nodes = split_names(self.geo_line)
        if nodes and self.ctl.is_active():
            self.ctl.set_targets(nodes, False)


# endregion
