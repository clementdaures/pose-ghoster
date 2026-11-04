"""Native Maya shelf and main-menu builder.
"""

# region Imports & Config

# dcc import
from maya import cmds, mel

SHELF = "PoseGhoster"
MENU = "PoseGhosterMenu"
_BUTTONS = (
    (
        "Ghost UI",
        "Open the Pose Ghoster panel",
        "import pose_ghoster; pose_ghoster.show_ui()",
    ),
    ("On/Off", "Toggle ghosting", "import pose_ghoster; pose_ghoster.toggle()"),
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


def _build_shelf() -> None:
    top = mel.eval("$tmp = $gShelfTopLevel")
    if cmds.shelfLayout(SHELF, exists=True):
        for child in cmds.shelfLayout(SHELF, q=True, childArray=True) or []:
            cmds.deleteUI(child)
    else:
        cmds.shelfLayout(SHELF, parent=top)
    for label, tip, command in _BUTTONS:
        cmds.shelfButton(
            parent=SHELF,
            label=label,
            annotation=tip,
            imageOverlayLabel=label,
            image1="pythonFamily.png",
            sourceType="python",
            command=command,
        )


def _build_menu() -> None:
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU, menu=True)
    main = mel.eval("$tmp = $gMainWindow")
    cmds.menu(MENU, label="Pose Ghoster", parent=main, tearOff=True)
    for label, _, command in _BUTTONS:
        cmds.menuItem(label=label, command=command, sourceType="python", parent=MENU)


# endregion
