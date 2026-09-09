from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame


class BindingType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"


@dataclass(frozen=True, slots=True)
class Binding:
    type: BindingType
    code: int


def resolve_keyboard_key(key: str | int) -> int:
    if isinstance(key, int):
        return key

    if not isinstance(key, str):
        raise TypeError("Keyboard binding must be a string or integer.")

    name = key.strip().lower()

    aliases = {
        "return": "enter",
        "esc": "escape",
        "spacebar": "space",
        "lshift": "left shift",
        "rshift": "right shift",
        "lctrl": "left ctrl",
        "rctrl": "right ctrl",
        "lalt": "left alt",
        "ralt": "right alt",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
    }

    name = aliases.get(name, name)

    try:
        return pygame.key.key_code(name)
    except ValueError as exc:
        raise ValueError(f"Unknown keyboard key: {key!r}") from exc


def resolve_mouse_button(button: int | str) -> int:
    if isinstance(button, int):
        if button < 1:
            raise ValueError("Mouse button must be at least 1.")
        return button

    if not isinstance(button, str):
        raise TypeError("Mouse binding must be a string or integer.")

    name = button.strip().lower()

    aliases = {
        "left": 1,
        "mouse_left": 1,
        "mouse1": 1,

        "middle": 2,
        "mouse_middle": 2,
        "mouse2": 2,

        "right": 3,
        "mouse_right": 3,
        "mouse3": 3,

        "x1": 4,
        "mouse_x1": 4,
        "mouse4": 4,

        "x2": 5,
        "mouse_x2": 5,
        "mouse5": 5,
    }

    if name in aliases:
        return aliases[name]

    try:
        value = int(name)
    except ValueError as exc:
        raise ValueError(f"Unknown mouse button: {button!r}") from exc

    if value < 1:
        raise ValueError("Mouse button must be at least 1.")

    return value