"""Cache behaviour and Golden Evaluation Rule tests (no Maya needed).
"""

# region Imports & Config

# python modules
import gc
import weakref

# pose_ghoster modules
from pose_ghoster.core.cache import GhostCache, GhostSnapshot, Topology
from pose_ghoster.core.manager import GhostManager, GhostMode

TOPO = Topology(num_vertices=8, wire_indices=[0, 1], tri_indices=[0, 1, 2], nbytes=64)

# endregion

# ==========

# region Helpers


def snap(target="a", frame=1.0, pinned=False, nbytes=100):
    """Build a dummy snapshot."""
    return GhostSnapshot(
        target, frame, [0.0] * 8, TOPO, pinned=pinned, nbytes=nbytes
    )


class FakeHost:
    """Stand-in for Maya: records bakes, owns time, selection and keys."""

    def __init__(self):
        self.time = 10.0
        self.bakes = []
        self.selection = ["a"]
        self.keys = [5.0, 10.0, 20.0, 30.0]
        self.key_calls = []

    def baker(self, target, frame, topo, pinned):
        """Record a bake and return a dummy snapshot."""
        self.bakes.append((target, frame, pinned))
        return snap(target, frame, pinned)

    def key_finder(self, target, sources):
        """Record the call and return the keys (or the override's keys)."""
        self.key_calls.append((target, list(sources)))
        return [100.0, 200.0] if sources else list(self.keys)

    def make(self, targets=("a",), **settings):
        """Create an active manager wired to this fake host."""
        mgr = GhostManager(
            cache=GhostCache(),
            baker=self.baker,
            topology_extractor=lambda t: TOPO,
            resolver=lambda names: list(names),
            key_finder=self.key_finder,
        )
        mgr.configure_host(
            time_getter=lambda: self.time,
            time_setter=lambda f: setattr(self, "time", f),
            selection_getter=lambda: self.selection,
            scheduler=lambda fn: fn(),
        )
        settings = dict({"past_count": 2, "future_count": 2}, **settings)
        mgr.set_settings(**settings)
        mgr.activate(nodes=list(targets))
        return mgr

    def frames(self):
        """Return the sorted baked frames."""
        return sorted(f for _, f, _ in self.bakes)


# endregion

# ==========

# region Cache Tests


def test_put_get_and_stats():
    """Hits and misses are counted."""
    c = GhostCache()
    c.put(snap(frame=1))
    assert c.get("a", 1) is not None
    assert c.get("a", 2) is None
    assert (c.stats.hits, c.stats.misses) == (1, 1)


def test_lru_eviction_respects_byte_budget():
    """Oldest relative ghosts are evicted first."""
    c = GhostCache(max_bytes=250)
    for f in range(5):
        c.put(snap(frame=f))
    assert c.memory_bytes <= 250 and c.size == 2
    assert c.get("a", 0) is None and c.get("a", 4) is not None
    assert c.stats.evictions == 3


def test_invalidate_relative_keeps_pins_and_drops_keys():
    """Animation edits drop relative ghosts and key lists only."""
    c = GhostCache()
    c.put(snap(frame=1))
    c.put(snap(frame=5, pinned=True))
    c.set_keys("a", [3, 1])
    assert c.keys("a") == [1.0, 3.0]
    assert c.invalidate_relative() == 1
    assert c.get("a", 1) is None and c.keys("a") is None
    assert c.get("a", 5, pinned=True) is not None


def test_invalidate_target_releases_everything_for_it():
    """Releasing a target frees its snapshots, keys and topology."""
    c = GhostCache()
    c.put(snap("a", 1))
    c.put(snap("a", 2, pinned=True))
    c.put(snap("b", 1))
    c.set_topology("a", TOPO)
    c.set_keys("a", [1])
    c.invalidate_target("a")
    assert c.get("a", 1) is None and c.get("a", 2, pinned=True) is None
    assert c.topology("a") is None and c.keys("a") is None
    assert c.get("b", 1) is not None


# endregion

# ==========

# region Golden Evaluation Rule Tests


def test_initial_window_bakes_each_frame_once():
    """T-2..T+2 are baked once each."""
    host = FakeHost()
    host.make()
    assert host.frames() == [8.0, 9.0, 11.0, 12.0]


def test_time_change_bakes_only_newly_exposed_frames():
    """Sliding the window by one frame bakes two new frames."""
    host = FakeHost()
    mgr = host.make()
    host.bakes.clear()
    host.time = 11.0
    mgr.on_time_changed()
    assert host.frames() == [10.0, 13.0]


def test_scrubbing_back_is_free():
    """Returning to a visited frame is served from the cache."""
    host = FakeHost()
    mgr = host.make()
    host.time = 11.0
    mgr.on_time_changed()
    host.bakes.clear()
    host.time = 10.0
    mgr.on_time_changed()
    assert host.bakes == []


def test_camera_activity_never_recalculates():
    """Orbit, pan and zoom only read draw_items: nothing bakes or rebuilds."""
    host = FakeHost()
    mgr = host.make()
    host.bakes.clear()
    version = mgr.version
    for _ in range(1000):
        _ = mgr.draw_items
        mgr.on_time_changed()
    assert host.bakes == [] and mgr.version == version


def test_keyframe_edit_rebakes_once_even_if_spammed():
    """A drag of edit events collapses into a single resample."""
    host = FakeHost()
    queued = []
    mgr = host.make()
    mgr.configure_host(scheduler=queued.append)
    host.bakes.clear()
    for _ in range(50):
        mgr.on_keyframes_changed()
    assert host.bakes == [] and len(queued) == 1
    queued[0]()
    assert len(host.bakes) == 4


def test_pins_survive_keyframe_edits_and_navigate():
    """Pins are kept on edits and can be jumped to."""
    host = FakeHost()
    mgr = host.make()
    host.time = 20.0
    mgr.pin()
    assert mgr.pinned_frames == [20.0]
    host.time = 30.0
    mgr.on_time_changed()
    mgr.on_keyframes_changed()
    assert mgr.pinned_frames == [20.0]
    assert mgr.go_to_pin(-1) == 20.0 and host.time == 20.0
    assert mgr.go_to_pin(-1) is None


def test_show_pins_off_hides_pins_without_baking():
    """Toggling pins redraws from the cache."""
    host = FakeHost()
    mgr = host.make(mode=GhostMode.OFF)
    mgr.pin(20.0)
    assert [i.kind for i in mgr.draw_items] == ["pinned"]
    host.bakes.clear()
    mgr.set_settings(show_pins=False)
    assert mgr.draw_items == [] and host.bakes == []


def test_style_change_does_not_bake():
    """Opacity and fill changes only rebuild draw items."""
    host = FakeHost()
    mgr = host.make()
    host.bakes.clear()
    mgr.set_settings(opacity=0.9, show_fill=False)
    assert host.bakes == []


# endregion

# ==========

# region Keys Mode Tests


def test_keys_mode_draws_neighbouring_keyed_poses():
    """At frame 12 the previous key is 10 and the next is 20."""
    host = FakeHost()
    host.time = 12.0
    mgr = host.make(mode=GhostMode.KEYS)
    assert host.frames() == [10.0, 20.0]
    assert [(i.kind, i.frame) for i in mgr.draw_items] == [
        ("past", 10.0),
        ("future", 20.0),
    ]


def test_keys_mode_on_a_key_skips_the_current_key():
    """Standing on key 10 shows keys 5 and 20."""
    host = FakeHost()
    mgr = host.make(mode=GhostMode.KEYS)
    assert sorted(i.frame for i in mgr.draw_items) == [5.0, 20.0]
    assert mgr.settings.mode == GhostMode.KEYS


def test_keys_mode_counts_and_ranks():
    """Two keys each side, nearest first."""
    host = FakeHost()
    host.time = 15.0
    mgr = host.make(mode=GhostMode.KEYS, key_past_count=2, key_future_count=2)
    assert sorted(i.frame for i in mgr.draw_items) == [5.0, 10.0, 20.0, 30.0]


def test_keys_mode_scrubbing_between_keys_is_free():
    """No bake and no key search while time moves between two keys."""
    host = FakeHost()
    host.time = 12.0
    mgr = host.make(mode=GhostMode.KEYS)
    host.bakes.clear()
    calls = len(host.key_calls)
    for t in (13.0, 14.0, 15.0, 19.0, 12.0):
        host.time = t
        mgr.on_time_changed()
    assert host.bakes == [] and len(host.key_calls) == calls


def test_keys_mode_crossing_a_key_bakes_one_new_pose():
    """Passing key 20 exposes key 30 as the next pose."""
    host = FakeHost()
    host.time = 12.0
    mgr = host.make(mode=GhostMode.KEYS)
    host.bakes.clear()
    host.time = 21.0
    mgr.on_time_changed()
    assert host.frames() == [30.0]
    assert sorted(i.frame for i in mgr.draw_items) == [20.0, 30.0]


def test_controller_override_replaces_auto_keys():
    """Key sources are passed to the finder and change the keyed poses."""
    host = FakeHost()
    host.time = 150.0
    mgr = host.make(mode=GhostMode.KEYS)
    assert mgr.draw_items == [] or all(i.frame != 100.0 for i in mgr.draw_items)
    mgr.set_key_sources(["ctrl"])
    assert host.key_calls[-1] == ("a", ["ctrl"])
    assert sorted(i.frame for i in mgr.draw_items) == [100.0, 200.0]
    mgr.set_key_sources([])
    assert host.key_calls[-1] == ("a", [])


def test_keyframe_edit_refinds_keys():
    """An animation edit rebuilds the key list once."""
    host = FakeHost()
    host.time = 12.0
    mgr = host.make(mode=GhostMode.KEYS)
    calls = len(host.key_calls)
    mgr.on_keyframes_changed()
    assert len(host.key_calls) == calls + 1


# endregion

# ==========

# region Leak Prevention Tests


def test_deactivate_releases_all_memory():
    """Deactivating leaves no live snapshot behind, pins and keys included."""
    host = FakeHost()
    mgr = host.make(mode=GhostMode.KEYS)
    mgr.pin()
    ref = weakref.ref(mgr.cache.get("a", host.time, pinned=True))
    mgr.deactivate()
    gc.collect()
    assert ref() is None
    assert mgr.cache.size == 0 and mgr.cache.memory_bytes == 0
    assert mgr.draw_items == [] and mgr.key_sources == []


def test_selection_change_releases_previous_target():
    """Retargeting frees the old mesh; empty selections are ignored."""
    host = FakeHost()
    mgr = host.make(targets=())
    mgr.follow_selection = True
    host.selection = ["a"]
    mgr.on_selection_changed()
    assert mgr.targets == ["a"]
    host.selection = ["b"]
    mgr.on_selection_changed()
    assert mgr.targets == ["b"]
    assert all(k[0] == "b" for k in list(mgr.cache._relative))
    host.selection = []
    mgr.on_selection_changed()
    assert mgr.targets == ["b"]


# endregion
