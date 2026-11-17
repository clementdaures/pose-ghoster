# User Guide

## Opening the panel

Click **Ghost UI** on the PoseGhoster shelf, use the **Pose Ghoster** menu, or run:

```python
import pose_ghoster
pose_ghoster.show_ui()
```

The **On/Off** shelf button toggles ghosting without opening the panel.

!!! warning
    Closing the panel window also **stops ghosting** and releases every cached resource.

## Quick start

1. Select a mesh (or a group of meshes), for example the body of your character.
2. Click **Ghosting: OFF** to turn it **ON**.
3. Scrub the timeline. Past poses appear in red, future poses in green.
4. Press **Pin Pose** on a pose you want to keep as a reference. It stays in blue.

## The panel

The window is a stack of four sections, with actions in the menu bar and a status line at the bottom.

### Target

| Control | Description |
|---|---|
| **Ghosting: ON/OFF** | Starts or stops ghosting. |
| **Geo to ghost** | Comma-separated list of meshes or groups to ghost. Groups are expanded to their non-intermediate meshes. |
| **Add Geo** | Copies the current selection into *Geo to ghost* and turns **Follow selection** off. |
| **Follow selection** | When on, the ghosted target changes when you change the selection. Empty selections are ignored. |

### Ghosts

| Control | Description |
|---|---|
| **Mode** | `Relative (T-n / T+n)`, `Keys (previous / next keyed pose)` or `Off (pins only)`. |
| **Past / Future** | Number of ghosts before / after the current frame (Relative mode). Range 0 to 30. |
| **Step** | Frame spacing between relative ghosts. |
| **Prev keys / Next keys** | Number of previous / next keyed poses (Keys mode). Range 0 to 10. |
| **Key source** | Where key times come from in Keys mode. See [Key source](#key-source). |
| **Playback** | `Hide during playback (fastest)`, `Freeze during playback` or `Live during playback`. |
| **Max verts (k)** | Vertex budget in thousands (default 250). Meshes beyond it are skipped. |

### Display

| Control | Description |
|---|---|
| **Opacity** | Ghost opacity, 0 to 1 in steps of 0.1. |
| **Fill** | Draws a translucent tint on the ghost surface. Off by default. |
| **Wire** | Draws the wireframe. On by default. |

Wire only gives the lightest, outline look. Turn **Fill** on for a tinted silhouette.

### Pinned ghosts

| Button | Action |
|---|---|
| **Pin Pose** | Bakes a permanent ghost of the current frame. |
| **Update Pin** | Re-bakes the pin on the current frame (useful after changing the pose). |
| **<<< Previous Pin / Next Pin >>>** | Moves the timeline to the previous / next pinned frame. |
| **Delete Current Pin** | Removes the pin on the current frame. |
| **Delete All Pins** | Removes every pin. |
| **Show pins** | Shows or hides all pinned ghosts. |

### Menus and status bar

- **Edit > Refresh** (**F5**) forces a resample. Use it after unkeyed edits.
- **Help** opens the documentation, the author's website and the bug report link.
- The status bar shows the ghost count, memory used and number of bakes, for example `6 ghosts | 12.4 MB | 24 bakes`. It may append:
    - `N pending`: bakes still being finished on idle.
    - `N meshes skipped (budget)`: meshes over the vertex budget.
    - `playing`: ghosts are hidden or frozen during playback.

## Ghost modes

### Relative

Shows a sliding window around the current frame: `Past` ghosts in red at T-step, T-2·step…, and `Future` ghosts in green at T+step, T+2·step….

- Ghosts fade with distance from the current pose.
- The ghost on the current frame itself is skipped.

### Keys

Shows the previous and next *keyed* poses, however far away they are. Baking only happens for these neighbouring poses, and scrubbing between two keys costs **nothing**: neither baking nor key search.

#### Key source

- **Auto** (default): key times are collected from every animation curve upstream of the mesh and of its parent transforms. Skin influences, constraints, IK and animation layers are all included.
- **Controllers**: select your rig controls and click **Controllers** to use only their keys. You can also type controller names, separated by commas.
- Click **Auto** to go back to automatic detection.

!!! tip
    On very heavy rigs, automatic detection walks the mesh history once per edit and can take a moment. Use a controller override there.

### Off (pins only)

No relative ghosts are drawn. Only pinned ghosts remain visible.

## Pinned ghosts

Pins are deliberate reference poses, drawn in blue.

- They **survive keyframe edits**: changing animation does not drop them.
- Pinning the same frame again replaces the old pin.
- Use the previous / next buttons to jump between pinned frames.
- Pins are tied to the ghosted meshes. They are **not saved with the scene** and are released when ghosting stops.

## Playback behavior

| Mode | Behavior |
|---|---|
| **Hide** (default) | Ghosts disappear while the timeline plays (zero work per frame) and are rebuilt once when it stops. |
| **Freeze** | Keeps the last ghosts on screen during playback. |
| **Live** | Updates ghosts on every frame. Heavy on dense or multiple meshes. |

## When ghosts update

| Event | Behavior |
|---|---|
| Time change | Bakes only frames not already cached. |
| Animation curve edit or transform attribute edit | Relative ghosts and key lists are dropped, then rebuilt once. Pins are untouched. |
| Selection change (follow mode) | Old target is released, the new one is baked. |
| Scene new / open / Maya exit | Ghosting is switched off automatically. |

!!! note
    Unkeyed edits on deep rig controls are not observed. Press **Refresh** (F5) to resample.

## Python API

```python
import pose_ghoster

# Start ghosting the selection and follow it
pose_ghoster.activate()

# Ghost specific nodes (selection following is disabled)
pose_ghoster.activate(["|char_GRP|body_GEO"])

# Switch on/off
pose_ghoster.toggle()

# Stop and release everything
pose_ghoster.deactivate()

# UI and shelf
pose_ghoster.show_ui()
pose_ghoster.install()
pose_ghoster.uninstall()
```

| Function | Description |
|---|---|
| `activate(nodes=None, follow_selection=True)` | Starts ghosting. Defaults to the current selection. Returns `True` once active. |
| `deactivate()` | Stops ghosting, releases the cache and removes the locator. |
| `toggle()` | Switches ghosting on or off. |
| `show_ui()` | Opens the control panel. |
| `install()` / `uninstall()` | Builds / removes the shelf and menu. |

### Advanced settings

Some settings are not in the panel (ghost colors, line width, falloff, hiding on the current frame, bake time budget). They can be changed through the manager:

```python
from pose_ghoster.core.manager import GhostManager

mgr = GhostManager.instance()
mgr.set_settings(
    past_color=(1.0, 0.5, 0.0),
    future_color=(0.0, 0.8, 1.0),
    line_width=2.0,
    falloff=False,
)
```

| Setting | Default | Description |
|---|---|---|
| `mode` | `"relative"` | `"relative"`, `"keys"` or `"off"`. |
| `past_count` / `future_count` | 3 / 3 | Relative ghosts before / after. |
| `step` | 1 | Frame spacing between relative ghosts. |
| `key_past_count` / `key_future_count` | 1 / 1 | Keyed poses before / after. |
| `opacity` | 0.5 | Base opacity (0 to 1). |
| `show_fill` / `show_wire` | `False` / `True` | Tint and wireframe. |
| `falloff` | `True` | Fade ghosts with distance from the current pose. |
| `line_width` | 1.0 | Wireframe width in pixels. |
| `hide_on_current_frame` | `True` | Skip relative / pinned ghosts on the current frame. |
| `show_pins` | `True` | Draw pinned ghosts. |
| `past_color` | `(1.0, 0.25, 0.25)` | RGB of past ghosts. |
| `future_color` | `(0.25, 1.0, 0.35)` | RGB of future ghosts. |
| `pinned_color` | `(0.35, 0.65, 1.0)` | RGB of pinned ghosts. |
| `playback_mode` | `"hide"` | `"hide"`, `"freeze"` or `"live"`. |
| `bake_time_ms` | 30.0 | Time budget per refresh (0 = unlimited). |
| `max_vertices` | 250000 | Total vertex budget across ghosted meshes. |

## Limitations

- Unkeyed edits on deep rig controls are not observed. Press **Refresh**.
- Automatic key detection can take a moment on very heavy rigs. Use a controller override.
- Pins are not saved with the scene.
- Only polygon meshes are ghosted. Groups and transforms are expanded to the meshes they contain.
- If a mesh's topology changes, its cached data is rebuilt. A mesh that keeps failing to bake is dropped from the targets.