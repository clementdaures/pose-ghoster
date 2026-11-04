"""Floating control panel, free of any DCC import.
"""

# region Imports & Config

# python modules
from typing import Callable, List, Optional

# pyside modules
from .qt_compat import QtCore, QtWidgets

# pose_ghoster modules
from .controller import PanelController

OBJECT_NAME = "PoseGhosterPanel"
STYLE = """
QWidget { background-color:#303030; color:#ddd; font-family:Segoe UI; font-size:8pt; }
QPushButton { background-color:#404040; border:1px solid #262626;
              border-radius:4px; padding:4px 8px; }
QPushButton:hover { border:1px solid #7a53cf; }
QPushButton:checked { background-color:#7a53cf; }
QLineEdit, QSpinBox, QComboBox { background-color:#262626; border:1px solid #555;
                                 border-radius:3px; padding:2px; }
QGroupBox { border:1px solid #7a53cf; border-radius:5px; margin-top:6px;
            padding:6px; font-weight:bold; }
"""
PLAYBACK_MODES = (
    ("Hide during playback (fastest)", "hide"),
    ("Freeze during playback", "freeze"),
    ("Live during playback", "live"),
)
MODES = (
    ("Relative (T-n / T+n)", "relative"),
    ("Keys (previous / next keyed pose)", "keys"),
    ("Off (pins and take only)", "off"),
)

# endregion

# ==========

# region Panel


class PoseGhosterPanel(QtWidgets.QWidget):
    """Qt panel driving a PanelController.

    Args:
        controller (PanelController): Host backend.
        parent (QtWidgets.QWidget, optional): Parent widget.

    """

    def __init__(
        self,
        controller: PanelController,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.ctl = controller
        self.setObjectName(OBJECT_NAME)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Pose Ghoster")
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLE)
        self._build()
        self.ctl.add_listener(self._on_update)
        self._on_update(None)

    # -- widget factories
    @staticmethod
    def _button(text: str, slot: Callable) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.clicked.connect(lambda _=False: slot())
        return btn

    def _spin(self, low: int, high: int, value: int, attr: str) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(low, high)
        spin.setValue(int(value))
        spin.valueChanged.connect(lambda v: self.ctl.set_settings(**{attr: v}))
        return spin

    def _check(self, text: str, attr: str, value: bool) -> QtWidgets.QCheckBox:
        box = QtWidgets.QCheckBox(text)
        box.setChecked(bool(value))
        box.toggled.connect(lambda v: self.ctl.set_settings(**{attr: v}))
        return box

    # -- UI construction
    def _build(self) -> None:
        s = self.ctl.get_settings()
        root = QtWidgets.QVBoxLayout(self)

        self.toggle_btn = QtWidgets.QPushButton("Ghosting: OFF")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._toggle)
        root.addWidget(self.toggle_btn)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Geo to ghost:"))
        self.geo_line = QtWidgets.QLineEdit()
        self.geo_line.editingFinished.connect(self._geo_edited)
        row.addWidget(self.geo_line)
        row.addWidget(self._button("Add Geo", self._add_geo))
        root.addLayout(row)

        self.follow_cb = QtWidgets.QCheckBox("Follow selection")
        self.follow_cb.setChecked(True)
        self.follow_cb.toggled.connect(self.ctl.set_follow_selection)
        root.addWidget(self.follow_cb)

        root.addWidget(self._ghost_box(s))
        root.addWidget(self._display_box(s))
        root.addWidget(self._pins_box())
        root.addWidget(self._take_box(s))

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self._button("Refresh", self.ctl.refresh))
        self.status = QtWidgets.QLabel("")
        bottom.addWidget(self.status, 1)
        root.addLayout(bottom)

    def _ghost_box(self, s) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Ghosts")
        grid = QtWidgets.QGridLayout(box)
        self.mode_combo = QtWidgets.QComboBox()
        for label, mode in MODES:
            self.mode_combo.addItem(label, mode)
        self.mode_combo.currentIndexChanged.connect(
            lambda _: self.ctl.set_settings(mode=self.mode_combo.currentData())
        )
        grid.addWidget(self.mode_combo, 0, 0, 1, 6)
        for col, (text, attr, low, value) in enumerate(
            (
                ("Past", "past_count", 0, s.past_count),
                ("Future", "future_count", 0, s.future_count),
                ("Step", "step", 1, s.step),
            )
        ):
            grid.addWidget(QtWidgets.QLabel(text), 1, col * 2)
            grid.addWidget(self._spin(low, 30, value, attr), 1, col * 2 + 1)
        grid.addWidget(QtWidgets.QLabel("Prev keys"), 2, 0)
        grid.addWidget(self._spin(0, 10, s.key_past_count, "key_past_count"), 2, 1)
        grid.addWidget(QtWidgets.QLabel("Next keys"), 2, 2)
        grid.addWidget(self._spin(0, 10, s.key_future_count, "key_future_count"), 2, 3)

        self.playback_combo = QtWidgets.QComboBox()
        for label, mode in PLAYBACK_MODES:
            self.playback_combo.addItem(label, mode)
        self.playback_combo.currentIndexChanged.connect(
            lambda _: self.ctl.set_settings(
                playback_mode=self.playback_combo.currentData()
            )
        )
        grid.addWidget(self.playback_combo, 4, 0, 1, 4)
        grid.addWidget(QtWidgets.QLabel("Max verts (k)"), 4, 4)
        budget = QtWidgets.QSpinBox()
        budget.setRange(0, 5000)
        budget.setValue(int(s.max_vertices / 1000))
        budget.valueChanged.connect(
            lambda v: self.ctl.set_settings(max_vertices=v * 1000)
        )
        grid.addWidget(budget, 4, 5)

        src = QtWidgets.QHBoxLayout()
        src.addWidget(QtWidgets.QLabel("Key source:"))
        self.key_line = QtWidgets.QLineEdit()
        self.key_line.setPlaceholderText("Auto (curves upstream of the mesh)")
        self.key_line.editingFinished.connect(self._key_sources_edited)
        src.addWidget(self.key_line)
        src.addWidget(self._button("Controllers", self._key_from_selection))
        src.addWidget(self._button("Auto", self._key_auto))
        grid.addLayout(src, 3, 0, 1, 6)
        return box

    def _display_box(self, s) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Display")
        row = QtWidgets.QHBoxLayout(box)
        row.addWidget(QtWidgets.QLabel("Opacity"))
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, 10)
        slider.setValue(int(s.opacity * 10))
        slider.valueChanged.connect(lambda v: self.ctl.set_settings(opacity=v / 10.0))
        row.addWidget(slider)
        for text, attr in (
            ("Fill", "show_fill"),
            ("Wire", "show_wire"),
            ("In front", "in_front"),
        ):
            row.addWidget(self._check(text, attr, getattr(s, attr)))
        return box

    def _pins_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Pinned ghosts")
        grid = QtWidgets.QVBoxLayout(box)
        for pair in (
            (("Pin Pose", self.ctl.pin), ("Update Pin", self.ctl.update_pin)),
            (
                ("<<< Previous Pin", lambda: self.ctl.go_to_pin(-1)),
                ("Next Pin >>>", lambda: self.ctl.go_to_pin(1)),
            ),
            (
                ("Delete Current Pin", self.ctl.unpin),
                ("Delete All Pins", self.ctl.clear_pins),
            ),
        ):
            line = QtWidgets.QHBoxLayout()
            for text, fn in pair:
                line.addWidget(self._button(text, fn))
            grid.addLayout(line)
        grid.addWidget(self._check("Show pins", "show_pins", True))
        return box

    def _take_box(self, s) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Compare (A/B)")
        row = QtWidgets.QHBoxLayout(box)
        row.addWidget(self._button("Capture Take A", self.ctl.capture_take))
        row.addWidget(self._button("Clear Take A", self.ctl.clear_take))
        row.addWidget(self._check("Show take", "show_take", s.show_take))
        return box

    # -- slots
    def _names(self, line: QtWidgets.QLineEdit) -> List[str]:
        return [t.strip() for t in line.text().split(",") if t.strip()]

    def _toggle(self, on: bool) -> None:
        if on:
            self.ctl.activate(
                self._names(self.geo_line) or None, self.follow_cb.isChecked()
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
        nodes = self._names(self.geo_line)
        if nodes and self.ctl.is_active():
            self.ctl.set_targets(nodes, False)

    def _key_sources_edited(self) -> None:
        self.ctl.set_key_sources(self._names(self.key_line))

    def _key_from_selection(self) -> None:
        sel = self.ctl.get_selection()
        if sel:
            self.key_line.setText(",".join(sel))
            self._key_sources_edited()

    def _key_auto(self) -> None:
        self.key_line.clear()
        self.ctl.set_key_sources([])

    def _on_update(self, _source) -> None:
        active = self.ctl.is_active()
        self.toggle_btn.blockSignals(True)
        self.toggle_btn.setChecked(active)
        self.toggle_btn.setText("Ghosting: ON" if active else "Ghosting: OFF")
        self.toggle_btn.blockSignals(False)
        self.status.setText(self.ctl.status_text())

    def closeEvent(self, event) -> None:
        """Release everything when the panel is closed."""
        self.ctl.remove_listener(self._on_update)
        self.ctl.deactivate()
        super().closeEvent(event)


# endregion
