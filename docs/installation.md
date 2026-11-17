# Installation

Pose Ghoster supports Maya 2022+. Pick the option that fits your setup.

| Option | Best for |
|---|---|
| [1. Drag and drop](#option-1-drag-and-drop-recommended-for-artists) | Artists, single workstation |
| [2. Copy to scripts folder](#option-2-copy-to-the-maya-scripts-directory) | Manual install without a startup script |
| [3. PYTHONPATH](#option-3-pipeline-setup-pythonpath) | Pipelines and shared network installs |
| [4. Rez](#option-4-rez-environment-studios-and-tds) | Studios using Rez |

## Option 1: Drag and drop (recommended for artists)

1. Download or clone the repository.
2. Drag `drag_and_drop_install.py` into an open Maya viewport.
3. The installer shows a confirmation dialog. The shelf is available immediately, with no restart needed.

The installer:

1. Copies `src/pose_ghoster` into your Maya user `scripts` directory (replacing any older version).
2. Adds an auto-install block to `userSetup.py` (safe to re-run, it never duplicates the block).
3. Builds the shelf and the **Pose Ghoster** menu right away.

!!! note
    Keep `drag_and_drop_install.py` at the repository root, next to the `src` folder. It looks for `src/pose_ghoster` beside itself.

## Option 2: Copy to the Maya scripts directory

1. Copy the inner `pose_ghoster` folder (inside `src/`) into your Maya user `scripts` directory:

    | OS | Path |
    |---|---|
    | Windows | `%USERPROFILE%\Documents\maya\<version>\scripts\` |
    | macOS | `~/Library/Preferences/Autodesk/maya/<version>/scripts/` |
    | Linux | `~/maya/<version>/scripts/` |

    For example: `C:\Users\<username>\Documents\maya\2025\scripts\pose_ghoster`.

2. Install Qt.py (not shipped with Maya):

    ```bash
    mayapy -m pip install Qt.py --target "<your maya scripts folder>"
    ```

    The UI falls back to PySide6 / PySide2 directly if Qt.py is missing.

3. In the Maya Script Editor (Python tab):

    ```python
    import pose_ghoster

    pose_ghoster.install()   # Registers shelf & menu (optional)
    pose_ghoster.show_ui()   # Opens the control panel
    ```

## Option 3: Pipeline setup (PYTHONPATH)

1. Add the **`src`** folder to your `PYTHONPATH`, for example in `Maya.env`:

    ```text
    PYTHONPATH=/path/to/pose-ghoster/src
    ```

2. Install Qt.py (not shipped with Maya):

    ```bash
    mayapy -m pip install Qt.py --target "<your maya scripts folder>"
    ```

3. In the Maya Script Editor:

    ```python
    import pose_ghoster

    pose_ghoster.install()
    pose_ghoster.show_ui()
    ```

To install automatically at each session, add this to `scripts/userSetup.py`:

```python
import maya.utils

maya.utils.executeDeferred("import pose_ghoster; pose_ghoster.install()")
```

## Option 4: Rez environment (studios and TDs)

1. Build and release the package to your Rez repository:

    ```bash
    rez build --install
    ```

2. Launch Maya in an environment containing `pose_ghoster` and `maya`:

    ```bash
    rez env pose_ghoster maya -- maya
    ```

3. The package's `package.py` appends `src` to `PYTHONPATH` and handles initialization through Maya setup hooks.

## The locator plugin

Viewport 2.0 only runs a draw override for a DAG node, so Pose Ghoster uses one hidden utility locator (`poseGhosterLocator`) as a host. The plugin file (`dcc/maya/locator.py`) **loads itself by path** when ghosting is switched on, so no `MAYA_PLUG_IN_PATH` setup is required. The locator is deleted when ghosting is switched off.

## Verify the installation

After installing, you should see:

- A **PoseGhoster** shelf with two buttons: **Ghost UI** and **On/Off**.
- A **Pose Ghoster** menu in Maya's main menu bar.

Or check from the Script Editor:

```python
import pose_ghoster
print(pose_ghoster.__version__)
pose_ghoster.show_ui()
```

## Uninstall

```python
import pose_ghoster

pose_ghoster.uninstall()   # Stops ghosting, removes the shelf and the menu
```

Then delete the `pose_ghoster` folder from your scripts directory, and remove the block between the following markers in `userSetup.py`:

```python
# >>> pose_ghoster (auto-generated) >>>
...
# <<< pose_ghoster (auto-generated) <<<
```

## Troubleshooting


#### **Question:** "Dragging the installer does nothing"
Make sure you drop `drag_and_drop_install.py` onto the **3D viewport**, and that the file still sits next to the `src` folder. Alternatively, open it in the Script Editor and run it.

#### **Question:** "I updated the files but still get the old behavior"
Maya caches imported modules. Restart Maya, or re-run the drag-and-drop installer, which purges stale `pose_ghoster` modules before reloading.