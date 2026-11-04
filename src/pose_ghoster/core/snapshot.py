"""High-speed mesh baking with OpenMaya 2.0.

A snapshot is the final evaluated mesh at a frame reduced to raw arrays. It
holds no reference to deformers, history or any DG/DAG node, and baking adds
no node to the scene. Evaluation uses an MDGContext, so the current time is
never touched.
"""

# region Imports & Config

# python modules
from typing import Iterable, List, Optional

# dcc import
import maya.api.OpenMaya as om

# pose_ghoster modules
from pose_ghoster.core.cache import GhostSnapshot, Topology

# endregion

# ==========

# region Helpers


class TopologyChanged(RuntimeError):
    """Raised when a mesh no longer matches its cached topology."""


def _dag_path(name: str) -> om.MDagPath:
    sl = om.MSelectionList()
    sl.add(name)
    return sl.getDagPath(0)


# endregion

# ==========

# region Key Times


def find_key_frames(path: str, sources: Optional[Iterable[str]] = None) -> List[float]:
    """Collect the key times that define "keyed poses" for a mesh.

    With ``sources`` (controllers), only their own keys are used. Without,
    every animation curve upstream of the mesh and of its parent transforms
    is used (skin influences, constraints, IK, animation layers included).
    This walks the history once; the manager caches the result.

    Args:
        path (str): Full DAG path of the mesh shape.
        sources (Iterable[str], optional): Controller nodes overriding auto
            detection.

    Returns:
        list[float]: Sorted unique key times in UI time units.

    """
    from maya import cmds

    names = [s for s in (sources or []) if s]
    if names:
        times = cmds.keyframe(names, query=True, timeChange=True) or []
    else:
        dag = _dag_path(path)
        nodes = []
        while dag.length() > 0:
            nodes.append(dag.fullPathName())
            dag.pop()
        history = set()
        for node in nodes:
            history.update(cmds.listHistory(node, pruneDagObjects=False) or [])
        curves = cmds.ls(list(history), type="animCurve") or []
        times = cmds.keyframe(curves, query=True, timeChange=True) if curves else []
    return sorted({round(float(t), 4) for t in times or []})


# endregion

# ==========

# region Extraction


def resolve_mesh_paths(names: Iterable[str]) -> List[str]:
    """Expand transforms and groups to their non-intermediate meshes.

    Args:
        names (Iterable[str]): Node names or paths.

    Returns:
        list[str]: Unique full DAG paths of the meshes found.

    """
    out, seen = [], set()
    for name in names:
        try:
            dag = _dag_path(name)
        except Exception:
            continue
        found = []
        if dag.apiType() == om.MFn.kMesh:
            found.append(dag)
        else:
            it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)
            it.reset(dag, om.MItDag.kDepthFirst, om.MFn.kMesh)
            while not it.isDone():
                found.append(it.getPath())
                it.next()
        for path in found:
            if om.MFnDagNode(path).isIntermediateObject:
                continue
            full = path.fullPathName()
            if full not in seen:
                seen.add(full)
                out.append(full)
    return out


def _edges_numpy(counts, connected, num_vertices):
    """Unique edge index pairs from face data using numpy (fast path)."""
    import numpy as np

    counts = np.array(list(counts), dtype=np.int64)
    conn = np.array(list(connected), dtype=np.int64)
    starts = np.repeat(np.cumsum(counts) - counts, counts)
    size = np.repeat(counts, counts)
    nxt = starts + (np.arange(len(conn)) - starts + 1) % size
    lo = np.minimum(conn, conn[nxt])
    hi = np.maximum(conn, conn[nxt])
    unique = np.unique(lo * num_vertices + hi)
    wire = np.empty(len(unique) * 2, dtype=np.int64)
    wire[0::2] = unique // num_vertices
    wire[1::2] = unique % num_vertices
    return om.MUintArray(wire.tolist())


def extract_topology(path: str) -> Topology:
    """Build the edge and triangle index arrays of a mesh (done once).

    Edges are derived from the face data with numpy when it is available,
    which is far faster than iterating edges one by one on dense meshes.

    Args:
        path (str): Full DAG path of the mesh shape.

    Returns:
        Topology: Shared index data.

    """
    dag = _dag_path(path)
    fn = om.MFnMesh(dag)
    _, tri_ids = fn.getTriangles()
    tris = om.MUintArray(list(tri_ids))

    try:
        counts, connected = fn.getVertices()
        wire = _edges_numpy(counts, connected, fn.numVertices)
    except ImportError:
        wire = om.MUintArray()
        it = om.MItMeshEdge(dag)
        while not it.isDone():
            wire.append(it.vertexId(0))
            wire.append(it.vertexId(1))
            it.next()
    return Topology(
        num_vertices=fn.numVertices,
        wire_indices=wire,
        tri_indices=tris,
        nbytes=(len(wire) + len(tris)) * 4,
    )


def bake_mesh(
    path: str, frame: float, topology: Topology, pinned: bool = False
) -> GhostSnapshot:
    """Evaluate a mesh at a frame and return a detached snapshot.

    Args:
        path (str): Full DAG path of the mesh shape.
        frame (float): Frame to evaluate, in UI time units.
        topology (Topology): Topology previously extracted for this mesh.
        pinned (bool): Flag the snapshot as a pinned pose.

    Returns:
        GhostSnapshot: World-space points at that frame.

    Raises:
        TopologyChanged: If the vertex count differs from ``topology``.

    """
    dag = _dag_path(path)
    ctx = om.MDGContext(om.MTime(float(frame), om.MTime.uiUnit()))
    dep = om.MFnDependencyNode(dag.node())

    # outMesh is the final deformed result at that time.
    mesh_obj = dep.findPlug("outMesh", False).asMObject(ctx)
    local_pts = om.MFnMesh(mesh_obj).getPoints(om.MSpace.kObject)
    if len(local_pts) != topology.num_vertices:
        raise TopologyChanged(path)

    # Context-aware world matrix (MDagPath.inclusiveMatrix ignores contexts).
    wm = dep.findPlug("worldMatrix", False).elementByLogicalIndex(dag.instanceNumber())
    matrix = om.MFnMatrixData(wm.asMObject(ctx)).matrix()
    if matrix.isEquivalent(om.MMatrix.kIdentity):
        world = local_pts
    else:
        world = om.MPointArray([p * matrix for p in local_pts])

    return GhostSnapshot(
        target=path,
        frame=float(frame),
        positions=world,
        topology=topology,
        pinned=pinned,
        nbytes=len(world) * 32,
    )


# endregion
