"""Geometry extraction accuracy. Run with: mayapy -m pytest tests/test_snapshot.py
"""

# region Imports & Config

# python modules
import pytest

# dcc import
pytest.importorskip("maya.cmds")
import maya.standalone  # noqa: E402

CUBE_SHAPE = "|cube|cubeShape"

# endregion

# ==========

# region Fixtures & Helpers


@pytest.fixture(scope="module", autouse=True)
def maya_session():
    """Start and stop a standalone Maya session."""
    maya.standalone.initialize(name="python")
    yield
    maya.standalone.uninitialize()


@pytest.fixture()
def cube():
    """Create a fresh scene with one cube."""
    from maya import cmds

    cmds.file(new=True, force=True)
    cmds.currentTime(1)
    return cmds.polyCube(name="cube")[0]


def _bake(frame):
    """Bake the cube shape at a frame."""
    from pose_ghoster.core import snapshot

    topo = snapshot.extract_topology(CUBE_SHAPE)
    return snapshot.bake_mesh(CUBE_SHAPE, frame, topo), topo


# endregion

# ==========

# region Tests


def test_resolve_and_topology(cube):
    """A cube resolves to one shape with 8 verts, 12 edges, 12 triangles."""
    from pose_ghoster.core import snapshot

    paths = snapshot.resolve_mesh_paths([cube])
    assert paths == [CUBE_SHAPE]
    topo = snapshot.extract_topology(paths[0])
    assert topo.num_vertices == 8
    assert len(topo.wire_indices) == 24 and len(topo.tri_indices) == 36


def test_bakes_future_frame_without_moving_timeline(cube):
    """Animated transforms are evaluated at the requested time only."""
    from maya import cmds

    cmds.setKeyframe(cube, attribute="translateX", t=1, v=0)
    cmds.setKeyframe(cube, attribute="translateX", t=10, v=9)
    s10, _ = _bake(10)
    s1, _ = _bake(1)
    assert max(p.x for p in s10.positions) == pytest.approx(9.5)
    assert max(p.x for p in s1.positions) == pytest.approx(0.5)
    assert cmds.currentTime(q=True) == 1


def test_captures_deformer_result_without_depending_on_it(cube):
    """The snapshot keeps the deformed pose and survives deformer deletion."""
    from maya import cmds

    _, handle = cmds.cluster(cube + ".vtx[*]")
    cmds.setKeyframe(handle, attribute="translateY", t=1, v=0)
    cmds.setKeyframe(handle, attribute="translateY", t=10, v=5)
    snap, _ = _bake(10)
    assert max(p.y for p in snap.positions) == pytest.approx(5.5)
    cmds.delete(handle)
    assert max(p.y for p in snap.positions) == pytest.approx(5.5)


def test_find_key_frames_auto_and_controller_override(cube):
    """Auto walks curves upstream of the mesh; sources restrict to controllers."""
    from maya import cmds
    from pose_ghoster.core import snapshot

    cmds.setKeyframe(cube, attribute="translateX", t=1, v=0)
    cmds.setKeyframe(cube, attribute="translateX", t=10, v=9)
    other = cmds.polyCube(name="other")[0]
    cmds.setKeyframe(other, attribute="translateY", t=5, v=1)
    assert snapshot.find_key_frames(CUBE_SHAPE) == [1.0, 10.0]
    assert snapshot.find_key_frames(CUBE_SHAPE, [other]) == [5.0]
    assert snapshot.find_key_frames(CUBE_SHAPE, [cube, other]) == [1.0, 5.0, 10.0]


def test_baking_creates_no_nodes(cube):
    """Baking leaves the scene untouched."""
    from maya import cmds

    before = set(cmds.ls())
    _bake(5)
    assert set(cmds.ls()) == before


# endregion
