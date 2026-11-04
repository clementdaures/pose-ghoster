# Pose Ghoster

GPU-drawn pose ghosts for Maya (2022+). Ghosts are cached world-space point arrays
drawn through `MUIDrawManager` in Viewport 2.0: no duplicates, no shaders, no DAG
node per ghost (one hidden host locator carries the draw override).

- **Relative ghosts**: T-n red, T+n green, sliding window, automatic.
- **Keys mode**: ghosts of the previous / next *keyed* poses (red / green), however far away they are.
  Key times are detected automatically from every animation curve upstream of the mesh
  (skin joints, constraints, IK, layers) or taken from controllers you choose
  (**Key source > Controllers**, **Auto** to go back).
- **Pinned ghosts**: deliberate poses (blue) with previous/next navigation; kept when keys change.
- **Display**: wire-only (outline look) or tinted, and opacity.
- **Menus**: **Edit > Refresh** (F5) forces a resample; **Help** links to the docs, the author and bug reports.
  The ghost count, memory and bake status is shown in the status bar.

## Layout

```
pose-ghoster/
  src/pose_ghoster/
    core/        manager, snapshot (OpenMaya 2.0), cache (pure Python)
    dcc/maya/    callbacks, draw_override, locator (plugin), shelf, controller, launcher
    ui/          qt_compat, controller (DCC-agnostic contract), main_window,
                 theme/ (colors, stylesheet), widgets/ (panel sections)
  tests/
```

The window (`ui/`) has no DCC import: to rebuild it in another DCC, copy `qt_compat.py`,
`controller.py`, `main_window.py`, `theme/` and `widgets/`, then implement `PanelController`
(see `dcc/maya/controller.py`). The stylesheet is set on the window only, never on the host application.

## Install

1. Add the **`src`** folder to Maya's path, e.g. in `Maya.env`:
   `PYTHONPATH=/path/to/pose-ghoster/src`
2. Install Qt.py (not shipped with Maya):
   `mayapy -m pip install Qt.py --target "<your maya scripts folder>"`
   (the UI falls back to PySide6/PySide2 directly if Qt.py is missing).
3. In the Script Editor (Python):

```python
import pose_ghoster
pose_ghoster.install()   # shelf + menu (optional)
pose_ghoster.show_ui()   # control panel
```

Auto-install each session, `scripts/userSetup.py`:

```python
import maya.utils
maya.utils.executeDeferred("import pose_ghoster; pose_ghoster.install()")
```

The locator plugin (`dcc/maya/locator.py`) loads itself by path when ghosting is switched on.

## Performance guide

- **Ghost what you need.** Every mesh shape is baked and drawn separately. Selecting a whole rig can
  mean 100+ meshes; select the body or a low-res proxy instead. A **vertex budget** (default 250k,
  panel field *Max verts*) skips meshes beyond it and the status line says how many.
- **Playback**: ghosts are hidden while the timeline plays (zero work per frame) and rebuilt when it
  stops. *Freeze* keeps the last ghosts on screen, *Live* updates every frame (heavy).
- **Responsive scrubbing**: baking is time-sliced (30 ms per refresh, nearest frames first, frame by
  frame across meshes); the rest finishes on idle, shown as *N pending* in the status line.
- **Cheaper ghosts**: tint is off by default (wire only). *Keys* mode bakes only the neighbouring keyed
  poses and costs nothing while scrubbing between keys. Fewer past/future ghosts means fewer draws.
- Edge data is built with numpy when available (much faster on dense meshes).
- `MUIDrawManager` is immediate-mode: ghost geometry is sent to the GPU on every viewport redraw,
  including camera moves. Baking never reruns on camera moves, but heavy ghosts still cost GPU
  bandwidth; a retained-buffer renderer (MPxSubSceneOverride) is the next step.

## Evaluation rules

| Event | Work done |
|---|---|
| Orbit / pan / zoom | None: the draw override replays cached arrays |
| Time change | Bakes only frames not already cached |
| Scrub between two keys (keys mode) | None: neither bakes nor key search |
| Animation curve / transform attribute edit | Relative ghosts + key lists dropped, rebuilt once (coalesced). Pins untouched |
| Opacity / fill / wire changes | Redraw only |
| Selection change (follow mode) | Old target released, new one baked |

Limits: unkeyed edits on deep rig controls are not observed (press **Refresh**). Auto key
detection walks the mesh history once per edit, which can take a moment on very heavy rigs:
use a controller override there. Pins are not saved with the scene.

## Development

```
pip install -e ".[dev]"
black src tests && ruff check src tests
pytest tests/test_cache.py                  # any Python
mayapy -m pytest tests/test_snapshot.py     # Maya interpreter
```