from __future__ import annotations

from nexora.ui import UIInput


def test_ui_input_defaults() -> None:
    ui_input = UIInput()

    assert ui_input.mouse_position == (
        0.0,
        0.0,
    )

    assert ui_input.mouse_left_down is False
    assert ui_input.mouse_left_pressed is False
    assert ui_input.mouse_left_released is False


def test_mouse_position() -> None:
    ui_input = UIInput()

    ui_input.set_mouse_position(
        123.5,
        456.25,
    )

    assert ui_input.mouse_position == (
        123.5,
        456.25,
    )


def test_mouse_press() -> None:
    ui_input = UIInput()

    ui_input.set_mouse_left(True)

    assert ui_input.mouse_left_down is True
    assert ui_input.mouse_left_pressed is True
    assert ui_input.mouse_left_released is False


def test_mouse_release() -> None:
    ui_input = UIInput()

    ui_input.set_mouse_left(True)
    ui_input.begin_frame()

    ui_input.set_mouse_left(False)

    assert ui_input.mouse_left_down is False
    assert ui_input.mouse_left_pressed is False
    assert ui_input.mouse_left_released is True


def test_pressed_is_only_true_for_transition() -> None:
    ui_input = UIInput()

    ui_input.set_mouse_left(True)

    assert ui_input.mouse_left_pressed is True

    ui_input.begin_frame()

    assert ui_input.mouse_left_pressed is False

    ui_input.set_mouse_left(True)

    assert ui_input.mouse_left_down is True
    assert ui_input.mouse_left_pressed is False


def test_released_is_only_true_for_transition() -> None:
    ui_input = UIInput()

    ui_input.set_mouse_left(True)
    ui_input.begin_frame()

    ui_input.set_mouse_left(False)

    assert ui_input.mouse_left_released is True

    ui_input.begin_frame()

    assert ui_input.mouse_left_released is False