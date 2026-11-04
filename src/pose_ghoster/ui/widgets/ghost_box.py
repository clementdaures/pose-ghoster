"""Ghosts section: mode, counts, playback, vertex budget and key source.
"""

# region Imports & Config

# pyside modules
from ..qt_compat import QtWidgets

# pose_ghoster modules
from ..controller import PanelController
from .factory import make_button, make_spin, split_names

PLAYBACK_MODES = (
    ("Hide during playback (fastest)", "hide"),
    ("Freeze during playback", "freeze"),
    ("Live during playback", "live"),
)
MODES = (
    ("Relative (T-n / T+n)", "relative"),
    ("Keys (previous / next keyed pose)", "keys"),
    ("Off (pins only)", "off"),
)

# endregion

# ==========

# region GhostBox


class GhostBox(QtWidgets.QGroupBox):
    """Card holding every ghost-selection setting.

    Args:
        ctl (PanelController): Host backend.
        parent (QtWidgets.QWidget, optional): Parent widget.

    """

    def __init__(self, ctl: PanelController, parent=None) -> None:
        super().__init__("Ghosts", parent)
        self.ctl = ctl
        s = ctl.get_settings()
        grid = QtWidgets.QGridLayout(self)

        self.mode_combo = QtWidgets.QComboBox()
        for label, mode in MODES:
            self.mode_combo.addItem(label, mode)
        self.mode_combo.currentIndexChanged.connect(
            lambda _: ctl.set_settings(mode=self.mode_combo.currentData())
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
            grid.addWidget(make_spin(ctl, low, 30, value, attr), 1, col * 2 + 1)
        grid.addWidget(QtWidgets.QLabel("Prev keys"), 2, 0)
        grid.addWidget(make_spin(ctl, 0, 10, s.key_past_count, "key_past_count"), 2, 1)
        grid.addWidget(QtWidgets.QLabel("Next keys"), 2, 2)
        grid.addWidget(
            make_spin(ctl, 0, 10, s.key_future_count, "key_future_count"), 2, 3
        )

        self.playback_combo = QtWidgets.QComboBox()
        for label, mode in PLAYBACK_MODES:
            self.playback_combo.addItem(label, mode)
        self.playback_combo.currentIndexChanged.connect(
            lambda _: ctl.set_settings(playback_mode=self.playback_combo.currentData())
        )
        grid.addWidget(self.playback_combo, 4, 0, 1, 4)
        grid.addWidget(QtWidgets.QLabel("Max verts (k)"), 4, 4)
        budget = QtWidgets.QSpinBox()
        budget.setRange(0, 5000)
        budget.setValue(int(s.max_vertices / 1000))
        budget.valueChanged.connect(lambda v: ctl.set_settings(max_vertices=v * 1000))
        grid.addWidget(budget, 4, 5)

        self.key_line = QtWidgets.QLineEdit()
        self.key_line.setPlaceholderText("Auto (curves upstream of the mesh)")
        self.key_line.editingFinished.connect(self._key_sources_edited)
        src = QtWidgets.QHBoxLayout()
        src.addWidget(QtWidgets.QLabel("Key source:"))
        src.addWidget(self.key_line)
        src.addWidget(make_button("Controllers", self._key_from_selection))
        src.addWidget(make_button("Auto", self._key_auto))
        grid.addLayout(src, 3, 0, 1, 6)

    # -- slots
    def _key_sources_edited(self) -> None:
        self.ctl.set_key_sources(split_names(self.key_line))

    def _key_from_selection(self) -> None:
        sel = self.ctl.get_selection()
        if sel:
            self.key_line.setText(",".join(sel))
            self._key_sources_edited()

    def _key_auto(self) -> None:
        self.key_line.clear()
        self.ctl.set_key_sources([])


# endregion
