"""Maya listeners: time, animation edits, selection and scene lifecycle only.

Camera and view transforms are deliberately not observed anywhere, which is
what guarantees that viewport navigation never recalculates ghosts.
"""

# region Imports & Config

# python modules
from typing import Callable, List, Tuple

# dcc import
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

# pose_ghoster modules
from pose_ghoster.core.manager import GhostManager

# endregion

# ==========

# region Helpers


def request_redraw() -> None:
    """Ask every viewport to refresh on its next idle."""
    try:
        import maya.OpenMayaUI as omui1

        omui1.M3dView.scheduleRefreshAllViews()
    except Exception:
        pass


def defer(fn: Callable) -> None:
    """Run a callable when Maya is idle.

    Args:
        fn (callable): Function to run.

    """
    from maya import utils

    utils.executeDeferred(fn)


# endregion

# ==========

# region Callback Registry


class MayaCallbacks:
    """Registers and removes every Maya listener used by the tool.

    Args:
        manager (GhostManager): Manager receiving the events.

    """

    def __init__(self, manager: GhostManager) -> None:
        self._mgr = manager
        self._ids: List[int] = []
        self._node_ids: List[int] = []
        self._watched: Tuple[str, ...] = ()

    def register(self) -> None:
        """Install the listeners (no-op if already installed)."""
        if self._ids:
            return
        m = self._mgr
        self._ids.append(
            om.MDGMessage.addTimeChangeCallback(lambda *_: m.on_time_changed())
        )
        try:
            self._ids.append(
                oma.MAnimMessage.addAnimCurveEditedCallback(
                    lambda *_: m.on_keyframes_changed()
                )
            )
        except Exception as exc:
            om.MGlobal.displayWarning(f"PoseGhoster: animCurve callback: {exc}")
        self._ids.append(
            om.MEventMessage.addEventCallback(
                "SelectionChanged", lambda *_: m.on_selection_changed()
            )
        )
        try:
            self._ids.append(
                om.MConditionMessage.addConditionCallback(
                    "playingBack", lambda state, *_: m.set_playing(state)
                )
            )
            m.set_playing(om.MConditionMessage.getConditionState("playingBack"))
        except Exception as exc:
            om.MGlobal.displayWarning(f"PoseGhoster: playback callback: {exc}")
        for msg in (
            om.MSceneMessage.kBeforeNew,
            om.MSceneMessage.kBeforeOpen,
            om.MSceneMessage.kMayaExiting,
        ):
            self._ids.append(om.MSceneMessage.addCallback(msg, self._on_scene_change))
        m.add_listener(self._on_manager_update)

    def unregister(self) -> None:
        """Remove every listener."""
        self._mgr.remove_listener(self._on_manager_update)
        for cb in self._ids + self._node_ids:
            try:
                om.MMessage.removeCallback(cb)
            except Exception:
                pass
        self._ids, self._node_ids, self._watched = [], [], ()

    def _on_scene_change(self, *_) -> None:
        from pose_ghoster.dcc import maya as dcc

        dcc.deactivate()

    def _on_manager_update(self, mgr: GhostManager) -> None:
        targets = tuple(mgr.targets)
        if targets != self._watched:
            self._rewatch(targets)

    def _rewatch(self, targets: Tuple[str, ...]) -> None:
        """Watch plain attribute edits on the ghosted meshes' transforms."""
        for cb in self._node_ids:
            try:
                om.MMessage.removeCallback(cb)
            except Exception:
                pass
        self._node_ids = []
        self._watched = targets
        for path in targets:
            try:
                sl = om.MSelectionList()
                sl.add(path)
                dag = sl.getDagPath(0)
                dag.pop()
                self._node_ids.append(
                    om.MNodeMessage.addAttributeChangedCallback(
                        dag.node(), self._on_attr
                    )
                )
            except Exception:
                continue

    def _on_attr(self, msg, plug, other, *_) -> None:
        if msg & om.MNodeMessage.kAttributeSet:
            self._mgr.on_keyframes_changed()


# endregion
