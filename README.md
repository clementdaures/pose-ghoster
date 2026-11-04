# Pose Ghoster

**Pose Ghoster** is a GPU-drawn pose ghosting tool for Autodesk Maya (2022+). Ghosts are cached world-space point arrays drawn through `MUIDrawManager` in Viewport 2.0: no duplicates, no shaders, and no DAG node per ghost (one hidden host locator carries the draw override).

## Technical Highlights

* **Relative Ghosts:** T-n in red, T+n in green, as a sliding window, fully automatic.
* **Keys Mode:** Ghosts of the previous / next *keyed* poses (red / green), however far away they are. Key times are detected automatically from every animation curve upstream of the mesh (skin joints, constraints, IK, layers), or taken from controllers you choose (**Key source > Controllers**, **Auto** to go back).
* **Pinned Ghosts:** Deliberate poses (blue) with previous/next navigation, kept when keys change.
* **Display Options:** Wire-only (outline look) or tinted, with adjustable opacity.
* **Menus:** **Edit > Refresh** (F5) forces a resample; **Help** links to the docs, the author and bug reports. Ghost count, memory and bake status are shown in the status bar.

## Project Layout

```
pose-ghoster/
├── src/
│   └── pose_ghoster/
│       ├── core/          Manager, snapshot (OpenMaya 2.0), cache (pure Python)
│       ├── dcc/
│       │   └── maya/      Callbacks, draw override, locator (plugin), shelf, controller, launcher
│       └── ui/            Qt compatibility layer, DCC-agnostic controller contract,
│                          main window, theme (colors, stylesheet), panel widgets
└── tests/                 Unit test suite
```

The window (`ui/`) has no DCC import. To rebuild it in another DCC, copy `qt_compat.py`, `controller.py`, `main_window.py`, `theme/` and `widgets/`, then implement `PanelController` (see `dcc/maya/controller.py`). The stylesheet is set on the window only, never on the host application.

## Installation

### Option 1: Automatic Setup (Recommended for Artists)

1. Download or clone this repository.
2. Drag and drop the `drag_and_drop_install.py` file directly into your open Maya viewport.
3. Restart Maya. The tool will automatically initialize on startup, and a shelf will appear.

---

### Option 2: Direct Copy to Maya Scripts Directory

1. Copy the inner `pose_ghoster` directory (located inside `src/`) directly into your Maya user `scripts` directory:

* **Windows:** `%USERPROFILE%\Documents\maya\<version>\scripts\`  
  *(e.g., `C:\Users\<username>\Documents\maya\2025\scripts\pose_ghoster`)*
* **macOS:** `~/Library/Preferences/Autodesk/maya/<version>/scripts/`  
  *(e.g., `/Users/<username>/Library/Preferences/Autodesk/maya/2025/scripts/pose_ghoster`)*
* **Linux:** `~/maya/<version>/scripts/`  
  *(e.g., `/home/<username>/maya/2025/scripts/pose_ghoster`)*

2. Install Qt.py (not shipped with Maya):

```bash
mayapy -m pip install Qt.py --target "<your maya scripts folder>"
```

The UI falls back to PySide6/PySide2 directly if Qt.py is missing.

3. In the Maya Script Editor (Python):

```python
import pose_ghoster

pose_ghoster.install()   # Registers shelf & menu (optional)
pose_ghoster.show_ui()   # Opens control panel
```

### Option 3: Pipeline / Manual Setup (PYTHONPATH)

1. Add the **`src`** folder to your `PYTHONPATH` (e.g., in `Maya.env`):
   ```text
   PYTHONPATH=/path/to/pose-ghoster/src
   ```
2. Install Qt.py (not shipped with Maya):
   ```bash
   mayapy -m pip install Qt.py --target "<your maya scripts folder>"
   ```
   The UI falls back to PySide6/PySide2 directly if Qt.py is missing.
3. In the Maya Script Editor (Python):

```python
import pose_ghoster

pose_ghoster.install()   # Registers shelf & menu (optional)
pose_ghoster.show_ui()   # Opens control panel
```

To auto-install each session, add this to `scripts/userSetup.py`:

```python
import maya.utils

maya.utils.executeDeferred("import pose_ghoster; pose_ghoster.install()")
```

The locator plugin (`dcc/maya/locator.py`) loads itself by path when ghosting is switched on.

### Option 4: Rez Environment (For Studios & TDs)

If your facility uses Rez for environment configuration:

1. Build and release the package to your Rez repository:

```bash
rez build --install
```

2. Launch Maya within an environment containing pose_ghoster and maya:

```bash
rez env pose_ghoster maya -- maya
```

3. The package's `package.py` appends `src` to `PYTHONPATH` and handles initialization automatically via Maya setup hooks.

## Performance Guide

* **Ghost what you need.** Every mesh shape is baked and drawn separately. Selecting a whole rig can mean 100+ meshes; select the body or a low-res proxy instead. A **vertex budget** (default 250k, panel field *Max verts*) skips meshes beyond it, and the status line says how many.
* **Playback:** Ghosts are hidden while the timeline plays (zero work per frame) and rebuilt when it stops. *Freeze* keeps the last ghosts on screen, *Live* updates every frame (heavy).
* **Responsive scrubbing:** Baking is time-sliced (30 ms per refresh, nearest frames first, frame by frame across meshes). The rest finishes on idle, shown as *N pending* in the status line.
* **Cheaper ghosts:** Tint is off by default (wire only). *Keys* mode bakes only the neighbouring keyed poses and costs nothing while scrubbing between keys. Fewer past/future ghosts means fewer draws.
* Edge data is built with numpy when available (much faster on dense meshes).
* `MUIDrawManager` is immediate-mode: ghost geometry is sent to the GPU on every viewport redraw, including camera moves. Baking never reruns on camera moves, but heavy ghosts still cost GPU bandwidth. A retained-buffer renderer (`MPxSubSceneOverride`) is the next step.

## Evaluation Rules

| Event | Work done |
|---|---|
| Orbit / pan / zoom | None: the draw override replays cached arrays |
| Time change | Bakes only frames not already cached |
| Scrub between two keys (keys mode) | None: neither bakes nor key search |
| Animation curve / transform attribute edit | Relative ghosts + key lists dropped, rebuilt once (coalesced). Pins untouched |
| Opacity / fill / wire changes | Redraw only |
| Selection change (follow mode) | Old target released, new one baked |

**Limits:** Unkeyed edits on deep rig controls are not observed (press **Refresh**). Auto key detection walks the mesh history once per edit, which can take a moment on very heavy rigs: use a controller override there. Pins are not saved with the scene.

## Development & Testing

Using [`uv`](https://github.com/astral-sh/uv) for dependency management:

```bash
# Sync dependencies and install in editable mode
uv sync --extra dev

# Code formatting & linting
uv run black src tests
uv run ruff check src tests

# Run tests
uv run pytest tests/test_cache.py      # Standard Python environment
mayapy -m pytest tests/test_snapshot.py  # Maya Python interpreter
```

## Author & Contact

* **Clement Daures** - *Pipeline TD*
* **Website:** [clementdaures.com](https://clementdaures.com)

## Contributing

Bug reports, feature requests, and pull requests are welcome. Please consult [`CONTRIBUTING.md`](CONTRIBUTING.md) for commit conventions, branching strategies, and codebase organization guidelines before submitting code.

## License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute this software under the terms of the license. See the [`LICENSE`](LICENSE) file for the full text.