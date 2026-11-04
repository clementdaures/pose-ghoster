"""Qt stylesheet of the Ghost design system.
"""

# region Imports & Config

# pyside modules
from ..qt_compat import QtWidgets

# pose_ghoster/ui/theme/..
from .colors import COLORS

# endregion

# ==========

# region Stylesheet Logic


def build_stylesheet(colors: dict = COLORS) -> str:
    """Build the Ghost Qt stylesheet.

    Args:
        colors (dict[str, str]): Palette to use. Defaults to ``COLORS``.

    Returns:
        str: Complete Qt stylesheet.

    """
    return f"""
    /* ------------------------------------------------------------------
       Global
       ------------------------------------------------------------------ */

    QWidget {{
        background: {colors["bg"]};
        color: {colors["text"]};
        font-family: "Inter", "Segoe UI", sans-serif;
        font-size: 12px;
    }}

    QMainWindow {{
        background: {colors["bg"]};
    }}

    QLabel,
    QCheckBox,
    QSlider {{
        background: transparent;
    }}

    /* Plain layout containers stay transparent so cards sit on the window
       background. ".QWidget" matches the exact class only, so windows and
       every other widget keep the background set above. */

    .QWidget {{
        background: transparent;
    }}

    .QWidget:window {{
        background: {colors["bg"]};
    }}


    /* ------------------------------------------------------------------
       Cards (group boxes)
       ------------------------------------------------------------------ */

    QGroupBox {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 11px;
        margin-top: 18px;
        padding: 10px 10px 8px 10px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 4px;
        padding: 0 2px;
        color: {colors["muted"]};
        background: transparent;
        font-weight: 600;
    }}

    /* A group box title is bold; its content must not inherit that. */

    QGroupBox QLabel,
    QGroupBox QCheckBox,
    QGroupBox QPushButton,
    QGroupBox QLineEdit,
    QGroupBox QSpinBox,
    QGroupBox QComboBox {{
        font-weight: 400;
    }}


    /* ------------------------------------------------------------------
       Buttons
       ------------------------------------------------------------------ */

    QPushButton {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 5px 13px;
        min-height: 16px;
    }}

    QPushButton:hover {{
        background: {colors["accent_subtle"]};
        border-color: {colors["accent"]};
    }}

    QPushButton:pressed {{
        background: {colors["accent_soft"]};
    }}

    QPushButton:disabled {{
        color: {colors["faint"]};
        background: {colors["surface2"]};
    }}

    /* On/off toggle: soft when off, filled accent when on */

    QPushButton[role="toggleButton"] {{
        background: {colors["accent_soft"]};
        color: {colors["accent_hover"]};
        border: 1px solid {colors["accent_soft"]};
        font-weight: 600;
        padding: 8px 13px;
    }}

    QPushButton[role="toggleButton"]:hover {{
        border-color: {colors["accent"]};
    }}

    QPushButton[role="toggleButton"]:checked {{
        background: {colors["accent"]};
        color: {colors["on_accent"]};
        border-color: {colors["accent"]};
    }}

    QPushButton[role="toggleButton"]:checked:hover {{
        background: {colors["accent_hover"]};
        border-color: {colors["accent_hover"]};
    }}

    /* Destructive actions */

    QPushButton[role="dangerButton"] {{
        background: {colors["error_soft"]};
        color: {colors["error"]};
        border: 1px solid transparent;
    }}

    QPushButton[role="dangerButton"]:hover {{
        border-color: {colors["error"]};
    }}

    QPushButton[role="dangerButton"]:pressed {{
        background: {colors["error_soft"]};
    }}


    /* ------------------------------------------------------------------
       Inputs
       ------------------------------------------------------------------ */

    QLineEdit,
    QComboBox,
    QSpinBox {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 4px 8px;
        selection-background-color: {colors["accent_soft"]};
        selection-color: {colors["text"]};
    }}

    QLineEdit:hover,
    QComboBox:hover,
    QSpinBox:hover {{
        border-color: {colors["faint"]};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox:focus {{
        border-color: {colors["accent"]};
    }}

    QLineEdit:disabled,
    QComboBox:disabled,
    QSpinBox:disabled {{
        background: {colors["surface2"]};
        color: {colors["faint"]};
    }}

    QComboBox QAbstractItemView {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        outline: none;
        selection-background-color: {colors["accent_soft"]};
        selection-color: {colors["text"]};
    }}


    /* ------------------------------------------------------------------
       Checkboxes
       ------------------------------------------------------------------ */

    QCheckBox {{
        spacing: 7px;
    }}

    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {colors["border"]};
        border-radius: 4px;
        background: {colors["surface"]};
    }}

    QCheckBox::indicator:hover {{
        border-color: {colors["accent"]};
    }}

    QCheckBox::indicator:checked {{
        background: {colors["accent"]};
        border-color: {colors["accent"]};
    }}

    QCheckBox:disabled {{
        color: {colors["faint"]};
    }}


    /* ------------------------------------------------------------------
       Slider
       ------------------------------------------------------------------ */

    QSlider:horizontal {{
        min-height: 24px;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {colors["border"]};
        border-radius: 2px;
    }}

    QSlider::sub-page:horizontal {{
        background: {colors["accent"]};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        width: 12px;
        height: 12px;
        margin: -6px 0;
        background: {colors["surface"]};
        border: 2px solid {colors["accent"]};
        border-radius: 8px;
    }}

    QSlider::handle:horizontal:hover {{
        background: {colors["accent_soft"]};
    }}


    /* ------------------------------------------------------------------
       Menu bar and menus
       ------------------------------------------------------------------ */

    QMenuBar {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border-bottom: 1px solid {colors["border"]};
        padding: 2px 4px;
    }}

    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
        border-radius: 6px;
    }}

    QMenuBar::item:selected {{
        background: {colors["accent_soft"]};
        color: {colors["accent_hover"]};
    }}

    QMenu {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px 6px 14px;
        border-radius: 6px;
        margin: 1px 2px;
    }}

    QMenu::item:selected {{
        background: {colors["accent_soft"]};
    }}

    QMenu::item:disabled {{
        color: {colors["faint"]};
    }}

    QMenu::separator {{
        height: 1px;
        background: {colors["border"]};
        margin: 4px 8px;
    }}


    /* ------------------------------------------------------------------
       Status bar (accent colored)
       ------------------------------------------------------------------ */

    QStatusBar {{
        background: {colors["accent"]};
        color: {colors["on_accent"]};
    }}

    QStatusBar QLabel {{
        background: transparent;
        color: {colors["on_accent"]};
        padding: 2px 6px;
    }}

    QStatusBar::item {{
        border: none;
    }}


    /* ------------------------------------------------------------------
       Tooltips
       ------------------------------------------------------------------ */

    QToolTip {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        padding: 5px 7px;
    }}
    """


def apply_stylesheet(widget: QtWidgets.QWidget, colors: dict = COLORS) -> None:
    """Apply the Ghost stylesheet to one widget (and its children).

    Args:
        widget (QtWidgets.QWidget): Window receiving the stylesheet.
        colors (dict[str, str]): Palette to use. Defaults to ``COLORS``.

    """
    widget.setStyleSheet(build_stylesheet(colors))


# endregion
