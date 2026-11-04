"""Drag-and-drop installer for Pose Ghoster (Maya 2022+).

Drop this file into a Maya viewport. It will:

1. Copy ``src/pose_ghoster`` into the Maya user ``scripts`` directory.
2. Add an auto-install block to ``userSetup.py`` (idempotent).
3. Install the shelf / menu right away, so no restart is needed.
"""

# region Imports & Config

# python modules
import inspect
import os
import shutil
import sys
from typing import List

# maya modules
import maya.cmds as cmds

PACKAGE_NAME = "pose_ghoster"
MARKER_BEGIN = "# >>> pose_ghoster (auto-generated) >>>"
MARKER_END = "# <<< pose_ghoster (auto-generated) <<<"
USERSETUP_BLOCK = """{begin}
import maya.utils
maya.utils.executeDeferred("import pose_ghoster; pose_ghoster.install()")
{end}
""".format(
    begin=MARKER_BEGIN, end=MARKER_END
)

# endregion

# ==========

# region Path Helpers


def get_installer_dir() -> str:
    """Return the folder containing this file, even when dropped in Maya.

    Returns:
        str: Absolute path of the installer folder.

    """
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(inspect.getfile(lambda: None)))


def get_scripts_dir() -> str:
    """Return the Maya user ``scripts`` directory.

    Returns:
        str: Normalized path of the scripts directory.

    """
    return os.path.normpath(cmds.internalVar(userScriptDir=True))


# endregion

# ==========

# region Install Steps


def copy_package(source: str, scripts_dir: str) -> str:
    """Copy the package into the scripts directory, replacing any old version.

    Args:
        source (str): Path of the ``pose_ghoster`` source folder.
        scripts_dir (str): Maya user scripts directory.

    Returns:
        str: Path of the installed package.

    """
    target = os.path.join(scripts_dir, PACKAGE_NAME)
    if os.path.isdir(target):
        shutil.rmtree(target)

    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return target


def update_user_setup(scripts_dir: str) -> str:
    """Add the auto-install block to ``userSetup.py`` without duplicating it.

    Args:
        scripts_dir (str): Maya user scripts directory.

    Returns:
        str: Path of the updated ``userSetup.py``.

    """
    path = os.path.join(scripts_dir, "userSetup.py")
    content = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()

    # Remove any previous block so re-installing never duplicates it
    if MARKER_BEGIN in content and MARKER_END in content:
        head, _, rest = content.partition(MARKER_BEGIN)
        _, _, tail = rest.partition(MARKER_END)
        content = head.rstrip() + "\n" + tail.lstrip("\n")

    content = content.rstrip()
    if content:
        content += "\n\n"
    content += USERSETUP_BLOCK

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def purge_modules() -> List[str]:
    """Drop stale ``pose_ghoster`` modules so a re-install loads the new code.

    Returns:
        list[str]: Names of the removed modules.

    """
    stale = [name for name in sys.modules if name.split(".")[0] == PACKAGE_NAME]
    for name in stale:
        del sys.modules[name]
    return stale


def install() -> None:
    """Run the full installation.

    Raises:
        RuntimeError: If ``src/pose_ghoster`` cannot be found next to this file.

    """
    source = os.path.join(get_installer_dir(), "src", PACKAGE_NAME)
    if not os.path.isdir(source):
        raise RuntimeError(
            "Could not find '{}'. Keep drag_and_drop_install.py at the "
            "repository root, next to the 'src' folder.".format(source)
        )

    scripts_dir = get_scripts_dir()
    os.makedirs(scripts_dir, exist_ok=True)

    target = copy_package(source, scripts_dir)
    user_setup = update_user_setup(scripts_dir)

    if scripts_dir not in sys.path:
        sys.path.append(scripts_dir)
    purge_modules()

    import pose_ghoster

    pose_ghoster.install()

    print("[Pose Ghoster] Package copied to: {}".format(target))
    print("[Pose Ghoster] Auto-install added to: {}".format(user_setup))
    cmds.confirmDialog(
        title="Pose Ghoster",
        message=(
            "Pose Ghoster is installed.\n\n"
            "The shelf is available now and will load on every Maya start."
        ),
        button=["OK"],
    )


# endregion

# ==========

# region Maya Entry Point


def onMayaDroppedPythonFile(*args) -> None:
    """Run the installer when the file is dropped in the Maya viewport.

    Args:
        *args: Unused arguments passed by Maya.

    Raises:
        Exception: Re-raised after showing an error dialog.

    """
    try:
        install()
    except Exception as error:
        cmds.confirmDialog(
            title="Pose Ghoster - Install failed",
            message=str(error),
            button=["OK"],
            icon="critical",
        )
        raise


# Allows running the file from the Script Editor as well
if __name__ == "__main__":
    onMayaDroppedPythonFile()


# endregion