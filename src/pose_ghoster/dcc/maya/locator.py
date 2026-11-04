"""Host locator for the draw override, also loadable as a Maya plugin.

Viewport 2.0 only runs a draw override for a DAG node, so one hidden utility
locator carries the whole system. Ghosts themselves are never nodes. The shelf
loads this file by path, so no MAYA_PLUG_IN_PATH setup is needed.
"""

# region Imports & Config

# dcc import
import maya.api.OpenMaya as om
import maya.api.OpenMayaRender as omr
import maya.api.OpenMayaUI as omui

# pose_ghoster modules (absolute: this file may be loaded as a plugin)
from pose_ghoster import __version__
from pose_ghoster.dcc.maya.draw_override import GhostDrawOverride

NODE_NAME = "poseGhosterLocator"
NODE_ID = om.MTypeId(0x0007F5A1)  # local development range
CLASSIFICATION = "drawdb/geometry/poseGhoster"
HOST_TRANSFORM = "poseGhoster_LOC"

# endregion

# ==========

# region Plugin Node


def maya_useNewAPI() -> None:
    """Tell Maya this plugin uses OpenMaya API 2.0."""


class PoseGhosterLocator(omui.MPxLocatorNode):
    """Empty locator whose only job is to host the draw override."""

    @staticmethod
    def creator() -> "PoseGhosterLocator":
        """Create a node instance for Maya.

        Returns:
            PoseGhosterLocator: New node.

        """
        return PoseGhosterLocator()

    @staticmethod
    def initialize() -> None:
        """Declare node attributes (none needed)."""

    def excludeAsLocator(self) -> bool:
        """Disable ghost toggling in animator viewport"""
        return False


def initializePlugin(plugin: om.MObject) -> None:
    """Register the locator node and its draw override.

    Args:
        plugin (om.MObject): Plugin handle supplied by Maya.

    """
    fn = om.MFnPlugin(plugin, "PoseGhoster", __version__, "Any")
    fn.registerNode(
        NODE_NAME,
        NODE_ID,
        PoseGhosterLocator.creator,
        PoseGhosterLocator.initialize,
        om.MPxNode.kLocatorNode,
        CLASSIFICATION,
    )
    omr.MDrawRegistry.registerDrawOverrideCreator(
        CLASSIFICATION, GhostDrawOverride.NAME, GhostDrawOverride.creator
    )


def uninitializePlugin(plugin: om.MObject) -> None:
    """Deregister the draw override and the locator node.

    Args:
        plugin (om.MObject): Plugin handle supplied by Maya.

    """
    fn = om.MFnPlugin(plugin)
    omr.MDrawRegistry.deregisterDrawOverrideCreator(
        CLASSIFICATION, GhostDrawOverride.NAME
    )
    fn.deregisterNode(NODE_ID)


# endregion

# ==========

# region Scene Helpers


def ensure_plugin_loaded() -> None:
    """Load this file as a Maya plugin (no-op when already loaded)."""
    from maya import cmds

    cmds.loadPlugin(__file__, quiet=True)


def ensure_locator() -> str:
    """Return the host locator shape, creating it when missing.

    Returns:
        str: Full path of the locator shape.

    """
    from maya import cmds

    existing = cmds.ls(type=NODE_NAME, long=True)
    if existing:
        return existing[0]
    xf = cmds.createNode("transform", name=HOST_TRANSFORM)
    shape = cmds.createNode(NODE_NAME, parent=xf, name=HOST_TRANSFORM + "Shape")
    cmds.setAttr(xf + ".hiddenInOutliner", 1)
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideDisplayType", 2)
    return cmds.ls(shape, long=True)[0]


def remove_locator() -> None:
    """Delete every host locator (and its transform) from the scene."""
    from maya import cmds

    for shape in cmds.ls(type=NODE_NAME, long=True) or []:
        parent = cmds.listRelatives(shape, parent=True, fullPath=True)
        cmds.delete(parent[0] if parent else shape)


# endregion
