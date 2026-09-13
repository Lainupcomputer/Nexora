from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import sdl3


class BindingType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"


@dataclass(frozen=True, slots=True)
class Binding:
    type: BindingType
    code: int


_KEY_ALIASES = {
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

    "pageup": "page up",
    "pagedown": "page down",

    "pgup": "page up",
    "pgdn": "page down",

    "del": "delete",
    "ins": "insert",

    "backspace": "backspace",
    "tab": "tab",
    "capslock": "caps lock",
}


# SDL scancode names.
# We intentionally resolve common keys explicitly so bindings do not
# depend on keyboard layout.
_KEY_SCANCODES = {
    "a": sdl3.SDL_SCANCODE_A,
    "b": sdl3.SDL_SCANCODE_B,
    "c": sdl3.SDL_SCANCODE_C,
    "d": sdl3.SDL_SCANCODE_D,
    "e": sdl3.SDL_SCANCODE_E,
    "f": sdl3.SDL_SCANCODE_F,
    "g": sdl3.SDL_SCANCODE_G,
    "h": sdl3.SDL_SCANCODE_H,
    "i": sdl3.SDL_SCANCODE_I,
    "j": sdl3.SDL_SCANCODE_J,
    "k": sdl3.SDL_SCANCODE_K,
    "l": sdl3.SDL_SCANCODE_L,
    "m": sdl3.SDL_SCANCODE_M,
    "n": sdl3.SDL_SCANCODE_N,
    "o": sdl3.SDL_SCANCODE_O,
    "p": sdl3.SDL_SCANCODE_P,
    "q": sdl3.SDL_SCANCODE_Q,
    "r": sdl3.SDL_SCANCODE_R,
    "s": sdl3.SDL_SCANCODE_S,
    "t": sdl3.SDL_SCANCODE_T,
    "u": sdl3.SDL_SCANCODE_U,
    "v": sdl3.SDL_SCANCODE_V,
    "w": sdl3.SDL_SCANCODE_W,
    "x": sdl3.SDL_SCANCODE_X,
    "y": sdl3.SDL_SCANCODE_Y,
    "z": sdl3.SDL_SCANCODE_Z,

    "0": sdl3.SDL_SCANCODE_0,
    "1": sdl3.SDL_SCANCODE_1,
    "2": sdl3.SDL_SCANCODE_2,
    "3": sdl3.SDL_SCANCODE_3,
    "4": sdl3.SDL_SCANCODE_4,
    "5": sdl3.SDL_SCANCODE_5,
    "6": sdl3.SDL_SCANCODE_6,
    "7": sdl3.SDL_SCANCODE_7,
    "8": sdl3.SDL_SCANCODE_8,
    "9": sdl3.SDL_SCANCODE_9,

    "escape": sdl3.SDL_SCANCODE_ESCAPE,
    "enter": sdl3.SDL_SCANCODE_RETURN,
    "space": sdl3.SDL_SCANCODE_SPACE,
    "tab": sdl3.SDL_SCANCODE_TAB,
    "backspace": sdl3.SDL_SCANCODE_BACKSPACE,

    "left shift": sdl3.SDL_SCANCODE_LSHIFT,
    "right shift": sdl3.SDL_SCANCODE_RSHIFT,

    "left ctrl": sdl3.SDL_SCANCODE_LCTRL,
    "right ctrl": sdl3.SDL_SCANCODE_RCTRL,

    "left alt": sdl3.SDL_SCANCODE_LALT,
    "right alt": sdl3.SDL_SCANCODE_RALT,

    "up": sdl3.SDL_SCANCODE_UP,
    "down": sdl3.SDL_SCANCODE_DOWN,
    "left": sdl3.SDL_SCANCODE_LEFT,
    "right": sdl3.SDL_SCANCODE_RIGHT,

    "home": sdl3.SDL_SCANCODE_HOME,
    "end": sdl3.SDL_SCANCODE_END,

    "page up": sdl3.SDL_SCANCODE_PAGEUP,
    "page down": sdl3.SDL_SCANCODE_PAGEDOWN,

    "insert": sdl3.SDL_SCANCODE_INSERT,
    "delete": sdl3.SDL_SCANCODE_DELETE,

    "caps lock": sdl3.SDL_SCANCODE_CAPSLOCK,

    "f1": sdl3.SDL_SCANCODE_F1,
    "f2": sdl3.SDL_SCANCODE_F2,
    "f3": sdl3.SDL_SCANCODE_F3,
    "f4": sdl3.SDL_SCANCODE_F4,
    "f5": sdl3.SDL_SCANCODE_F5,
    "f6": sdl3.SDL_SCANCODE_F6,
    "f7": sdl3.SDL_SCANCODE_F7,
    "f8": sdl3.SDL_SCANCODE_F8,
    "f9": sdl3.SDL_SCANCODE_F9,
    "f10": sdl3.SDL_SCANCODE_F10,
    "f11": sdl3.SDL_SCANCODE_F11,
    "f12": sdl3.SDL_SCANCODE_F12,

    "minus": sdl3.SDL_SCANCODE_MINUS,
    "equals": sdl3.SDL_SCANCODE_EQUALS,

    "left bracket": sdl3.SDL_SCANCODE_LEFTBRACKET,
    "right bracket": sdl3.SDL_SCANCODE_RIGHTBRACKET,

    "backslash": sdl3.SDL_SCANCODE_BACKSLASH,
    "semicolon": sdl3.SDL_SCANCODE_SEMICOLON,
    "apostrophe": sdl3.SDL_SCANCODE_APOSTROPHE,
    "grave": sdl3.SDL_SCANCODE_GRAVE,

    "comma": sdl3.SDL_SCANCODE_COMMA,
    "period": sdl3.SDL_SCANCODE_PERIOD,
    "slash": sdl3.SDL_SCANCODE_SLASH,

    "print screen": sdl3.SDL_SCANCODE_PRINTSCREEN,
    "scroll lock": sdl3.SDL_SCANCODE_SCROLLLOCK,
    "pause": sdl3.SDL_SCANCODE_PAUSE,

    "num lock": sdl3.SDL_SCANCODE_NUMLOCKCLEAR,

    "kp 0": sdl3.SDL_SCANCODE_KP_0,
    "kp 1": sdl3.SDL_SCANCODE_KP_1,
    "kp 2": sdl3.SDL_SCANCODE_KP_2,
    "kp 3": sdl3.SDL_SCANCODE_KP_3,
    "kp 4": sdl3.SDL_SCANCODE_KP_4,
    "kp 5": sdl3.SDL_SCANCODE_KP_5,
    "kp 6": sdl3.SDL_SCANCODE_KP_6,
    "kp 7": sdl3.SDL_SCANCODE_KP_7,
    "kp 8": sdl3.SDL_SCANCODE_KP_8,
    "kp 9": sdl3.SDL_SCANCODE_KP_9,
}


def resolve_keyboard_key(key: str | int) -> int:
    """
    Resolve a keyboard binding to an SDL3 scancode.

    Integer values are treated as raw SDL scancodes.
    String values are layout-independent physical key names.
    """

    if isinstance(key, int):
        return key

    if not isinstance(key, str):
        raise TypeError("keyboard key must be str or int")

    name = key.strip().lower()

    if not name:
        raise ValueError("keyboard key cannot be empty")

    name = _KEY_ALIASES.get(name, name)

    # Single-character keys.
    if len(name) == 1 and name in _KEY_SCANCODES:
        return _KEY_SCANCODES[name]

    try:
        return _KEY_SCANCODES[name]
    except KeyError:
        raise ValueError(f"Unknown SDL keyboard key: {key!r}") from None


def resolve_mouse_button(button: str | int) -> int:
    """
    Resolve a mouse button.

    SDL3 mouse button values:
        1 = left
        2 = middle
        3 = right
        4 = X1
        5 = X2
    """

    if isinstance(button, int):
        if 1 <= button <= 5:
            return button
        raise ValueError(f"Invalid mouse button: {button}")

    if not isinstance(button, str):
        raise TypeError("mouse button must be str or int")

    aliases = {
        "left": 1,
        "middle": 2,
        "right": 3,
        "x1": 4,
        "x2": 5,
    }

    name = button.strip().lower()

    try:
        return aliases[name]
    except KeyError:
        raise ValueError(f"Unknown mouse button: {button!r}") from None