from __future__ import annotations

from typing import Iterable

import pygame

from nexora.debug.logger import Logger
from nexora.input.action import ActionState
from nexora.input.bindings import (
    Binding,
    BindingType,
    resolve_keyboard_key,
    resolve_mouse_button,
)
from nexora.threading.context import ThreadContext


class InputManager:
    """
    Main-thread input manager.

    Pygame events are processed on the main thread.
    Worker threads only read the synchronized state.
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self.logger = logger
        self._mouse_pressed: set[int] = set()
        self._mouse_released: set[int] = set()

        self._actions: dict[str, ActionState] = {}
        self._bindings: dict[str, list[Binding]] = {}

        self._keys_down: set[int] = set()
        self._mouse_down: set[int] = set()

        self._mouse_x = 0
        self._mouse_y = 0

        self._mouse_dx = 0
        self._mouse_dy = 0

        self._wheel_x = 0
        self._wheel_y = 0

        self._initialized = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initializes the cached mouse state.

        Must be called from the main thread.
        """
        ThreadContext.assert_main_thread("InputManager.initialize")

        position = pygame.mouse.get_pos()

        self._mouse_x = position[0]
        self._mouse_y = position[1]

        self._initialized = True

    # ------------------------------------------------------------------
    # Binding API
    # ------------------------------------------------------------------

    def bind(
        self,
        action: str,
        binding: str | int,
    ) -> None:
        """
        Bind a keyboard key or mouse button to an action.

        Examples:

            input.bind("move_left", "A")
            input.bind("move_left", "LEFT")
            input.bind("jump", "SPACE")

            input.bind("shoot", "MOUSE_LEFT")
        """
        action = self._normalize_action(action)

        if isinstance(binding, str) and binding.strip().lower().startswith("mouse"):
            resolved = resolve_mouse_button(binding)
            new_binding = Binding(BindingType.MOUSE, resolved)
        else:
            try:
                resolved = resolve_keyboard_key(binding)
                new_binding = Binding(BindingType.KEYBOARD, resolved)
            except (TypeError, ValueError):
                if isinstance(binding, str):
                    resolved = resolve_mouse_button(binding)
                    new_binding = Binding(BindingType.MOUSE, resolved)
                else:
                    raise

        bindings = self._bindings.setdefault(action, [])

        if new_binding not in bindings:
            bindings.append(new_binding)

        self._actions.setdefault(action, ActionState())

    def bind_key(
        self,
        action: str,
        key: str | int,
    ) -> None:
        action = self._normalize_action(action)

        resolved = resolve_keyboard_key(key)

        binding = Binding(BindingType.KEYBOARD, resolved)

        bindings = self._bindings.setdefault(action, [])

        if binding not in bindings:
            bindings.append(binding)

        self._actions.setdefault(action, ActionState())

    def bind_mouse(
        self,
        action: str,
        button: str | int,
    ) -> None:
        action = self._normalize_action(action)

        resolved = resolve_mouse_button(button)

        binding = Binding(BindingType.MOUSE, resolved)

        bindings = self._bindings.setdefault(action, [])

        if binding not in bindings:
            bindings.append(binding)

        self._actions.setdefault(action, ActionState())

    def unbind(
        self,
        action: str,
        binding: str | int,
    ) -> bool:
        action = self._normalize_action(action)

        if action not in self._bindings:
            return False

        if isinstance(binding, str) and binding.strip().lower().startswith("mouse"):
            resolved = Binding(BindingType.MOUSE, resolve_mouse_button(binding))
        else:
            try:
                resolved = Binding(
                    BindingType.KEYBOARD,
                    resolve_keyboard_key(binding),
                )
            except (TypeError, ValueError):
                if isinstance(binding, str):
                    resolved = Binding(
                        BindingType.MOUSE,
                        resolve_mouse_button(binding),
                    )
                else:
                    raise

        bindings = self._bindings[action]

        if resolved not in bindings:
            return False

        bindings.remove(resolved)
        return True

    def clear_bindings(self, action: str | None = None) -> None:
        if action is None:
            self._bindings.clear()
            self._actions.clear()
            return

        action = self._normalize_action(action)

        self._bindings.pop(action, None)
        self._actions.pop(action, None)

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def begin_frame(
        self,
        events: Iterable[pygame.event.Event] = (),
    ) -> None:
        """
        Process all pygame events for the current frame.

        Must only run on the main thread.
        """
        ThreadContext.assert_main_thread("InputManager.begin_frame")

        if not self._initialized:
            self.initialize()

        for state in self._actions.values():
            state.begin_frame()

        self._mouse_dx = 0
        self._mouse_dy = 0
        self._wheel_x = 0
        self._wheel_y = 0

        self._mouse_pressed.clear()
        self._mouse_released.clear()

        for event in events:
            self._process_event(event)

        self._update_mouse_position()
        self._update_action_states()


    def _process_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._keys_down.add(event.key)

        elif event.type == pygame.KEYUP:
            self._keys_down.discard(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_down.add(event.button)
            self._mouse_pressed.add(event.button)

        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_down.discard(event.button)
            self._mouse_released.add(event.button)

        elif event.type == pygame.MOUSEMOTION:
            self._mouse_dx += event.rel[0]
            self._mouse_dy += event.rel[1]

            self._mouse_x = event.pos[0]
            self._mouse_y = event.pos[1]

        elif event.type == pygame.MOUSEWHEEL:
            self._wheel_x += event.x
            self._wheel_y += event.y

        elif event.type == pygame.WINDOWFOCUSLOST:
            self._keys_down.clear()
            self._mouse_down.clear()

        elif event.type == pygame.ACTIVEEVENT:
            # Compatibility with pygame configurations where focus
            # events are still delivered through ACTIVEEVENT.
            if getattr(event, "gain", 1) == 0:
                self._keys_down.clear()
                self._mouse_down.clear()


    def _update_mouse_position(self) -> None:
        """
        Reads the mouse position on the main thread only.
        """
        position = pygame.mouse.get_pos()

        self._mouse_x = position[0]
        self._mouse_y = position[1]

    def _update_action_states(self) -> None:
        for action, state in self._actions.items():
            old_down = state.down
            new_down = self._action_is_down(action)

            state.down = new_down

            if new_down and not old_down:
                state.pressed = True

            if old_down and not new_down:
                state.released = True

    def _action_is_down(self, action: str) -> bool:
        bindings = self._bindings.get(action)

        if not bindings:
            return False

        for binding in bindings:
            if binding.type is BindingType.KEYBOARD:
                if binding.code in self._keys_down:
                    return True

            elif binding.type is BindingType.MOUSE:
                if binding.code in self._mouse_down:
                    return True

        return False

    # ------------------------------------------------------------------
    # Action state
    # ------------------------------------------------------------------

    def is_down(self, action: str) -> bool:
        action = self._normalize_action(action)

        state = self._actions.get(action)

        if state is None:
            return False

        return state.down

    def is_pressed(self, action: str) -> bool:
        action = self._normalize_action(action)

        state = self._actions.get(action)

        if state is None:
            return False

        return state.pressed

    def is_released(self, action: str) -> bool:
        action = self._normalize_action(action)

        state = self._actions.get(action)

        if state is None:
            return False

        return state.released

    def action_state(self, action: str) -> ActionState:
        action = self._normalize_action(action)

        return self._actions.setdefault(action, ActionState())

    def actions(self) -> tuple[str, ...]:
        return tuple(self._actions)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def key_down(self, key: str | int) -> bool:
        resolved = resolve_keyboard_key(key)
        return resolved in self._keys_down

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def mouse_position(self) -> tuple[int, int]:
        return self._mouse_x, self._mouse_y

    def mouse_delta(self) -> tuple[int, int]:
        return self._mouse_dx, self._mouse_dy

    def mouse_down(self, button: int | str = 1) -> bool:
        resolved = resolve_mouse_button(button)
        return resolved in self._mouse_down

    def mouse_pressed(self, button: int | str = 1) -> bool:
        resolved = resolve_mouse_button(button)

        return self._mouse_button_transition(
            resolved,
            pressed=True,
        )

    def mouse_released(self, button: int | str = 1) -> bool:
        resolved = resolve_mouse_button(button)

        return self._mouse_button_transition(
            resolved,
            pressed=False,
        )

    def _mouse_button_transition(
        self,
        button: int,
        *,
        pressed: bool,
    ) -> bool:
        """
        Transition state is reconstructed from the current event frame.

        This is intentionally kept separate from pygame.mouse so workers
        never have to access pygame.
        """
        # The transition flags are populated in begin_frame.
        if pressed:
            return button in self._mouse_pressed
        return button in self._mouse_released

    def wheel(self) -> tuple[int, int]:
        return self._wheel_x, self._wheel_y

    # ------------------------------------------------------------------
    # Frame state
    # ------------------------------------------------------------------

    def end_frame(self) -> None:
        """
        Reserved for future input features.

        Kept as a lifecycle hook so the input pipeline can grow without
        changing the game loop API.
        """
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_action(action: str) -> str:
        if not isinstance(action, str):
            raise TypeError("Action name must be a string.")

        action = action.strip().lower()

        if not action:
            raise ValueError("Action name cannot be empty.")

        return action

    @property
    def keys_down(self) -> frozenset[int]:
        return frozenset(self._keys_down)

    @property
    def mouse_buttons_down(self) -> frozenset[int]:
        return frozenset(self._mouse_down)