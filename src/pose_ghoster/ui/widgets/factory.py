"""Small widget factories shared by the panel sections.
"""

# region Imports & Config

# python modules
from typing import Callable, Optional

# pyside modules
from ..qt_compat import QtWidgets

# pose_ghoster modules
from ..controller import PanelController

# endregion

# ==========

# region Factories


def make_button(
    text: str, slot: Callable, role: Optional[str] = None
) -> QtWidgets.QPushButton:
    """Create a push button calling ``slot()`` when clicked.

    Args:
        text (str): Button label.
        slot (callable): Called without arguments.
        role (str, optional): Semantic role set as the ``role`` property.

    Returns:
        QtWidgets.QPushButton: The button.

    """
    btn = QtWidgets.QPushButton(text)
    if role:
        btn.setProperty("role", role)
    btn.clicked.connect(lambda _=False: slot())
    return btn


def make_spin(
    ctl: PanelController, low: int, high: int, value: int, attr: str
) -> QtWidgets.QSpinBox:
    """Create a spin box bound to one setting.

    Args:
        ctl (PanelController): Receives ``set_settings(attr=value)``.
        low (int): Minimum.
        high (int): Maximum.
        value (int): Initial value.
        attr (str): Settings field name.

    Returns:
        QtWidgets.QSpinBox: The spin box.

    """
    spin = QtWidgets.QSpinBox()
    spin.setRange(low, high)
    spin.setValue(int(value))
    spin.valueChanged.connect(lambda v: ctl.set_settings(**{attr: v}))
    return spin


def make_check(
    ctl: PanelController, text: str, attr: str, value: bool
) -> QtWidgets.QCheckBox:
    """Create a check box bound to one setting.

    Args:
        ctl (PanelController): Receives ``set_settings(attr=checked)``.
        text (str): Label.
        attr (str): Settings field name.
        value (bool): Initial state.

    Returns:
        QtWidgets.QCheckBox: The check box.

    """
    box = QtWidgets.QCheckBox(text)
    box.setChecked(bool(value))
    box.toggled.connect(lambda v: ctl.set_settings(**{attr: v}))
    return box


def split_names(line: QtWidgets.QLineEdit) -> list:
    """Return the comma separated names typed in a line edit.

    Args:
        line (QtWidgets.QLineEdit): Source field.

    Returns:
        list[str]: Stripped, non-empty names.

    """
    return [t.strip() for t in line.text().split(",") if t.strip()]


# endregion
