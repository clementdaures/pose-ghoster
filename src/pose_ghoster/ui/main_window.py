"""Pose Ghoster main window, free of any DCC import.
"""

# region Imports & Config

# python modules
from typing import Optional

# pyside modules
from .qt_compat import QAction, QtCore, QtGui, QtWidgets

# pose_ghoster modules
from .controller import PanelController
from .theme import apply_stylesheet
from .widgets import DisplayBox, GhostBox, PinsBox, TargetPanel

OBJECT_NAME = "PoseGhosterPanel"
APP_TITLE = "Pose Ghoster"
DOCS_URL = "https://docs.clementdaures.com/pose-ghoster"
AUTHOR_URL = "https://clementdaures.com"
# TODO: point this to the issue tracker (or a mailto: link) once it is known.
REPORT_BUG_URL = "https://clementdaures.com"

# endregion

# ==========

# region Main Window


class PoseGhosterWindow(QtWidgets.QMainWindow):
    """Floating window driving a PanelController.

    The layout is a stack of cards (target, ghosts, display, pins). Actions
    live in the menu bar (Edit, Help) and the one-line ghost status is shown
    in the status bar.

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
        self.setWindowTitle(APP_TITLE)
        self.setMinimumWidth(500)
        # Set on this window only, never on the host application.
        apply_stylesheet(self)
        self._build_ui()
        self._build_menus()
        self.ctl.add_listener(self._on_update)
        self._on_update(None)

    # region UI Construction

    def _build_ui(self) -> None:
        """Stack the sections in the central widget."""
        self.target_panel = TargetPanel(self.ctl)
        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.target_panel)
        layout.addWidget(GhostBox(self.ctl))
        layout.addWidget(DisplayBox(self.ctl))
        layout.addWidget(PinsBox(self.ctl))
        self.setCentralWidget(root)

    def _build_menus(self) -> None:
        """Create the Edit and Help menus and the status bar."""
        bar = self.menuBar()

        edit = bar.addMenu("Edit")
        self.refresh_action = self._action(
            "Refresh", self.ctl.refresh, shortcut="F5"
        )
        edit.addAction(self.refresh_action)

        help_menu = bar.addMenu("Help")
        for text, url in (
            ("Help on Pose Ghoster", DOCS_URL),
            ("About Author", AUTHOR_URL),
            ("Report Bug", REPORT_BUG_URL),
        ):
            help_menu.addAction(
                self._action(text, lambda u=url: self._open_url(u))
            )

        self.statusBar()

    def _action(self, text: str, slot, shortcut: str = "") -> QAction:
        """Create a menu action calling ``slot()``.

        Args:
            text (str): Action label.
            slot (callable): Called without arguments.
            shortcut (str): Optional key sequence.

        Returns:
            QAction: The action.

        """
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
        action.triggered.connect(lambda _checked=False: slot())
        return action

    # endregion

    # region Slots

    @staticmethod
    def _open_url(url: str) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _on_update(self, _source) -> None:
        self.target_panel.sync()
        self.statusBar().showMessage(self.ctl.status_text())

    def closeEvent(self, event) -> None:
        """Release everything when the window is closed."""
        self.ctl.remove_listener(self._on_update)
        self.ctl.deactivate()
        super().closeEvent(event)

    # endregion


# endregion
