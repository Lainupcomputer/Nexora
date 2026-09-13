
from __future__ import annotations

from types import SimpleNamespace

from nexora.rendering.gpu.text_renderer import GPUTextRenderer


def create_mock_renderer() -> GPUTextRenderer:
    renderer = object.__new__(GPUTextRenderer)

    renderer.font = SimpleNamespace(
        line_skip=20.0,
        glyph=lambda codepoint: SimpleNamespace(
            advance=10.0,
        ),
    )

    return renderer


def test_measure_single_line() -> None:
    renderer = create_mock_renderer()

    width, height = renderer.measure(
        "Hello",
    )

    assert width == 50.0
    assert height == 20.0


def test_measure_multiline() -> None:
    renderer = create_mock_renderer()

    width, height = renderer.measure(
        "Hello\nWorld",
    )

    assert width == 50.0
    assert height == 40.0


def test_measure_uses_longest_line() -> None:
    renderer = create_mock_renderer()

    width, height = renderer.measure(
        "Hi\nHello",
    )

    assert width == 50.0
    assert height == 40.0


def test_measure_scale() -> None:
    renderer = create_mock_renderer()

    width, height = renderer.measure(
        "Hello",
        scale=2.0,
    )

    assert width == 100.0
    assert height == 40.0


def test_measure_empty_text() -> None:
    renderer = create_mock_renderer()

    width, height = renderer.measure("")

    assert width == 0.0
    assert height == 0.0