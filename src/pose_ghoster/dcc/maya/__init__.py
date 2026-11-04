"""Maya integration entry points.
"""

# region Imports & Config

# python modules
from typing import List, Optional

_callbacks = None

# endregion

# ==========

# region Activation


def is_active() -> bool:
    """Tell whether ghosting is running.

    Returns:
        bool: True while active.

    """
    from pose_ghoster.core.manager import GhostManager

    return GhostManager.instance().active


def activate(nodes: Optional[List[str]] = None, follow_selection: bool = True) -> bool:
    """Load the plugin, create the host locator, add listeners, start ghosting.

    Args:
        nodes (list[str], optional): Meshes or groups to ghost. Explicit nodes
            disable selection following.
        follow_selection (bool): Retarget when the selection changes.

    Returns:
        bool: True once active.

    """
    global _callbacks
    from pose_ghoster.core.manager import GhostManager
    from pose_ghoster.dcc.maya import callbacks, locator

    locator.ensure_plugin_loaded()
    locator.ensure_locator()
    mgr = GhostManager.instance()
    mgr.configure_host(scheduler=callbacks.defer, redraw=callbacks.request_redraw)
    if _callbacks is None:
        _callbacks = callbacks.MayaCallbacks(mgr)
    _callbacks.register()
    return mgr.activate(nodes=nodes, follow_selection=follow_selection and not nodes)


def deactivate() -> None:
    """Stop ghosting: release the cache, remove listeners and the locator."""
    global _callbacks
    from pose_ghoster.core.manager import GhostManager

    GhostManager.instance().deactivate()
    if _callbacks is not None:
        _callbacks.unregister()
        _callbacks = None
    try:
        from pose_ghoster.dcc.maya import locator

        locator.remove_locator()
    except Exception:
        pass


# endregion
