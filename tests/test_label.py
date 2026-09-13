

from __future__ import annotations

from nexora.nodes import Label
from nexora.scene import Scene


class MockRenderer:
    def __init__(self) -> None:
        self.text_calls = []

    def text_measure(
        self,
        text: str,
        *,
        scale: float = 1.0,
    ) -> tuple[float, float]:
        return (
            float(len(text) * 10) * scale,
            20.0 * scale,
        )

    def text_baseline(
        self,
        *,
        scale: float = 1.0,
    ) -> float:
        return 15.0 * scale

    def text(
        self,
        *args,
        **kwargs,
    ) -> None:
        self.text_calls.append(
            (
                args,
                kwargs,
            )
        )


def test_label_defaults() -> None:
    scene = Scene("LabelTest")

    label = scene.ui.create_child(
        "Label",
        node_type=Label,
    )

    assert label.text == ""
    assert label.scale == 1.0
    assert label.rotation == 0.0
    assert label.visible is True


def test_label_renders_text() -> None:
    scene = Scene("LabelTest")

    scene.ui.set_viewport_size(
        1280,
        720,
    )

    label = scene.ui.create_child(
        "Label",
        node_type=Label,
    )

    label.text = "Hello Nexora"

    renderer = MockRenderer()

    scene.ui.render(renderer)

    assert len(renderer.text_calls) == 1

    args, kwargs = renderer.text_calls[0]

    assert args[0] == "Hello Nexora"

    # "Hello Nexora" = 12 characters
    # Mock text size = 120 x 20
    # Default pivot = (0.5, 0.5)
    # Mock baseline = 15
    #
    # X:
    # 0 - (120 * 0.5) = -60
    #
    # Y:
    # 0 - (20 * 0.5) + 15 = 5
    assert args[1] == -60.0
    assert args[2] == 5.0

    assert kwargs["rotation"] == 0.0
    assert kwargs["scale"] == 1.0


def test_empty_label_does_not_render() -> None:
    scene = Scene("LabelTest")

    label = scene.ui.create_child(
        "Label",
        node_type=Label,
    )

    renderer = MockRenderer()

    scene.ui.render(renderer)

    assert renderer.text_calls == []

