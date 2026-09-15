from __future__ import annotations

from nexora.rendering.gpu.renderer import GPURenderer


class _Batch:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def draw_range(self, render_pass, start, count):
        self.calls.append((self.name, start, count))
        return count


def _renderer():
    r = GPURenderer.__new__(GPURenderer)
    r._destroyed = False
    r._frame_started = True
    r._clip_stack = []
    r._render_commands = []
    r._render_command_phases = []
    r._submission_index = 0
    r._render_phase = "world"
    return r


def test_render_phase_scope_restores_previous_phase():
    r = _renderer()
    assert r.render_phase == "world"
    with r.overlay_scope():
        assert r.render_phase == "overlay"
    assert r.render_phase == "world"


def test_draw_scene_can_filter_world_and_overlay_commands():
    calls = []
    r = _renderer()
    r.sprite_batch = _Batch("sprite", calls)
    r.rect_batch = _Batch("rect", calls)
    r.line_batch = _Batch("line", calls)
    r.shape_batch = object()
    r.text_renderer = None

    r._queue_render_command("rect", 0, 1, 0)
    with r.overlay_scope():
        r._queue_render_command("sprite", 0, 1, -1000)
    r._queue_render_command("line", 0, 1, 10)

    r._draw_scene(object(), phase="world")
    assert calls == [("rect", 0, 1), ("line", 0, 1)]

    calls.clear()
    r._draw_scene(object(), phase="overlay")
    assert calls == [("sprite", 0, 1)]


def test_command_tuple_layout_remains_backwards_compatible():
    r = _renderer()
    r._queue_render_command("rect", 5, 2, 17)
    assert r._render_commands == [(17, 0, "rect", 5, 2)]
    assert r._render_command_phases == ["world"]
