from __future__ import annotations

from pathlib import Path
from typing import Iterable

import sdl3

from nexora.debug.logger import Logger

from nexora.input.action import (
    ActionState,
    ActionStateProxy,
)

from nexora.input.binding_store import (
    BindingStore,
)

from nexora.input.bindings import (
    Binding,
    BindingType,
    resolve_keyboard_key,
    resolve_mouse_button,
)

from nexora.threading.context import (
    ThreadContext,
)


class InputManager:
    """
    SDL3 based main-thread input manager.

    SDL3 events are collected on the engine/main thread.

    Worker threads never touch SDL directly. They only read the
    synchronized input state maintained here.
    """

    def __init__(
        self,
        logger: Logger | None = None,
        *,
        project_name: str = "Nexora",
        settings_path=...,
        defaults_path: str | Path | None = None,
        project_bindings_path: str | Path | None = None,
        mod_binding_paths: Iterable[
            str | Path
        ] = (),
    ):
        self.logger = logger
        self._window = None

        # ======================================================
        # Physical keyboard state
        # ======================================================

        self._keys_down: set[int] = set()
        self._keys_pressed: set[int] = set()
        self._keys_released: set[int] = set()

        # ======================================================
        # Physical mouse state
        # ======================================================

        self._mouse_down: set[int] = set()
        self._mouse_pressed: set[int] = set()
        self._mouse_released: set[int] = set()

        # ======================================================
        # Mouse position / movement
        # ======================================================

        self._mouse_x = 0.0
        self._mouse_y = 0.0

        self._mouse_dx = 0.0
        self._mouse_dy = 0.0

        self._wheel_x = 0.0
        self._wheel_y = 0.0

        # ======================================================
        # Text input
        # ======================================================

        self._text_input: list[str] = []

        self._text_input_active = False
        self._text_input_started = False
        self._text_input_stopped = False
        self._text_input_locks: set[int] = set()

        # ======================================================
        # Actions
        # ======================================================

        self._actions: dict[
            str,
            ActionState,
        ] = {}

        self._bindings: dict[
            str,
            list[Binding],
        ] = {}

        # ======================================================
        # Action capture
        # ======================================================
        #
        # Global engine tools such as the debug console can
        # temporarily suppress gameplay actions while still
        # allowing a small engine-level allowlist.
        # ======================================================

        self._action_capture_active = False
        self._action_capture_allowlist: set[str] = set()
        self._captured_action_state = ActionState()

        # ======================================================
        # Layered TOML binding storage
        # ======================================================

        store_kwargs = {
            "project_name": (
                project_name
            ),
            "defaults_path": (
                defaults_path
            ),
            "project_path": (
                project_bindings_path
            ),
            "mod_paths": (
                mod_binding_paths
            ),
        }

        if settings_path is not ...:
            store_kwargs[
                "settings_path"
            ] = settings_path

        self.binding_store = (
            BindingStore(
                **store_kwargs
            )
        )

        # ======================================================
        # Dynamic action API
        # ======================================================

        self.action_down = (
            ActionStateProxy(
                self,
                "down",
            )
        )

        self.action_pressed = (
            ActionStateProxy(
                self,
                "pressed",
            )
        )

        self.action_released = (
            ActionStateProxy(
                self,
                "released",
            )
        )

        self._initialized = False
        self._focused = True

        self.load_bindings()

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(
        self,
        window=None,
    ) -> None:
        ThreadContext.assert_main_thread(
            "InputManager.initialize() "
            "must run on the main thread"
        )

        if window is not None:
            self._window = window

        self._initialized = True

    # ==========================================================
    # BINDING API
    # ==========================================================

    def bind(
        self,
        action: str,
        binding: Binding | str | int,
        *,
        binding_type: BindingType = (
            BindingType.KEYBOARD
        ),
    ) -> None:
        if (
            not isinstance(
                action,
                str,
            )
            or not action
        ):
            raise ValueError(
                "action must be a non-empty string"
            )

        if isinstance(
            binding,
            Binding,
        ):
            resolved = binding

        elif (
            binding_type
            is BindingType.KEYBOARD
        ):
            resolved = Binding(
                BindingType.KEYBOARD,
                resolve_keyboard_key(
                    binding
                ),
            )

        elif (
            binding_type
            is BindingType.MOUSE
        ):
            resolved = Binding(
                BindingType.MOUSE,
                resolve_mouse_button(
                    binding
                ),
            )

        else:
            raise ValueError(
                "Unsupported binding type: "
                f"{binding_type}"
            )

        self._bindings.setdefault(
            action,
            [],
        ).append(
            resolved
        )

        if action not in self._actions:
            self._actions[
                action
            ] = ActionState()

    def bind_key(
        self,
        action: str,
        key: str | int,
    ) -> None:
        self.bind(
            action,
            resolve_keyboard_key(
                key
            ),
            binding_type=(
                BindingType.KEYBOARD
            ),
        )

    def bind_mouse(
        self,
        action: str,
        button: str | int,
    ) -> None:
        self.bind(
            action,
            resolve_mouse_button(
                button
            ),
            binding_type=(
                BindingType.MOUSE
            ),
        )

    def unbind(
        self,
        action: str,
        binding: (
            Binding
            | str
            | int
            | None
        ) = None,
    ) -> None:
        if action not in self._bindings:
            return

        if binding is None:
            self._bindings.pop(
                action,
                None,
            )

            self._actions.pop(
                action,
                None,
            )

            return

        if isinstance(
            binding,
            Binding,
        ):
            resolved = binding

        else:
            candidates = []

            try:
                candidates.append(
                    Binding(
                        BindingType.KEYBOARD,
                        resolve_keyboard_key(
                            binding
                        ),
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

            try:
                candidates.append(
                    Binding(
                        BindingType.MOUSE,
                        resolve_mouse_button(
                            binding
                        ),
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

            current = (
                self._bindings[
                    action
                ]
            )

            self._bindings[
                action
            ] = [
                item
                for item in current
                if item not in candidates
            ]

            if not self._bindings[
                action
            ]:
                self._bindings.pop(
                    action,
                    None,
                )

                self._actions.pop(
                    action,
                    None,
                )

            return

        self._bindings[
            action
        ] = [
            item
            for item
            in self._bindings[
                action
            ]
            if item != resolved
        ]

        if not self._bindings[
            action
        ]:
            self._bindings.pop(
                action,
                None,
            )

            self._actions.pop(
                action,
                None,
            )

    def clear_bindings(
        self,
    ) -> None:
        self._bindings.clear()
        self._actions.clear()

    def load_bindings(
        self,
    ) -> None:
        loaded = (
            self.binding_store.load()
        )

        previous = (
            self._actions
        )

        self._bindings = {
            action: list(
                bindings
            )
            for action, bindings
            in loaded.items()
        }

        self._actions = {
            action: previous.get(
                action,
                ActionState(),
            )
            for action in self._bindings
        }

    def reload_bindings(
        self,
    ) -> None:
        self.load_bindings()

    def save_bindings(
        self,
    ) -> None:
        self.binding_store.save(
            self._bindings
        )

    def reset_bindings(
        self,
    ) -> None:
        self.binding_store.reset_user()

        self.load_bindings()

    @property
    def settings_path(
        self,
    ) -> Path | None:
        return (
            self.binding_store.settings_path
        )

    @property
    def keybinds_path(
        self,
    ) -> Path | None:
        return (
            self.binding_store.user_path
        )

    # ==========================================================
    # FRAME PROCESSING
    # ==========================================================

    def begin_frame(
        self,
        events: Iterable[
            object
        ] = (),
    ) -> None:
        ThreadContext.assert_main_thread(
            "InputManager.begin_frame() "
            "must run on the main thread"
        )

        if not self._initialized:
            self.initialize()

        for state in self._actions.values():
            state.begin_frame()

        self._keys_pressed.clear()
        self._keys_released.clear()

        self._mouse_pressed.clear()
        self._mouse_released.clear()

        self._mouse_dx = 0.0
        self._mouse_dy = 0.0

        self._wheel_x = 0.0
        self._wheel_y = 0.0

        self._text_input.clear()

        self._text_input_started = False
        self._text_input_stopped = False

        for event in events:
            self._process_event(
                event
            )

        self._update_action_states()

    # ==========================================================
    # SDL EVENTS
    # ==========================================================

    def _process_event(
        self,
        event: object,
    ) -> None:
        event_type = getattr(
            event,
            "type",
            None,
        )

        # ------------------------------------------------------
        # Keyboard
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_KEY_DOWN
        ):
            keyboard = event.key

            scancode = int(
                keyboard.scancode
            )

            if (
                scancode
                not in self._keys_down
            ):
                self._keys_pressed.add(
                    scancode
                )

            self._keys_down.add(
                scancode
            )

            return

        if (
            event_type
            == sdl3.SDL_EVENT_KEY_UP
        ):
            keyboard = event.key

            scancode = int(
                keyboard.scancode
            )

            self._keys_down.discard(
                scancode
            )

            self._keys_released.add(
                scancode
            )

            return

        # ------------------------------------------------------
        # Text input
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_TEXT_INPUT
        ):
            text_event = event.text

            text = (
                text_event.text
            )

            if isinstance(
                text,
                bytes,
            ):
                text = text.decode(
                    "utf-8",
                    errors="replace",
                )

            if text:
                self._text_input.append(
                    str(
                        text
                    )
                )

            return

        # ------------------------------------------------------
        # Mouse motion
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_MOUSE_MOTION
        ):
            motion = event.motion

            self._mouse_x = float(
                motion.x
            )

            self._mouse_y = float(
                motion.y
            )

            self._mouse_dx += float(
                motion.xrel
            )

            self._mouse_dy += float(
                motion.yrel
            )

            return

        # ------------------------------------------------------
        # Mouse buttons
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_MOUSE_BUTTON_DOWN
        ):
            mouse = event.button

            button = int(
                mouse.button
            )

            if (
                button
                not in self._mouse_down
            ):
                self._mouse_pressed.add(
                    button
                )

            self._mouse_down.add(
                button
            )

            self._mouse_x = float(
                mouse.x
            )

            self._mouse_y = float(
                mouse.y
            )

            return

        if (
            event_type
            == sdl3.SDL_EVENT_MOUSE_BUTTON_UP
        ):
            mouse = event.button

            button = int(
                mouse.button
            )

            self._mouse_down.discard(
                button
            )

            self._mouse_released.add(
                button
            )

            self._mouse_x = float(
                mouse.x
            )

            self._mouse_y = float(
                mouse.y
            )

            return

        # ------------------------------------------------------
        # Mouse wheel
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_MOUSE_WHEEL
        ):
            wheel = event.wheel

            self._wheel_x += float(
                wheel.x
            )

            self._wheel_y += float(
                wheel.y
            )

            return

        # ------------------------------------------------------
        # Window focus
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_WINDOW_FOCUS_LOST
        ):
            self._focused = False

            self._keys_down.clear()
            self._mouse_down.clear()

            if self._text_input_active:
                if self._window is not None:
                    sdl3.SDL_StopTextInput(
                        self._window
                    )

                self._text_input_active = False

            return

        if (
            event_type
            == sdl3.SDL_EVENT_WINDOW_FOCUS_GAINED
        ):
            self._focused = True

            return

    # ==========================================================
    # ACTIONS
    # ==========================================================

    def _update_action_states(
        self,
    ) -> None:
        for action, bindings in self._bindings.items():
            state = (
                self._actions[
                    action
                ]
            )

            down = False
            pressed = False
            released = False

            for binding in bindings:
                if (
                    binding.type
                    is BindingType.KEYBOARD
                ):
                    code = (
                        binding.code
                    )

                    if code in self._keys_down:
                        down = True

                    if code in self._keys_pressed:
                        pressed = True

                    if code in self._keys_released:
                        released = True

                elif (
                    binding.type
                    is BindingType.MOUSE
                ):
                    button = (
                        binding.code
                    )

                    if button in self._mouse_down:
                        down = True

                    if button in self._mouse_pressed:
                        pressed = True

                    if button in self._mouse_released:
                        released = True

            state.down = down
            state.pressed = pressed
            state.released = released

    # ==========================================================
    # ACTION CAPTURE
    # ==========================================================

    def set_action_capture(
        self,
        active: bool,
        *,
        allowed_actions: Iterable[str] = (),
    ) -> None:
        self._action_capture_active = bool(active)

        if self._action_capture_active:
            self._action_capture_allowlist = {
                str(action)
                for action in allowed_actions
            }
        else:
            self._action_capture_allowlist.clear()

    @property
    def action_capture_active(
        self,
    ) -> bool:
        return self._action_capture_active

    # ==========================================================
    # TEXT INPUT
    # ==========================================================

    def acquire_text_input(
        self,
        owner: object,
    ) -> None:
        """Keep SDL text input enabled until *owner* releases it."""
        self._text_input_locks.add(
            id(owner)
        )
        self.start_text_input()

    def release_text_input(
        self,
        owner: object,
    ) -> None:
        """Release a persistent text-input request."""
        self._text_input_locks.discard(
            id(owner)
        )

        if not self._text_input_locks:
            self.stop_text_input()

    @property
    def text_input_locked(
        self,
    ) -> bool:
        return bool(
            self._text_input_locks
        )

    def start_text_input(
        self,
    ) -> None:
        ThreadContext.assert_main_thread(
            "InputManager.start_text_input() "
            "must run on the main thread"
        )

        if self._text_input_active:
            return

        if self._window is None:
            raise RuntimeError(
                "InputManager has no SDL window."
            )

        sdl3.SDL_StartTextInput(
            self._window
        )

        self._text_input_active = True
        self._text_input_started = True

    def stop_text_input(
        self,
    ) -> None:
        ThreadContext.assert_main_thread(
            "InputManager.stop_text_input() "
            "must run on the main thread"
        )

        if self._text_input_locks:
            return

        if not self._text_input_active:
            return

        if self._window is None:
            return

        sdl3.SDL_StopTextInput(
            self._window
        )

        self._text_input_active = False
        self._text_input_stopped = True

    @property
    def text_input(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._text_input
        )

    @property
    def text_input_active(
        self,
    ) -> bool:
        return (
            self._text_input_active
        )

    @property
    def text_input_started(
        self,
    ) -> bool:
        return (
            self._text_input_started
        )

    @property
    def text_input_stopped(
        self,
    ) -> bool:
        return (
            self._text_input_stopped
        )

    # ==========================================================
    # DIRECT KEYBOARD API
    # ==========================================================

    def key_down(
        self,
        key: str | int,
    ) -> bool:
        return (
            resolve_keyboard_key(
                key
            )
            in self._keys_down
        )

    def key_pressed(
        self,
        key: str | int,
    ) -> bool:
        return (
            resolve_keyboard_key(
                key
            )
            in self._keys_pressed
        )

    def key_released(
        self,
        key: str | int,
    ) -> bool:
        return (
            resolve_keyboard_key(
                key
            )
            in self._keys_released
        )

    # ==========================================================
    # DIRECT MOUSE API
    # ==========================================================

    def mouse_down(
        self,
        button: str | int,
    ) -> bool:
        return (
            resolve_mouse_button(
                button
            )
            in self._mouse_down
        )

    def mouse_pressed(
        self,
        button: str | int,
    ) -> bool:
        return (
            resolve_mouse_button(
                button
            )
            in self._mouse_pressed
        )

    def mouse_released(
        self,
        button: str | int,
    ) -> bool:
        return (
            resolve_mouse_button(
                button
            )
            in self._mouse_released
        )

    # ==========================================================
    # GENERIC API
    # ==========================================================

    def is_down(
        self,
        key: str | int,
    ) -> bool:
        return self.key_down(
            key
        )

    def is_pressed(
        self,
        key: str | int,
    ) -> bool:
        return self.key_pressed(
            key
        )

    def is_released(
        self,
        key: str | int,
    ) -> bool:
        return self.key_released(
            key
        )

    # ==========================================================
    # ACTION API
    # ==========================================================

    def action_state(
        self,
        action: str,
    ) -> ActionState:
        if (
            self._action_capture_active
            and action not in self._action_capture_allowlist
        ):
            return self._captured_action_state

        if action not in self._actions:
            self._actions[
                action
            ] = ActionState()

        return (
            self._actions[
                action
            ]
        )

    def action(
        self,
        action: str,
    ) -> ActionState:
        return self.action_state(
            action
        )

    def actions(
        self,
    ) -> dict[
        str,
        ActionState,
    ]:
        return self._actions

    def is_action_down(
        self,
        action: str,
    ) -> bool:
        return (
            self.action_state(
                action
            ).down
        )

    def is_action_pressed(
        self,
        action: str,
    ) -> bool:
        return (
            self.action_state(
                action
            ).pressed
        )

    def is_action_released(
        self,
        action: str,
    ) -> bool:
        return (
            self.action_state(
                action
            ).released
        )

    # ==========================================================
    # MOUSE STATE
    # ==========================================================

    @property
    def mouse_position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self._mouse_x,
            self._mouse_y,
        )

    @property
    def mouse_delta(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self._mouse_dx,
            self._mouse_dy,
        )

    @property
    def wheel(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self._wheel_x,
            self._wheel_y,
        )

    # ==========================================================
    # STATE ACCESS
    # ==========================================================

    @property
    def keys_down(
        self,
    ) -> frozenset[int]:
        return frozenset(
            self._keys_down
        )

    @property
    def keys_pressed(
        self,
    ) -> frozenset[int]:
        return frozenset(
            self._keys_pressed
        )

    @property
    def keys_released(
        self,
    ) -> frozenset[int]:
        return frozenset(
            self._keys_released
        )

    @property
    def mouse_buttons_down(
        self,
    ) -> frozenset[int]:
        return frozenset(
            self._mouse_down
        )

    @property
    def focused(
        self,
    ) -> bool:
        return (
            self._focused
        )

    # ==========================================================
    # END FRAME
    # ==========================================================

    def end_frame(
        self,
    ) -> None:
        ThreadContext.assert_main_thread(
            "InputManager.end_frame() "
            "must run on the main thread"
        )