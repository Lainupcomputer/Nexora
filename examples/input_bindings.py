from __future__ import annotations

import time

from nexora.input import InputManager
from nexora.rendering.gpu.context import GPUContext
from nexora.threading.context import ThreadContext


def main() -> None:
    print("=" * 60)
    print(" Nexora Input Bindings Example")
    print("=" * 60)
    print()
    print("Testing TOML key bindings")
    print()
    print("W / UP     -> move_up")
    print("S / DOWN   -> move_down")
    print("A / LEFT   -> move_left")
    print("D / RIGHT  -> move_right")
    print("SPACE      -> jump")
    print("E          -> interact")
    print("ESC        -> exit")
    print()

    ThreadContext.initialize()

    context = None
    input_manager = None

    try:
        # ------------------------------------------------------
        # Window
        # ------------------------------------------------------

        context = GPUContext(
            960,
            540,
            title="Nexora - Input Bindings",
            debug=True,
            vsync=True,
        )

        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        input_manager = InputManager(
            settings_path="settings",
            defaults_path=(
                "nexora/core/defaults/keybinds.toml"
            ),
        )

        input_manager.initialize(
            context.window,
        )

        print("Input initialized.")
        print()

        running = True

        while running:
            # --------------------------------------------------
            # Events
            # --------------------------------------------------

            events = list(
                context.poll_events()
            )

            input_manager.begin_frame(
                events
            )

            # --------------------------------------------------
            # Exit
            # --------------------------------------------------

            if input_manager.action_pressed.pause:
                running = False

            # --------------------------------------------------
            # Movement
            # --------------------------------------------------

            if input_manager.action_down.move_up:
                print("move_up")

            if input_manager.action_down.move_down:
                print("move_down")

            if input_manager.action_down.move_left:
                print("move_left")

            if input_manager.action_down.move_right:
                print("move_right")

            # --------------------------------------------------
            # Pressed
            # --------------------------------------------------

            if input_manager.action_pressed.jump:
                print("JUMP pressed")

            if input_manager.action_pressed.interact:
                print("INTERACT pressed")

            # --------------------------------------------------
            # Released
            # --------------------------------------------------

            if input_manager.action_released.jump:
                print("JUMP released")

            # --------------------------------------------------
            # Prevent unnecessary CPU usage
            # --------------------------------------------------

            time.sleep(
                0.001
            )

    finally:
        if input_manager is not None:
            input_manager.shutdown()

        if context is not None:
            context.shutdown()

        ThreadContext.shutdown()

        print()
        print("Done.")


if __name__ == "__main__":
    main()