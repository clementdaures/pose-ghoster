"""Maya implementation of the panel controller.
"""

# region Imports & Config

# python modules
from typing import Any, Callable, List, Optional

# dcc import
from maya import cmds

# pose_ghoster modules
from pose_ghoster.core.manager import GhostManager
from pose_ghoster.dcc import maya as dcc
from pose_ghoster.ui.controller import PanelController

# endregion

# ==========

# region Controller


class MayaPanelController(PanelController):
    """Bridges the Qt panel to the GhostManager and Maya activation.

    Args:
        manager (GhostManager, optional): Manager to drive. Defaults to the
            shared instance.

    """

    def __init__(self, manager: Optional[GhostManager] = None) -> None:
        self.mgr = manager or GhostManager.instance()

    def is_active(self) -> bool:
        """Tell whether ghosting is running."""
        return self.mgr.active

    def activate(self, nodes: Optional[List[str]], follow_selection: bool) -> None:
        """Start ghosting through the Maya integration layer."""
        dcc.activate(nodes=nodes, follow_selection=follow_selection)

    def deactivate(self) -> None:
        """Stop ghosting and release resources."""
        dcc.deactivate()

    def set_targets(self, nodes: List[str], follow: bool) -> None:
        """Change the ghosted nodes."""
        self.mgr.set_targets(nodes, follow=follow)

    def set_follow_selection(self, follow: bool) -> None:
        """Enable or disable selection following."""
        self.mgr.follow_selection = follow
        if follow:
            self.mgr.on_selection_changed()

    def get_selection(self) -> List[str]:
        """Return the selected nodes as long names."""
        return cmds.ls(sl=True, long=True) or []

    def get_settings(self) -> Any:
        """Return the manager's GhostSettings."""
        return self.mgr.settings

    def set_settings(self, **kwargs: Any) -> None:
        """Update display settings."""
        self.mgr.set_settings(**kwargs)

    def pin(self) -> None:
        """Pin the current pose."""
        self.mgr.pin()

    def update_pin(self) -> None:
        """Re-bake the pin on the current frame."""
        self.mgr.update_pin()

    def unpin(self) -> None:
        """Remove the pin on the current frame."""
        self.mgr.unpin()

    def clear_pins(self) -> None:
        """Remove every pin."""
        self.mgr.clear_pins()

    def go_to_pin(self, direction: int) -> None:
        """Jump to the previous (-1) or next (+1) pin."""
        self.mgr.go_to_pin(direction)

    def set_key_sources(self, nodes: List[str]) -> None:
        """Override key detection with controllers (empty = auto)."""
        self.mgr.set_key_sources(nodes)

    def refresh(self) -> None:
        """Force a resample."""
        self.mgr.refresh()

    def status_text(self) -> str:
        """Return the manager's one-line status."""
        return self.mgr.describe()

    def add_listener(self, fn: Callable) -> None:
        """Subscribe to manager updates."""
        self.mgr.add_listener(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unsubscribe from manager updates."""
        self.mgr.remove_listener(fn)


# endregion
