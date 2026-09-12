from __future__ import annotations

from pathlib import Path

import pytest
import sdl3

from nexora.nodes import Label
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.scene import Scene


ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "DejaVuSans.ttf"



def test_label_centered_gpu() -> None:
    if not FONT_PATH.exists():
        pytest.fail(
            f"Test font not found: {FONT_PATH}"
        )

    text_system = TextSystem()
    text_system.initialize()

    context = GPUContext(
        1280,
        720,
        title="Nexora - Label GPU Test",
        debug=True,
        vsync=True,
    )

    font = text_system.font(
        FONT_PATH,
        32,
    )

    renderer = Renderer(
        context,
        font=font,
    )

    scene = Scene("LabelGPUTest")

    scene.ui.set_viewport_size(
        1280,
        720,
    )

    label = scene.ui.create_child(
        "CenterLabel",
        node_type=Label,
    )

    label.text = "Nexora Engine"

    label.anchor = (
        0.5,
        0.5,
    )

    label.pivot = (
        0.5,
        0.5,
    )

    try:
        assert renderer.width == 1280
        assert renderer.height == 720

        text_width, text_height = renderer.text_measure(
            label.text,
            scale=label.scale,
        )

        baseline = renderer.text_baseline(
            scale=label.scale,
        )

        assert text_width > 0.0
        assert text_height > 0.0
        assert baseline > 0.0

        assert label.calculate_position() == (
            0.0,
            0.0,
        )

        assert label.pivot == (
            0.5,
            0.5,
        )

        assert renderer.begin_frame()

        scene.ui.render(renderer)

        assert renderer.end_frame()

    finally:
        renderer.destroy()
        context.destroy()
        text_system.shutdown()


if __name__ == "__main__":
    test_label_centered_gpu()

