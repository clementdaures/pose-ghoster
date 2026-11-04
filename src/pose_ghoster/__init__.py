"""Pose Ghoster: GPU-drawn pose ghosts for Maya.

Public entry points. Everything is imported lazily so that
``pose_ghoster.core`` stays importable outside Maya (unit tests).
"""

# region Imports & Config

# python modules
from typing import Any, List, Optional

__version__ = "0.1.0"

# endregion

# ==========

# region Public API


def install() -> None:
    """Build the Pose Ghoster shelf and main menu."""
    from pose_ghoster.dcc.maya import shelf

    shelf.install()


def uninstall() -> None:
    """Deactivate ghosting and remove the shelf and main menu."""
    from pose_ghoster.dcc.maya import shelf

    shelf.uninstall()


def show_ui() -> Any:
    """Open the control window.

    Returns:
        PoseGhosterWindow: The displayed window.

    """
    from pose_ghoster.dcc.maya import launcher

    return launcher.launch()


def activate(nodes: Optional[List[str]] = None, follow_selection: bool = True) -> bool:
    """Start ghosting.

    Args:
        nodes (list[str], optional): Meshes or groups to ghost. Defaults to
            the current selection.
        follow_selection (bool): Retarget when the selection changes.

    Returns:
        bool: True once ghosting is active.

    """
    from pose_ghoster.dcc import maya as dcc

    return dcc.activate(nodes, follow_selection)


def deactivate() -> None:
    """Stop ghosting and release every cached resource."""
    from pose_ghoster.dcc import maya as dcc

    dcc.deactivate()


def toggle() -> None:
    """Switch ghosting on or off."""
    from pose_ghoster.dcc import maya as dcc

    if dcc.is_active():
        dcc.deactivate()
    else:
        dcc.activate()


# endregion
