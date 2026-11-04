"""Controller contract between the Qt panel and any DCC backend.

The panel talks only to this interface, so it can be rebuilt in another DCC
(or in a bare Qt app) by implementing these methods. No Qt, no Maya here.
"""

# region Imports & Config

# python modules
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional

# endregion

# ==========

# region Controller Interface


class PanelController(ABC):
    """Operations the panel needs from its host."""

    @abstractmethod
    def is_active(self) -> bool:
        """Tell whether ghosting is running.

        Returns:
            bool: True while active.

        """

    @abstractmethod
    def activate(self, nodes: Optional[List[str]], follow_selection: bool) -> None:
        """Start ghosting.

        Args:
            nodes (list[str], optional): Explicit targets, or None.
            follow_selection (bool): Retarget on selection change.

        """

    @abstractmethod
    def deactivate(self) -> None:
        """Stop ghosting and release resources."""

    @abstractmethod
    def set_targets(self, nodes: List[str], follow: bool) -> None:
        """Change the ghosted nodes.

        Args:
            nodes (list[str]): New targets.
            follow (bool): Follow-selection state.

        """

    @abstractmethod
    def set_follow_selection(self, follow: bool) -> None:
        """Enable or disable selection following.

        Args:
            follow (bool): New state.

        """

    @abstractmethod
    def get_selection(self) -> List[str]:
        """Return the host's current selection.

        Returns:
            list[str]: Selected node paths.

        """

    @abstractmethod
    def get_settings(self) -> Any:
        """Return the settings object (attributes read by the panel).

        Returns:
            Any: Object exposing the GhostSettings fields.

        """

    @abstractmethod
    def set_settings(self, **kwargs: Any) -> None:
        """Update display settings.

        Args:
            **kwargs: Settings fields to change.

        """

    @abstractmethod
    def pin(self) -> None:
        """Pin the current pose."""

    @abstractmethod
    def update_pin(self) -> None:
        """Re-bake the pin on the current frame."""

    @abstractmethod
    def unpin(self) -> None:
        """Remove the pin on the current frame."""

    @abstractmethod
    def clear_pins(self) -> None:
        """Remove every pin."""

    @abstractmethod
    def go_to_pin(self, direction: int) -> None:
        """Jump to a neighbouring pin.

        Args:
            direction (int): -1 previous, +1 next.

        """

    @abstractmethod
    def set_key_sources(self, nodes: List[str]) -> None:
        """Override key detection with controllers (empty list = auto).

        Args:
            nodes (list[str]): Controller nodes.

        """

    @abstractmethod
    def refresh(self) -> None:
        """Force a resample."""

    @abstractmethod
    def status_text(self) -> str:
        """Return a one-line status.

        Returns:
            str: Human-readable status.

        """

    @abstractmethod
    def add_listener(self, fn: Callable) -> None:
        """Subscribe to state changes.

        Args:
            fn (callable): Called as ``fn(controller_or_manager)``.

        """

    @abstractmethod
    def remove_listener(self, fn: Callable) -> None:
        """Unsubscribe from state changes.

        Args:
            fn (callable): Previously added listener.

        """


# endregion
