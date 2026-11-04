"""Viewport 2.0 draw override pushing cached ghosts to the GPU.

Ghosts are drawn through MUIDrawManager. This class never calls the manager's
sampling API: prepareForDraw compares an integer version and addUIDrawables
replays pre-built arrays, so orbit, pan and zoom cost no recalculation.
"""

# region Imports & Config

# dcc import
import maya.api.OpenMaya as om
import maya.api.OpenMayaRender as omr

# pose_ghoster modules
from pose_ghoster.core.manager import GhostManager

FILL_ALPHA_SCALE = 0.35

# endregion

# ==========

# region Draw Override


def maya_useNewAPI() -> None:
    """Tell Maya this module uses OpenMaya API 2.0."""


class GhostDrawData(om.MUserData):
    """Per-draw data kept between refreshes (deleteAfterUse is False)."""

    def __init__(self) -> None:
        super().__init__(False)
        self.version = -1
        self.items = []
        self.show_fill = True
        self.show_wire = True
        self.line_width = 1.0


class GhostDrawOverride(omr.MPxDrawOverride):
    """Draws the manager's DrawItems as wireframe plus translucent tint.

    Args:
        obj (om.MObject): The host locator node.

    """

    NAME = "poseGhosterDrawOverride"

    @staticmethod
    def creator(obj: om.MObject) -> "GhostDrawOverride":
        """Create an override instance for Maya's draw registry.

        Args:
            obj (om.MObject): The host locator node.

        Returns:
            GhostDrawOverride: New override.

        """
        return GhostDrawOverride(obj)

    def __init__(self, obj: om.MObject) -> None:
        # isAlwaysDirty=True: called every refresh, but each call is O(1).
        super().__init__(obj, None, True)

    def supportedDrawAPIs(self) -> int:
        """Return the supported draw APIs.

        Returns:
            int: omr.MRenderer.kAllDevices.

        """
        return omr.MRenderer.kAllDevices

    def isBounded(self, obj_path, camera_path) -> bool:
        """Report the node as unbounded so it is never frustum-culled.

        Returns:
            bool: Always False.

        """
        return False

    def boundingBox(self, obj_path, camera_path) -> om.MBoundingBox:
        """Return an empty bounding box (unused, see isBounded).

        Returns:
            om.MBoundingBox: Empty box.

        """
        return om.MBoundingBox()

    def hasUIDrawables(self) -> bool:
        """Enable addUIDrawables.

        Returns:
            bool: Always True.

        """
        return True

    def prepareForDraw(self, obj_path, camera_path, frame_context, old_data):
        """Refresh the draw data only if the manager's version changed.

        Returns:
            GhostDrawData: Data passed to addUIDrawables.

        """
        data = old_data if isinstance(old_data, GhostDrawData) else GhostDrawData()
        mgr = GhostManager.instance()
        if data.version != mgr.version:
            data.items = mgr.draw_items
            data.version = mgr.version
        s = mgr.settings
        data.show_fill = s.show_fill
        data.show_wire = s.show_wire
        data.line_width = s.line_width
        return data

    def addUIDrawables(self, obj_path, draw_manager, frame_context, data) -> None:
        """Issue the immediate draw calls for every cached ghost."""
        if not isinstance(data, GhostDrawData) or not data.items:
            return
        draw_manager.beginDrawable()
        draw_manager.setLineWidth(data.line_width)
        for item in data.items:
            r, g, b, a = item.color
            if data.show_fill and len(item.tri_indices):
                draw_manager.setColor(om.MColor((r, g, b, a * FILL_ALPHA_SCALE)))
                draw_manager.mesh(
                    omr.MUIDrawManager.kTriangles,
                    item.positions,
                    None,
                    None,
                    item.tri_indices,
                )
            if data.show_wire and len(item.wire_indices):
                draw_manager.setColor(om.MColor((r, g, b, a)))
                draw_manager.mesh(
                    omr.MUIDrawManager.kLines,
                    item.positions,
                    None,
                    None,
                    item.wire_indices,
                )
        draw_manager.endDrawable()


# endregion
