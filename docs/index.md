# Pose Ghoster

**Pose Ghoster** is a GPU-drawn pose ghosting tool for Autodesk Maya (2022+).

Ghosts are cached world-space point arrays drawn through `MUIDrawManager` in Viewport 2.0. There are no duplicated meshes, no shaders, and no DAG node per ghost: a single hidden host locator carries the draw override.

## Features

- **Relative ghosts**: T-n in red, T+n in green, as a sliding window around the current frame, fully automatic.
- **Keys mode**: ghosts of the previous / next *keyed* poses (red / green), however far away they are. Key times are detected automatically from every animation curve upstream of the mesh (skin joints, constraints, IK, animation layers), or taken from controllers you choose.
- **Pinned ghosts**: deliberate poses (blue) with previous / next navigation. Pins are kept when keys change.
- **Display options**: wire-only (outline look) or tinted, with adjustable opacity.
- **Responsive by design**: ghosts are cached, baking is time-sliced, and ghosts are hidden during playback by default.
- **Status bar**: ghost count, memory use and bake status at a glance.

## How it works

```
Time change / anim edit ──► GhostManager ──► GhostCache ──► Draw override ──► GPU
        (Maya callbacks)    (what to bake)   (point arrays)  (replays arrays)
```

1. Maya callbacks (time, animation edits, selection, playback) notify the **manager**.
2. The manager decides which frames are needed and bakes only those missing from the **cache**.
3. The **draw override** replays the cached arrays through `MUIDrawManager`.

Camera and view transforms are never observed, so orbit, pan and zoom never trigger a recalculation.

## Project layout

```
pose-ghoster/
├── src/
│   └── pose_ghoster/
│       ├── core/          Manager, snapshot (OpenMaya 2.0), cache (pure Python)
│       ├── dcc/
│       │   └── maya/      Callbacks, draw override, locator (plugin), shelf,
│       │                  controller, launcher
│       └── ui/            Qt compatibility layer, DCC-agnostic controller contract,
│                          main window, theme, panel widgets
└── tests/                 Unit test suite
```

The window (`ui/`) has no DCC import, so it can be rebuilt in another DCC. See [Development](contributing.md#porting-the-ui-to-another-dcc).

## Requirements

| Requirement | Details |
|---|---|
| Maya | 2022 or newer, Viewport 2.0 |
| Python | 3.7+ (the interpreter shipped with Maya) |
| Qt | [Qt.py](https://github.com/mottosso/Qt.py) (falls back to PySide6 / PySide2 if missing) |
| Optional | `numpy`, used to build edge data faster on dense meshes |

## Next steps

- [Install the tool](installation.md)
- [Read the user guide](usage.md)
- [Tune performance](performance.md)

## License

Released under the **MIT License**. © 2026 Clement Daures.