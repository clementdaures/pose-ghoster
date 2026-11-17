# Development

Bug reports, feature requests and pull requests are welcome.

## Getting started

Pose Ghoster uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
git clone <repository-url>
cd pose-ghoster

# Sync dependencies and install in editable mode
uv sync --extra dev
```

## Code style and checks

```bash
uv run black src tests        # Formatting
uv run ruff check src tests   # Linting
```

Both tools are configured in `pyproject.toml`: line length **88**, target **Python 3.7**. Ruff enforces the `E`, `F`, `W`, `B` rules and docstring formatting rules (`D2`, `D3`, `D4`).

Source files follow a consistent layout:

- Region markers (`# region ...` / `# endregion`) separated by `# ==========`.
- Google-style docstrings with `Args:`, `Returns:` and `Raises:`.
- Imports grouped as: python modules, dcc modules, pyside modules, `pose_ghoster` modules.

## Running the tests

```bash
# Pure Python tests (cache and manager logic, no Maya needed)
uv run pytest tests/test_cache.py

# Tests that need Maya's OpenMaya (run in Maya's interpreter)
mayapy -m pytest tests/test_snapshot.py
```

| File | Needs Maya | Covers |
|---|---|---|
| `tests/test_cache.py` | No | Cache behavior, LRU eviction, pins, and the evaluation rules of the manager (with a fake host). |
| `tests/test_snapshot.py` | Yes | Mesh extraction and baking with OpenMaya. |

## Architecture

### Package layout

| Package | Role | Maya imports |
|---|---|---|
| `core/manager.py` | Lifecycle, settings, frame planning, state machine. | None (host services are injected) |
| `core/cache.py` | Snapshot store, LRU eviction, pins, key and topology caches. | None |
| `core/snapshot.py` | Key detection, mesh resolution, topology extraction and baking (OpenMaya 2.0). | Yes |
| `dcc/maya/callbacks.py` | Time, animation, selection, playback and scene listeners. | Yes |
| `dcc/maya/locator.py` | Host locator, loadable as a Maya plugin. | Yes |
| `dcc/maya/draw_override.py` | Viewport 2.0 `MPxDrawOverride` using `MUIDrawManager`. | Yes |
| `dcc/maya/controller.py` | Maya implementation of the panel controller. | Yes |
| `dcc/maya/launcher.py` | Opens the window as a child of Maya's main window. | Yes |
| `dcc/maya/shelf.py` | Shelf and main menu. | Yes |
| `ui/` | Qt window, widgets, theme. DCC-agnostic. | None |

### Design rules

1. **Golden evaluation rule**: geometry is recomputed only from `on_time_changed` and `on_keyframes_changed`. The draw override never calls the sampling API; it compares an integer `version` and replays cached arrays.
2. **No camera callbacks**: viewport navigation must never trigger work.
3. **No node per ghost**: all ghosts are drawn by one hidden locator.
4. **Stay testable**: the manager and cache never import Maya. Maya services (time, selection, deferred execution, redraw, baking) are injected through `configure_host` and constructor arguments, which is how the tests run without Maya.
5. **Release everything on deactivate**: cache, draw items, callbacks and the locator.
6. **Scoped styling**: the stylesheet is set on the Pose Ghoster window only, never on the host application.

### Data flow

1. A callback calls `GhostManager.on_time_changed()` or `on_keyframes_changed()`.
2. `refresh()` plans the frames to show, bakes the missing ones within the time budget, and builds the list of `DrawItem` objects.
3. `version` is incremented and a viewport redraw is requested.
4. `GhostDrawOverride.prepareForDraw` sees the new `version` and picks up the items. `addUIDrawables` draws them.

## Porting the UI to another DCC

The window in `ui/` has no DCC import. To rebuild it in another DCC:

1. Copy `qt_compat.py`, `controller.py`, `main_window.py`, `theme/` and `widgets/`.
2. Implement the `PanelController` interface (see `dcc/maya/controller.py` for a reference implementation).
3. Create your window with `PoseGhosterWindow(YourController(), parent)`.

The controller must provide: activation (`is_active`, `activate`, `deactivate`), targeting (`set_targets`, `set_follow_selection`, `get_selection`), settings (`get_settings`, `set_settings`), pins (`pin`, `update_pin`, `unpin`, `clear_pins`, `go_to_pin`), `set_key_sources`, `refresh`, `status_text`, and the listener methods (`add_listener`, `remove_listener`).

## Submitting changes

1. Open an issue to discuss larger changes first.
2. Create a branch from `main`.
3. Make your change, with tests when it touches `core/`.
4. Run `black`, `ruff` and the tests (see above).
5. Open a pull request describing what changed and why.

!!! note
    Suggested conventions: short, imperative commit messages (for example `Fix pin update on empty selection`) and one topic per pull request. Adapt this section if your project uses a different convention.

## Reporting bugs

Please include:

- Maya version and operating system.
- Pose Ghoster version (`pose_ghoster.__version__`).
- Steps to reproduce, and whether the problem happens with a simple mesh.
- Any message from the Script Editor.

## Author

**Clement Daures**, Pipeline TD. [clementdaures.com](https://clementdaures.com)

## License

Released under the **MIT License**. See the `LICENSE` file for the full text.