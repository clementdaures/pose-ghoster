"""In-memory ghost cache.

Pure Python (no Maya imports) so it is fully unit-testable. Relative ghosts
(T-n / T+n and keyed poses) live in a byte-budgeted LRU; pinned ghosts
survive keyframe edits. Key-time lists are cached per mesh.
"""

# region Imports & Config

# python modules
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

Key = Tuple[str, float]

# endregion

# ==========

# region Data Models


@dataclass
class Topology:
    """Static per-mesh index data shared by every snapshot of that mesh.

    Args:
        num_vertices (int): Vertex count the indices refer to.
        wire_indices (Any): MUintArray of vertex pairs (kLines).
        tri_indices (Any): MUintArray of vertex triples (kTriangles).
        nbytes (int): Approximate memory footprint.

    """

    num_vertices: int
    wire_indices: Any
    tri_indices: Any
    nbytes: int = 0


@dataclass
class GhostSnapshot:
    """World-space vertex positions of one mesh at one frame.

    Args:
        target (str): Full DAG path of the mesh.
        frame (float): Frame the points were evaluated at.
        positions (Any): MPointArray in world space, detached from the DG.
        topology (Topology): Shared index data.
        pinned (bool): True for deliberate pinned poses.
        nbytes (int): Approximate memory footprint.

    """

    target: str
    frame: float
    positions: Any
    topology: Topology
    pinned: bool = False
    nbytes: int = 0


@dataclass
class CacheStats:
    """Counters exposed for diagnostics and tests."""

    hits: int = 0
    misses: int = 0
    bakes: int = 0
    evictions: int = 0
    invalidations: int = 0


# endregion

# ==========

# region Cache


class GhostCache:
    """Snapshot store with LRU eviction and explicit release.

    Args:
        max_bytes (int): Memory budget for relative ghosts.

    """

    def __init__(self, max_bytes: int = 256 * 1024 * 1024) -> None:
        self.max_bytes = max_bytes
        self.stats = CacheStats()
        self._relative: "OrderedDict[Key, GhostSnapshot]" = OrderedDict()
        self._pinned: Dict[Key, GhostSnapshot] = {}
        self._keys: Dict[str, List[float]] = {}
        self._topology: Dict[str, Topology] = {}
        self._bytes = 0

    # -- snapshots
    def get(
        self, target: str, frame: float, pinned: bool = False
    ) -> Optional[GhostSnapshot]:
        """Look up a snapshot.

        Args:
            target (str): Mesh path.
            frame (float): Frame number.
            pinned (bool): Search pinned ghosts instead of relative ones.

        Returns:
            GhostSnapshot: The snapshot, or None on a miss.

        """
        key = (target, float(frame))
        if pinned:
            snap = self._pinned.get(key)
        else:
            snap = self._relative.get(key)
            if snap is not None:
                self._relative.move_to_end(key)
        if snap is None:
            self.stats.misses += 1
        else:
            self.stats.hits += 1
        return snap

    def contains(self, target: str, frame: float) -> bool:
        """Tell whether a relative snapshot exists (no stats, no LRU touch).

        Args:
            target (str): Mesh path.
            frame (float): Frame number.

        Returns:
            bool: True if cached.

        """
        return (target, float(frame)) in self._relative

    def put(self, snap: GhostSnapshot) -> None:
        """Store a snapshot, replacing any existing one and evicting if needed.

        Args:
            snap (GhostSnapshot): Snapshot to store.

        """
        if snap.pinned:
            store = self._pinned
        else:
            store = self._relative
        key = (snap.target, float(snap.frame))
        old = store.pop(key, None)
        if old is not None:
            self._bytes -= old.nbytes
        store[key] = snap
        self._bytes += snap.nbytes
        if store is self._relative:
            self._evict()

    def record_bake(self) -> None:
        """Count one bake for diagnostics."""
        self.stats.bakes += 1

    def _evict(self) -> None:
        while self._bytes > self.max_bytes and self._relative:
            _, old = self._relative.popitem(last=False)
            self._bytes -= old.nbytes
            self.stats.evictions += 1

    # -- invalidation / release
    def invalidate_relative(self) -> int:
        """Drop relative ghosts and key lists (animation changed).

        Pins are kept.

        Returns:
            int: Number of snapshots dropped.

        """
        n = len(self._relative)
        self._bytes -= sum(s.nbytes for s in self._relative.values())
        self._relative.clear()
        self._keys.clear()
        self.stats.invalidations += n
        return n

    def invalidate_target(self, target: str) -> None:
        """Release everything held for one mesh (selection change).

        Args:
            target (str): Mesh path.

        """
        for store in (self._relative, self._pinned):
            for key in [k for k in store if k[0] == target]:
                self._bytes -= store.pop(key).nbytes
        self._topology.pop(target, None)
        self._keys.pop(target, None)

    def drop_pinned(
        self, frame: Optional[float] = None, target: Optional[str] = None
    ) -> int:
        """Remove pinned ghosts.

        Args:
            frame (float, optional): Only this frame. Defaults to all frames.
            target (str, optional): Only this mesh. Defaults to all meshes.

        Returns:
            int: Number of pins removed.

        """
        keys = [
            k
            for k in self._pinned
            if (frame is None or k[1] == float(frame))
            and (target is None or k[0] == target)
        ]
        for k in keys:
            self._bytes -= self._pinned.pop(k).nbytes
        return len(keys)

    def clear(self) -> None:
        """Drop every reference (tool deactivated)."""
        self._relative.clear()
        self._pinned.clear()
        self._keys.clear()
        self._topology.clear()
        self._bytes = 0

    # -- key times
    def keys(self, target: str) -> Optional[List[float]]:
        """Return the cached key times of a mesh, or None.

        Args:
            target (str): Mesh path.

        Returns:
            list[float]: Sorted key times, or None if not cached.

        """
        return self._keys.get(target)

    def set_keys(self, target: str, frames: List[float]) -> None:
        """Cache the key times of a mesh.

        Args:
            target (str): Mesh path.
            frames (list[float]): Key times.

        """
        self._keys[target] = sorted({round(float(f), 4) for f in frames})

    def clear_keys(self) -> None:
        """Forget every cached key list (key source changed)."""
        self._keys.clear()

    # -- topology
    def topology(self, target: str) -> Optional[Topology]:
        """Return the cached topology of a mesh, or None.

        Args:
            target (str): Mesh path.

        Returns:
            Topology: Cached index data, or None.

        """
        return self._topology.get(target)

    def set_topology(self, target: str, topo: Optional[Topology]) -> None:
        """Store (or with None, forget) the topology of a mesh.

        Args:
            target (str): Mesh path.
            topo (Topology, optional): Index data, or None to forget it.

        """
        if topo is None:
            self._topology.pop(target, None)
        else:
            self._topology[target] = topo

    # -- introspection
    def pinned_frames(self, target: Optional[str] = None) -> List[float]:
        """List pinned frames in ascending order.

        Args:
            target (str, optional): Restrict to one mesh.

        Returns:
            list[float]: Sorted frames.

        """
        return sorted({k[1] for k in self._pinned if target is None or k[0] == target})

    @property
    def size(self) -> int:
        """int: Number of cached snapshots (relative and pinned)."""
        return len(self._relative) + len(self._pinned)

    @property
    def memory_bytes(self) -> int:
        """int: Approximate total memory held."""
        return self._bytes + sum(t.nbytes for t in self._topology.values())


# endregion
