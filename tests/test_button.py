from __future__ import annotations

from nexora.nodes import Button
from nexora.scene import Scene
from nexora.ui import UIInput


class MockRenderer:
    def __init__(self) -> None:
        self.rect_calls = []
        self.text_calls = []

    def rect(
        self,
        x,
        y,
        width,
        height,
        *,
        color,
        radius=0.0,
        **kwargs,
    ) -> None:
        self.rect_calls.append(
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "color": color,
                "radius": radius,
            }
        )

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


def create_button() -> Button:
    scene = Scene("ButtonTest")

    scene.ui.set_viewport_size(
        1280,
        720,
    )

    button = scene.ui.create_child(
        "Button",
        node_type=Button,
    )

    button.size = (
        200.0,
        60.0,
    )

    return button


def test_button_defaults() -> None:
    button = create_button()

    assert button.text == ""
    assert button.text_scale == 1.0

    assert button.hovered is False
    assert button.pressed is False

    assert button.enabled is True
    assert button.visible is True

    assert button.background == (
        32,
        34,
        37,
        255,
    )


def test_button_contains_label() -> None:
    button = create_button()

    assert len(button.children) == 1

    label = button.children[0]

    assert label is button._label
    assert label.text == ""


def test_button_text_is_synced_to_label() -> None:
    button = create_button()

    button.text = "Play"
    button.text_scale = 1.5

    renderer = MockRenderer()

    button.render(renderer)

    assert button._label.text == "Play"
    assert button._label.scale == 1.5

    assert len(renderer.text_calls) == 1

    args, kwargs = renderer.text_calls[0]

    assert args[0] == "Play"
    assert kwargs["scale"] == 1.5


def test_button_normal_state() -> None:
    button = create_button()

    renderer = MockRenderer()

    button.render(renderer)

    assert button.background == (
        32,
        34,
        37,
        255,
    )


def test_button_hover_state() -> None:
    button = create_button()

    button.hovered = True

    renderer = MockRenderer()

    button.render(renderer)

    assert button.background == (
        45,
        48,
        52,
        255,
    )


def test_button_pressed_state() -> None:
    button = create_button()

    button.pressed = True

    renderer = MockRenderer()

    button.render(renderer)

    assert button.background == (
        25,
        27,
        30,
        255,
    )


def test_button_disabled_state() -> None:
    button = create_button()

    button.enabled = False

    renderer = MockRenderer()

    button.render(renderer)

    assert button.background == (
        20,
        21,
        23,
        255,
    )


def test_button_state_priority() -> None:
    button = create_button()

    button.hovered = True
    button.pressed = True

    renderer = MockRenderer()

    button.render(renderer)

    assert button.background == (
        25,
        27,
        30,
        255,
    )

    button.enabled = False

    button.render(renderer)

    assert button.background == (
        20,
        21,
        23,
        255,
    )


def test_button_label_is_centered() -> None:
    button = create_button()

    button.text = "Play"

    renderer = MockRenderer()

    button.render(renderer)

    label = button._label

    assert label.anchor == (
        0.5,
        0.5,
    )

    assert label.pivot == (
        0.5,
        0.5,
    )

    assert label.position == (
        0.0,
        0.0,
    )

    assert label.calculate_position() == (
        0.0,
        0.0,
    )

def test_button_hovered_when_mouse_is_inside() -> None:
    button = create_button()

    ui_input = UIInput()

    ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is True


def test_button_not_hovered_when_mouse_is_outside() -> None:
    button = create_button()

    ui_input = UIInput()

    ui_input.set_mouse_position(
        150.0,
        0.0,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is False


def test_button_hover_is_disabled_when_button_disabled() -> None:
    button = create_button()

    button.enabled = False

    ui_input = UIInput()

    ui_input.set_mouse_position(
        0.0,
        0.0,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is False


def test_button_hover_is_disabled_when_button_invisible() -> None:
    button = create_button()

    button.visible = False

    ui_input = UIInput()

    ui_input.set_mouse_position(
        0.0,
        0.0,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is False

def test_button_pressed_when_mouse_is_down_inside() -> None:
    button = create_button()

    ui_input = UIInput()

    ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    ui_input.set_mouse_left(
        True,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is True
    assert button.pressed is True


def test_button_not_pressed_when_mouse_is_up() -> None:
    button = create_button()

    ui_input = UIInput()

    ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is True
    assert button.pressed is False


def test_button_not_pressed_when_mouse_is_down_outside() -> None:
    button = create_button()

    ui_input = UIInput()

    ui_input.set_mouse_position(
        150.0,
        0.0,
    )

    ui_input.set_mouse_left(
        True,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is False
    assert button.pressed is False


def test_button_pressed_is_disabled_when_button_disabled() -> None:
    button = create_button()

    button.enabled = False

    ui_input = UIInput()

    ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    ui_input.set_mouse_left(
        True,
    )

    button.update_input(
        ui_input,
    )

    assert button.hovered is False
    assert button.pressed is False

    