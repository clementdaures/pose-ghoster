# Performance

Pose Ghoster is designed so that ghosts cost as little as possible while you animate. This page explains what is expensive, what is free, and how to tune it.

## Ghost what you need

Every mesh shape is baked and drawn separately. Selecting a whole rig can mean 100+ meshes.

- Select the **body** or a **low-res proxy** instead of the full rig.
- Use the **Max verts (k)** field to cap the total vertex count. The default is **250k**. Meshes beyond the budget are skipped and the status line tells you how many (`N meshes skipped (budget)`).
- Set it to `0` for no limit (not recommended on heavy scenes).

## Playback

| Mode | Cost |
|---|---|
| **Hide during playback** (default) | Zero work per frame. Ghosts are rebuilt once when playback stops. |
| **Freeze during playback** | Zero work per frame. The last ghosts stay on screen. |
| **Live during playback** | Bakes on every frame. Heavy. |

## Responsive scrubbing

Baking is **time-sliced**:

- Each refresh gets a budget of **30 ms** (`bake_time_ms`).
- Missing frames are baked **nearest first**, and frame by frame across all meshes.
- Whatever does not fit is finished on idle. The status line shows it as `N pending`.

## Cheaper ghosts

- **Wire only** (the default): tint is off, which draws far less geometry.
- **Keys mode** bakes only the neighbouring keyed poses and costs **nothing** while you scrub between two keys.
- **Fewer past / future ghosts** means fewer bakes and fewer draw calls.
- A larger **Step** spreads the same number of ghosts over a wider window without adding more.
- **Install numpy**: edge data is built with numpy when it is available, which is much faster on dense meshes.

## What is free, what is not

| Event | Work done |
|---|---|
| Orbit / pan / zoom | None. The draw override replays cached arrays. |
| Time change | Bakes only frames not already cached. |
| Scrub between two keys (Keys mode) | None. Neither baking nor key search. |
| Animation curve / transform attribute edit | Relative ghosts and key lists are dropped and rebuilt once (coalesced). Pins are untouched. |
| Opacity / fill / wire changes | Redraw only. |
| Selection change (follow mode) | Old target released, new one baked. |

### The golden evaluation rule

Geometry is recomputed **only** from two events: a time change and an animation edit. The draw override reads pre-built arrays and nothing else. Camera and view transforms are never observed, so viewport navigation never reruns a bake.

## Memory

- Relative ghosts (T-n / T+n and keyed poses) live in an LRU cache with a **256 MB** budget by default. The oldest entries are evicted first.
- Pinned ghosts are kept until you delete them.
- Topology (index data) is shared between all snapshots of a mesh.
- Stopping ghosting, or closing the panel, **releases every cached array**.
- The status bar shows the current memory use.

## GPU cost

`MUIDrawManager` is immediate-mode: ghost geometry is sent to the GPU on **every viewport redraw**, including camera moves. Baking never reruns on camera moves, but heavy ghosts still cost GPU bandwidth.

A retained-buffer renderer based on `MPxSubSceneOverride` is the planned next step to remove this cost.

## Troubleshooting slow scenes

| Symptom | Try |
|---|---|
| Viewport is slow while orbiting | Reduce the number of ghosts, lower the vertex budget, or switch Fill off. |
| Scrubbing is laggy | Ghost a lighter mesh or proxy. Check for a high `N pending` count. |
| Lag after every animation edit | Switch to Keys mode with a **controller override**, to avoid walking the mesh history. |
| Playback stutters | Use **Hide** or **Freeze** instead of **Live**. |
| Memory keeps growing | Reduce ghost counts, or switch ghosting off and on to release the cache. |
| Some meshes are missing | They exceed the vertex budget. Raise **Max verts**, or ghost fewer meshes. |