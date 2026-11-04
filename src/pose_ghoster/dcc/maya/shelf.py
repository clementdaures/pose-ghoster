"""Native Maya shelf and main-menu builder."""

# region Imports & Config

# python modules
from pathlib import Path
from typing import Optional

# dcc modules
from maya import cmds, mel

ICONS_DIR = Path(__file__).resolve().parent / "icons"
DEFAULT_ICON = "pythonFamily.png"
SHELF = "PoseGhoster"
MENU = "PoseGhosterMenu"

# (label, annotation, command, icon file or None for the default icon)
_BUTTONS = (
    (
        "Ghost UI",
        "Open the Pose Ghoster panel",
        "import pose_ghoster; pose_ghoster.show_ui()",
        "ghost_logo.png",
    ),
    (
        "On/Off",
        "Toggle ghosting",
        "import pose_ghoster; pose_ghoster.toggle()",
        "toggle_logo.png",
    ),
)

# endregion

# ==========

# region Shelf & Menu


def install() -> None:
    """Build the shelf and the main menu (rebuilds them when they exist)."""
    _build_shelf()
    _build_menu()


def uninstall() -> None:
    """Deactivate ghosting and delete the shelf and the main menu."""
    try:
        import pose_ghoster

        pose_ghoster.deactivate()
    except Exception:
        pass
    if cmds.shelfLayout(SHELF, exists=True):
        cmds.deleteUI(SHELF, layout=True)
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU, menu=True)


def get_icon(name: str) -> str:
    """Return the full path of a package icon.

    Args:
        name (str): Icon file name, e.g. ``"ghost_logo.png"``.

    Returns:
        str: Path with forward slashes, as expected by Maya.

    """
    return (ICONS_DIR / name).as_posix()


def _resolve_icon(icon: Optional[str]) -> str:
    """Return the icon to use for a button, falling back to Maya's default.

    Args:
        icon (str, optional): Package icon file name, or None.

    Returns:
        str: Full path of the package icon, or the default Maya icon name.

    """
    if icon and (ICONS_DIR / icon).is_file():
        return get_icon(icon)
    return DEFAULT_ICON


def _build_shelf() -> None:
    top = mel.eval("$tmp = $gShelfTopLevel")
    if cmds.shelfLayout(SHELF, exists=True):
        for child in cmds.shelfLayout(SHELF, q=True, childArray=True) or []:
            cmds.deleteUI(child)
    else:
        cmds.shelfLayout(SHELF, parent=top)
    for label, tip, command, icon in _BUTTONS:
        cmds.shelfButton(
            parent=SHELF,
            label=label,
            annotation=tip,
            # The logo speaks for itself, the text overlay stays on default icons
            imageOverlayLabel="" if icon else label,
            image1=_resolve_icon(icon),
            sourceType="python",
            command=command,
        )


def _build_menu() -> None:
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU, menu=True)
    main = mel.eval("$tmp = $gMainWindow")
    cmds.menu(MENU, label="Pose Ghoster", parent=main, tearOff=True)
    for label, _, command, _ in _BUTTONS:
        cmds.menuItem(label=label, command=command, sourceType="python", parent=MENU)


# endregion