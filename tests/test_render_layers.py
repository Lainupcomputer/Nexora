from __future__ import annotations

from dataclasses import dataclass

from nexora.rendering.gpu.renderer import GPURenderer


class _DrawBatch:
    def __init__(self, kind: str, calls: list[tuple]) -> None:
        self.kind = kind
        self.calls = calls

    def draw_range(self, render_pass, start: int, count: int) -> int:
        self.calls.append((self.kind, start, count))
        return count


class _ShapeDrawBatch:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls

    def draw_shape_range(self, render_pass, start: int, count: int) -> int:
        self.calls.append(("shape", start, count))
        return count

    def draw_geometry_range(self, render_pass, start: int, count: int) -> int:
        self.calls.append(("geometry", start, count))
        return count


class _TextDrawBatch:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls

    def draw_range(self, render_pass, start: int, count: int) -> int:
        self.calls.append(("text", start, count))
        return count


class _LineSubmitBatch:
    def __init__(self) -> None:
        self.line_count = 0

    def add(self, *args, **kwargs) -> None:
        self.line_count += 1


class _ShapeSubmitBatch:
    def __init__(self) -> None:
        self.shape_count = 0
        self.geometry_vertex_count = 0

    def circle(self, *args, **kwargs) -> None:
        self.shape_count += 1

    def ellipse(self, *args, **kwargs) -> None:
        self.shape_count += 1

    def triangle(self, *args, **kwargs) -> None:
        self.geometry_vertex_count += 3

    def polygon(self, points, *args, **kwargs) -> None:
        points = list(points)
        self.geometry_vertex_count += (len(points) - 2) * 3


class _TextSubmitBatch:
    def __init__(self) -> None:
        self.glyph_count = 0

    def draw(self, text: str, *args, **kwargs) -> int:
        count = len(text)
        self.glyph_count += count
        return count


class _SpriteSubmitBatch:
    def __init__(self) -> None:
        self.sprite_count = 0

    def submit_snapshot(self, snapshot, *, texture) -> int:
        count = int(snapshot.count)
        self.sprite_count += count
        return count


@dataclass
class _Snapshot:
    count: int


def _bare_renderer() -> GPURenderer:
    renderer = GPURenderer.__new__(GPURenderer)
    renderer._destroyed = False
    renderer._frame_started = True
    renderer._clip_stack = []
    renderer._render_commands = []
    renderer._submission_index = 0
    return renderer


def test_draw_scene_sorts_globally_by_layer_and_submission_order() -> None:
    calls: list[tuple] = []
    renderer = _bare_renderer()

    renderer.sprite_batch = _DrawBatch("sprite", calls)
    renderer.rect_batch = _DrawBatch("rect", calls)
    renderer.line_batch = _DrawBatch("line", calls)
    renderer.shape_batch = _ShapeDrawBatch(calls)
    renderer.text_renderer = _TextDrawBatch(calls)

    # Deliberately submit in a scrambled renderer-type order.
    renderer._queue_render_command("text", 0, 2, 100)
    renderer._queue_render_command("rect", 0, 1, -100)
    renderer._queue_render_command("line", 0, 1, 10)
    renderer._queue_render_command("sprite", 0, 4, 0)
    renderer._queue_render_command("shape", 0, 1, 20)
    renderer._queue_render_command("geometry", 0, 3, 30)

    renderer._draw_scene(object())

    assert calls == [
        ("rect", 0, 1),
        ("sprite", 0, 4),
        ("line", 0, 1),
        ("shape", 0, 1),
        ("geometry", 0, 3),
        ("text", 0, 2),
    ]


def test_equal_layers_preserve_exact_submission_order_across_types() -> None:
    calls: list[tuple] = []
    renderer = _bare_renderer()

    renderer.sprite_batch = _DrawBatch("sprite", calls)
    renderer.rect_batch = _DrawBatch("rect", calls)
    renderer.line_batch = _DrawBatch("line", calls)
    renderer.shape_batch = _ShapeDrawBatch(calls)
    renderer.text_renderer = _TextDrawBatch(calls)

    renderer._queue_render_command("rect", 0, 1, 50)
    renderer._queue_render_command("shape", 0, 1, 50)
    renderer._queue_render_command("line", 0, 1, 50)
    renderer._queue_render_command("sprite", 0, 1, 50)
    renderer._queue_render_command("text", 0, 1, 50)

    renderer._draw_scene(object())

    assert calls == [
        ("rect", 0, 1),
        ("shape", 0, 1),
        ("line", 0, 1),
        ("sprite", 0, 1),
        ("text", 0, 1),
    ]


def test_public_line_and_shape_methods_queue_correct_ranges() -> None:
    renderer = _bare_renderer()
    renderer.line_batch = _LineSubmitBatch()
    renderer.shape_batch = _ShapeSubmitBatch()

    renderer.line(0, 0, 10, 10, layer=5)
    renderer.circle(0, 0, 20, layer=6)
    renderer.ellipse(0, 0, 30, 10, layer=7)
    renderer.triangle(0, 0, 10, 0, 5, 10, layer=8)
    renderer.polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        layer=9,
    )

    assert renderer._render_commands == [
        (5, 0, "line", 0, 1),
        (6, 1, "shape", 0, 1),
        (7, 2, "shape", 1, 1),
        (8, 3, "geometry", 0, 3),
        (9, 4, "geometry", 3, 6),
    ]


def test_text_queues_glyph_range_on_requested_layer() -> None:
    renderer = _bare_renderer()
    renderer.text_renderer = _TextSubmitBatch()

    count = renderer.text(
        "Nexora",
        0,
        0,
        layer=123,
    )

    assert count == 6
    assert renderer._render_commands == [
        (123, 0, "text", 0, 6),
    ]


def test_snapshot_submit_participates_in_global_layer_queue() -> None:
    renderer = _bare_renderer()
    renderer.sprite_batch = _SpriteSubmitBatch()

    count = renderer.submit(
        _Snapshot(count=4),
        texture=object(),
        layer=-7,
    )

    assert count == 4
    assert renderer._render_commands == [
        (-7, 0, "sprite", 0, 4),
    ]
