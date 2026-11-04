"""Ghost lifecycle, frame sampling and state machine.

Golden Evaluation Rule: geometry is (re)computed only from on_time_changed and
on_keyframes_changed. The draw override reads draw_items and nothing else, so
orbit, pan and zoom never reach this module. Maya services (time, selection,
deferred execution, redraw) are injected through configure_host and default
lazily to OpenMaya, which keeps the manager unit-testable without Maya.
"""

# region Imports & Config

# python modules
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# pose_ghoster modules
from pose_ghoster.core.cache import GhostCache, GhostSnapshot, Topology

_WINDOW_KEYS = (
    "mode",
    "past_count",
    "future_count",
    "step",
    "key_past_count",
    "key_future_count",
    "show_pins",
)

# endregion

# ==========

# region Settings & Models


class GhostMode:
    """Where relative ghosts come from."""

    RELATIVE = "relative"
    KEYS = "keys"
    OFF = "off"


class PlaybackMode:
    """What ghosts do while the timeline is playing."""

    HIDE = "hide"
    FREEZE = "freeze"
    LIVE = "live"


class State:
    """Manager lifecycle states."""

    IDLE = "idle"
    ACTIVE = "active"


@dataclass
class GhostSettings:
    """User-facing display settings.

    Args:
        mode (str): One of GhostMode. RELATIVE shows T-n..T+n, KEYS shows the
            previous/next keyed poses, OFF shows only pins.
        past_count (int): Past ghosts in RELATIVE mode.
        future_count (int): Future ghosts in RELATIVE mode.
        step (int): Frame spacing between relative ghosts.
        key_past_count (int): Previous keyed poses in KEYS mode.
        key_future_count (int): Next keyed poses in KEYS mode.
        opacity (float): Base opacity, 0 to 1.
        show_fill (bool): Draw the translucent tint.
        show_wire (bool): Draw the wireframe (wire only = outline look).
        falloff (bool): Fade ghosts with distance from the current pose.
        line_width (float): Wireframe width in pixels.
        hide_on_current_frame (bool): Skip relative/pinned ghosts on the
            current frame.
        show_pins (bool): Draw pinned ghosts.
        past_color (tuple): RGB of past ghosts.
        future_color (tuple): RGB of future ghosts.
        pinned_color (tuple): RGB of pinned ghosts.
        playback_mode (str): One of PlaybackMode. HIDE removes ghosts during
            playback (zero cost), FREEZE keeps the last ones, LIVE updates.
        bake_time_ms (float): Time budget per refresh; remaining bakes are
            continued on idle so scrubbing stays responsive (0 = unlimited).
        max_vertices (int): Total vertex budget across ghosted meshes; meshes
            beyond it are skipped.

    """

    mode: str = GhostMode.RELATIVE
    past_count: int = 3
    future_count: int = 3
    step: int = 1
    key_past_count: int = 1
    key_future_count: int = 1
    opacity: float = 0.5
    show_fill: bool = False
    show_wire: bool = True
    falloff: bool = True
    line_width: float = 1.0
    hide_on_current_frame: bool = True
    show_pins: bool = True
    past_color: Tuple[float, float, float] = (1.0, 0.25, 0.25)
    future_color: Tuple[float, float, float] = (0.25, 1.0, 0.35)
    pinned_color: Tuple[float, float, float] = (0.35, 0.65, 1.0)
    playback_mode: str = PlaybackMode.HIDE
    bake_time_ms: float = 30.0
    max_vertices: int = 250000


@dataclass
class DrawItem:
    """One ready-to-draw ghost, consumed by the draw override.

    Args:
        positions (Any): World-space points.
        wire_indices (Any): Index pairs for lines.
        tri_indices (Any): Index triples for the tint.
        color (tuple): RGBA, alpha already includes opacity and falloff.
        frame (float): Source frame.
        kind (str): "past", "future" or "pinned".

    """

    positions: Any
    wire_indices: Any
    tri_indices: Any
    color: Tuple[float, float, float, float]
    frame: float
    kind: str


# endregion

# ==========

# region Manager


class GhostManager:
    """Owns targets, settings, the cache and the list of draw items.

    Args:
        cache (GhostCache, optional): Cache to use. Defaults to a new one.
        baker (callable, optional): ``baker(target, frame, topology, pinned)``.
        topology_extractor (callable, optional): ``extractor(target)``.
        resolver (callable, optional): ``resolver(names) -> list[str]``.
        key_finder (callable, optional): ``finder(target, sources) -> list[float]``.

    """

    _instance: Optional["GhostManager"] = None

    def __init__(
        self,
        cache: Optional[GhostCache] = None,
        baker: Optional[Callable] = None,
        topology_extractor: Optional[Callable] = None,
        resolver: Optional[Callable] = None,
        key_finder: Optional[Callable] = None,
    ) -> None:
        self.cache = cache or GhostCache()
        self.settings = GhostSettings()
        self.follow_selection = True
        self.version = 0
        self._baker = baker
        self._extract = topology_extractor
        self._resolve = resolver
        self._key_finder = key_finder
        self._key_sources: List[str] = []
        self._time_getter: Optional[Callable] = None
        self._time_setter: Optional[Callable] = None
        self._selection_getter: Optional[Callable] = None
        self._scheduler: Optional[Callable] = None
        self._redraw: Optional[Callable] = None
        self._state = State.IDLE
        self._targets: List[str] = []
        self._visible: List[Tuple[GhostSnapshot, str, int, int]] = []
        self._draw_items: List[DrawItem] = []
        self._last_time: Optional[float] = None
        self._refresh_pending = False
        self._continue_pending = False
        self._playing = False
        self._clock: Callable = time.perf_counter
        self._pending = 0
        self.skipped: List[str] = []
        self._failures: Dict[str, int] = {}
        self._listeners: List[Callable] = []

    # -- singleton
    @classmethod
    def instance(cls) -> "GhostManager":
        """Return the shared manager, creating it on first use.

        Returns:
            GhostManager: The process-wide instance.

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Deactivate and discard the shared manager."""
        if cls._instance is not None:
            cls._instance.deactivate()
        cls._instance = None

    # -- host hooks
    def configure_host(
        self,
        time_getter: Optional[Callable] = None,
        time_setter: Optional[Callable] = None,
        selection_getter: Optional[Callable] = None,
        scheduler: Optional[Callable] = None,
        redraw: Optional[Callable] = None,
        clock: Optional[Callable] = None,
    ) -> None:
        """Inject host services; omitted ones keep their current value.

        Args:
            time_getter (callable, optional): ``() -> float`` current frame.
            time_setter (callable, optional): ``(frame) -> None``.
            selection_getter (callable, optional): ``() -> list[str]``.
            scheduler (callable, optional): ``(fn) -> None`` deferred call.
            redraw (callable, optional): ``() -> None`` viewport refresh.
            clock (callable, optional): ``() -> float`` seconds (bake budgets).

        """
        if clock:
            self._clock = clock
        if time_getter:
            self._time_getter = time_getter
        if time_setter:
            self._time_setter = time_setter
        if selection_getter:
            self._selection_getter = selection_getter
        if scheduler:
            self._scheduler = scheduler
        if redraw:
            self._redraw = redraw

    def _now(self) -> float:
        if self._time_getter is None:
            from maya.api import OpenMayaAnim as oma

            self._time_getter = lambda: oma.MAnimControl.currentTime().value
        return float(self._time_getter())

    def _go_to(self, frame: float) -> None:
        if self._time_setter is None:
            from maya.api import OpenMaya as om
            from maya.api import OpenMayaAnim as oma

            self._time_setter = lambda f: oma.MAnimControl.setCurrentTime(
                om.MTime(f, om.MTime.uiUnit())
            )
        self._time_setter(frame)

    def _selection(self) -> List[str]:
        if self._selection_getter is None:
            from maya.api import OpenMaya as om

            self._selection_getter = lambda: list(
                om.MGlobal.getActiveSelectionList().getSelectionStrings()
            )
        return self._selection_getter()

    def _schedule(self, fn: Callable) -> None:
        (self._scheduler or (lambda f: f()))(fn)

    def _request_redraw(self) -> None:
        if self._redraw:
            self._redraw()

    def _do_resolve(self, names: List[str]) -> List[str]:
        if self._resolve is None:
            from pose_ghoster.core import snapshot

            self._resolve = snapshot.resolve_mesh_paths
        return self._resolve(names)

    def _do_extract(self, target: str) -> Topology:
        if self._extract is None:
            from pose_ghoster.core import snapshot

            self._extract = snapshot.extract_topology
        return self._extract(target)

    def _do_bake(
        self, target: str, frame: float, topo: Topology, pinned: bool
    ) -> GhostSnapshot:
        if self._baker is None:
            from pose_ghoster.core import snapshot

            self._baker = snapshot.bake_mesh
        return self._baker(target, frame, topo, pinned)

    def _do_find_keys(self, target: str) -> List[float]:
        if self._key_finder is None:
            from pose_ghoster.core import snapshot

            self._key_finder = snapshot.find_key_frames
        return self._key_finder(target, list(self._key_sources))

    # -- properties
    @property
    def active(self) -> bool:
        """bool: True while ghosting is running."""
        return self._state == State.ACTIVE

    @property
    def targets(self) -> List[str]:
        """list[str]: Full paths of the ghosted meshes."""
        return list(self._targets)

    @property
    def key_sources(self) -> List[str]:
        """list[str]: Controllers overriding key detection (empty = auto)."""
        return list(self._key_sources)

    @property
    def draw_items(self) -> List[DrawItem]:
        """list[DrawItem]: Read-only view for the draw override (no work done)."""
        return self._draw_items

    @property
    def pinned_frames(self) -> List[float]:
        """list[float]: Frames that currently hold a pinned ghost."""
        return self.cache.pinned_frames()

    # -- listeners
    def add_listener(self, fn: Callable) -> None:
        """Register a callback invoked as ``fn(manager)`` after state changes.

        Args:
            fn (callable): Listener.

        """
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        """Unregister a listener.

        Args:
            fn (callable): Listener previously added.

        """
        if fn in self._listeners:
            self._listeners.remove(fn)

    def _notify(self) -> None:
        for fn in list(self._listeners):
            try:
                fn(self)
            except Exception:
                self.remove_listener(fn)

    def describe(self) -> str:
        """Return a one-line status summary.

        Returns:
            str: Ghost count, memory use and bake count.

        """
        c = self.cache
        extra = ""
        if self._pending:
            extra += " | %d pending" % self._pending
        if self.skipped:
            extra += " | %d meshes skipped (budget)" % len(self.skipped)
        if self._playing and self.settings.playback_mode != PlaybackMode.LIVE:
            extra += " | playing"
        return "%d ghosts | %.1f MB | %d bakes%s" % (
            len(self._draw_items),
            c.memory_bytes / 1048576.0,
            c.stats.bakes,
            extra,
        )

    # -- lifecycle
    def activate(
        self,
        nodes: Optional[List[str]] = None,
        follow_selection: Optional[bool] = None,
    ) -> bool:
        """Start ghosting.

        Args:
            nodes (list[str], optional): Meshes or groups to ghost.
            follow_selection (bool, optional): Retarget on selection change.

        Returns:
            bool: True once active.

        """
        if follow_selection is not None:
            self.follow_selection = follow_selection
        self._state = State.ACTIVE
        if nodes:
            self.set_targets(nodes, refresh=False)
        elif self.follow_selection:
            self.on_selection_changed(refresh=False)
        self.refresh()
        return True

    def deactivate(self) -> None:
        """Stop ghosting and release every cached array and draw reference."""
        self._state = State.IDLE
        self._targets = []
        self._key_sources = []
        self._failures.clear()
        self._visible = []
        self._draw_items = []
        self._last_time = None
        self._refresh_pending = False
        self._continue_pending = False
        self._pending = 0
        self.skipped = []
        self.cache.clear()
        self.version += 1
        self._request_redraw()
        self._notify()

    def set_targets(
        self,
        nodes: List[str],
        follow: Optional[bool] = None,
        refresh: bool = True,
    ) -> bool:
        """Change the ghosted meshes, releasing the ones no longer used.

        Args:
            nodes (list[str]): Meshes or groups.
            follow (bool, optional): New follow-selection state.
            refresh (bool): Resample right away (False when the caller will).

        Returns:
            bool: False if no mesh was found (targets are left untouched).

        """
        paths = self._do_resolve(list(nodes))
        if not paths:
            return False
        if follow is not None:
            self.follow_selection = follow
        for old in set(self._targets) - set(paths):
            self.cache.invalidate_target(old)
        self._targets = list(paths)
        self._failures.clear()
        if self.active and refresh:
            self.refresh()
        return True

    def set_key_sources(self, nodes: Optional[List[str]]) -> None:
        """Override key detection with controllers (empty or None = auto).

        Args:
            nodes (list[str], optional): Controller nodes whose keys define
                the keyed poses.

        """
        self._key_sources = [n for n in (nodes or []) if n]
        self.cache.clear_keys()
        if self.active:
            self.refresh()

    def set_settings(self, **kwargs: Any) -> None:
        """Update display settings; only window changes trigger sampling.

        Args:
            **kwargs: Any GhostSettings field.

        Raises:
            AttributeError: If a key is not a GhostSettings field.

        """
        window_changed = False
        for key, value in kwargs.items():
            if not hasattr(self.settings, key):
                raise AttributeError(key)
            if getattr(self.settings, key) != value:
                setattr(self.settings, key, value)
                window_changed = window_changed or key in _WINDOW_KEYS
        if self.active:
            if window_changed:
                self.refresh()
            else:
                self._build_draw_items()
                self._notify()

    # -- the only entry points that may compute geometry
    def on_time_changed(self) -> None:
        """Timeline moved: bake only frames missing from the cache."""
        if not self.active or self._frozen():
            return
        if self._now() == self._last_time:
            return
        self.refresh()

    def on_keyframes_changed(self) -> None:
        """Animation edited: drop relative ghosts and key lists, resample once.

        Pins are deliberately kept.
        """
        if not self.active:
            return
        self.cache.invalidate_relative()
        if self._frozen():
            return
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self._schedule(self._flush)

    def _flush(self) -> None:
        self._refresh_pending = False
        self.refresh()

    def on_selection_changed(self, refresh: bool = True) -> None:
        """Retarget to the selection when following it (empty selections ignored).

        Args:
            refresh (bool): Resample right away (False when the caller will).

        """
        if not (self.active and self.follow_selection):
            return
        names = self._selection()
        if not names:
            return
        paths = self._do_resolve(names)
        if paths and paths != self._targets:
            self.set_targets(paths, refresh=refresh)

    def _frozen(self) -> bool:
        """True while playing in a mode that must do no work."""
        return self._playing and self.settings.playback_mode != PlaybackMode.LIVE

    def set_playing(self, playing: bool) -> None:
        """Tell the manager playback started or stopped.

        With HIDE the ghosts disappear for the duration of playback and no
        callback does any work; on stop everything is rebuilt once.

        Args:
            playing (bool): True while the timeline is playing.

        """
        playing = bool(playing)
        if playing == self._playing:
            return
        self._playing = playing
        if not self.active:
            return
        if playing:
            if self.settings.playback_mode == PlaybackMode.HIDE:
                self._draw_items = []
                self.version += 1
                self._request_redraw()
                self._notify()
        else:
            self.refresh()

    def _continue(self) -> None:
        self._continue_pending = False
        if self.active and not self._frozen() and self._last_time == self._now():
            self.refresh()

    def _active_targets(self) -> List[str]:
        """Apply the vertex budget; remember which meshes were skipped."""
        budget = int(self.settings.max_vertices)
        used, keep, skipped = 0, [], []
        for target in self._targets:
            topo = self._topology(target)
            if topo is None:
                self._fail(target)
                continue
            if budget > 0 and used + topo.num_vertices > budget:
                skipped.append(target)
                continue
            used += topo.num_vertices
            keep.append(target)
        self.skipped = skipped
        return keep

    def refresh(self) -> None:
        """Resample around the current frame, hitting the cache first.

        Missing frames are baked nearest-first and frame by frame across all
        meshes, within the time budget; the rest continues on idle.
        """
        if not self.active or self._frozen():
            return
        t = self._now()
        self._last_time = t
        s = self.settings
        targets = self._active_targets()
        plan = []
        for target in targets:
            for frame, kind, rank, count in self._relative_frames(target, t):
                plan.append((target, frame, kind, rank, count))
        missing = [p for p in plan if not self.cache.contains(p[0], p[1])]
        missing.sort(key=lambda p: (abs(p[1] - t), p[1]))
        self._bake_missing(missing)
        visible = []
        for target, frame, kind, rank, count in plan:
            snap = self.cache.get(target, frame)
            if snap is not None:
                visible.append((snap, kind, rank, count))
        for target in targets:
            if s.show_pins:
                for frame in self.cache.pinned_frames(target):
                    snap = self.cache.get(target, frame, pinned=True)
                    if snap is not None:
                        visible.append((snap, "pinned", 0, 0))
        for target in [x for x in self._targets if self._failures.get(x, 0) >= 3]:
            self._targets.remove(target)
            self.cache.invalidate_target(target)
        self._visible = visible
        self._build_draw_items()
        self._notify()

    def _bake_missing(self, missing: List[Tuple[Any, ...]]) -> None:
        """Bake within the time budget and schedule the rest on idle."""
        budget = float(self.settings.bake_time_ms) / 1000.0
        deadline = self._clock() + budget
        done = 0
        for target, frame, _kind, _rank, _count in missing:
            if budget > 0 and done and self._clock() >= deadline:
                break
            topo = self.cache.topology(target)
            if topo is not None and self._relative(target, frame, topo) is not None:
                done += 1
            elif topo is None:
                break
        self._pending = max(0, len(missing) - done)
        if self._pending and not self._continue_pending:
            self._continue_pending = True
            self._schedule(self._continue)

    def _relative_frames(
        self, target: str, t: float
    ) -> List[Tuple[float, str, int, int]]:
        """Return (frame, kind, rank, count) for the active mode."""
        s = self.settings
        out = []
        if s.mode == GhostMode.RELATIVE:
            for off in range(-s.past_count, 0):
                out.append((t + off * s.step, "past", -off, s.past_count))
            for off in range(1, s.future_count + 1):
                out.append((t + off * s.step, "future", off, s.future_count))
        elif s.mode == GhostMode.KEYS:
            keys = self._keys(target)
            lo = bisect_left(keys, t)
            hi = bisect_right(keys, t)
            past = keys[max(0, lo - s.key_past_count) : lo] if s.key_past_count else []
            future = keys[hi : hi + s.key_future_count]
            for rank, frame in enumerate(reversed(past), 1):
                out.append((frame, "past", rank, s.key_past_count))
            for rank, frame in enumerate(future, 1):
                out.append((frame, "future", rank, s.key_future_count))
        return out

    def _keys(self, target: str) -> List[float]:
        keys = self.cache.keys(target)
        if keys is None:
            try:
                keys = self._do_find_keys(target)
            except Exception:
                keys = []
            self.cache.set_keys(target, keys)
            keys = self.cache.keys(target)
        return keys

    def _topology(self, target: str) -> Optional[Topology]:
        topo = self.cache.topology(target)
        if topo is None:
            try:
                topo = self._do_extract(target)
            except Exception:
                return None
            self.cache.set_topology(target, topo)
        return topo

    def _relative(
        self, target: str, frame: float, topo: Topology
    ) -> Optional[GhostSnapshot]:
        snap = self.cache.get(target, frame)
        if snap is not None:
            return snap
        try:
            snap = self._do_bake(target, frame, topo, False)
        except Exception:
            self.cache.set_topology(target, None)
            self._fail(target)
            return None
        self._failures.pop(target, None)
        self.cache.record_bake()
        self.cache.put(snap)
        return snap

    def _fail(self, target: str) -> None:
        self._failures[target] = self._failures.get(target, 0) + 1

    def _build_draw_items(self) -> None:
        s, t = self.settings, self._last_time
        items = []
        for snap, kind, rank, count in self._visible:
            if kind in ("past", "future", "pinned"):
                if s.hide_on_current_frame and snap.frame == t:
                    continue
            rgb = {
                "past": s.past_color,
                "future": s.future_color,
            }.get(kind, s.pinned_color)
            alpha = s.opacity
            if kind in ("past", "future") and s.falloff and count > 1:
                alpha *= 1.0 - 0.65 * (rank - 1) / float(count - 1)
            items.append(
                DrawItem(
                    snap.positions,
                    snap.topology.wire_indices,
                    snap.topology.tri_indices,
                    tuple(rgb) + (alpha,),
                    snap.frame,
                    kind,
                )
            )
        self._draw_items = items
        self.version += 1
        self._request_redraw()

    # -- pinned ghosts
    def pin(self, frame: Optional[float] = None) -> int:
        """Bake a permanent ghost, replacing an existing pin on that frame.

        Args:
            frame (float, optional): Frame to pin. Defaults to the current one.

        Returns:
            int: Number of meshes pinned.

        """
        if not self.active:
            return 0
        t = self._now() if frame is None else float(frame)
        count = 0
        for target in self._targets:
            topo = self._topology(target)
            if topo is None:
                continue
            try:
                snap = self._do_bake(target, t, topo, True)
            except Exception:
                continue
            self.cache.record_bake()
            self.cache.put(snap)
            count += 1
        if count:
            self.refresh()
        return count

    def update_pin(self, frame: Optional[float] = None) -> int:
        """Re-bake the pin on a frame (alias of pin).

        Args:
            frame (float, optional): Frame to update. Defaults to the current one.

        Returns:
            int: Number of meshes pinned.

        """
        return self.pin(frame)

    def unpin(self, frame: Optional[float] = None) -> int:
        """Remove the pins on a frame.

        Args:
            frame (float, optional): Frame to clear. Defaults to the current one.

        Returns:
            int: Number of pins removed.

        """
        t = self._now() if frame is None else float(frame)
        n = self.cache.drop_pinned(frame=t)
        if n:
            self.refresh()
        return n

    def clear_pins(self) -> int:
        """Remove every pinned ghost.

        Returns:
            int: Number of pins removed.

        """
        n = self.cache.drop_pinned()
        if n:
            self.refresh()
        return n

    def go_to_pin(self, direction: int) -> Optional[float]:
        """Move the timeline to the previous or next pinned frame.

        Args:
            direction (int): -1 for previous, +1 for next.

        Returns:
            float: The frame reached, or None if there is no such pin.

        """
        t = self._now()
        cands = [
            f for f in self.cache.pinned_frames() if (f < t if direction < 0 else f > t)
        ]
        if not cands:
            return None
        target = max(cands) if direction < 0 else min(cands)
        self._go_to(target)
        return target


# endregion
