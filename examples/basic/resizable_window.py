from __future__ import annotations

import time

from nexora import Game


class WindowTestGame(Game):
    """
    Public Game API window management test.

    Controls:
        1 = Windowed
        2 = Borderless
        3 = Fullscreen
        F = Toggle Fullscreen
        V = Toggle VSync
        ESC = Exit
    """

    def __init__(self):
        super().__init__(
            title="Nexora - Game Window Test",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
            window_mode="windowed",
            vsync=True,
        )

        self._last_status = None
        self._start_time = 0.0

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self):
        self._start_time = time.perf_counter()

        print()
        print("=" * 40)
        print(" Nexora Game Window API Test")
        print("=" * 40)
        print()

        print(f"Initial mode: {self.window_mode.value}")
        print(f"Initial VSync: {self.vsync}")
        print()

        print("Controls:")
        print("  1 = Windowed")
        print("  2 = Borderless")
        print("  3 = Fullscreen")
        print("  F = Toggle Fullscreen")
        print("  V = Toggle VSync")
        print("  ESC = Exit")
        print()

        self._print_status()

    # ==========================================================
    # EVENTS
    # ==========================================================

    def handle_event(self, event):
        """
        Handle keyboard input through the public Game API.
        """

        # SDL3 keyboard event
        if event.type == 0x300:  # SDL_EVENT_KEY_DOWN
            key = event.key.key

            # SDL keycodes
            # 1
            if key == ord("1"):
                self.set_windowed()
                self._print_status()

            # 2
            elif key == ord("2"):
                self.set_borderless()
                self._print_status()

            # 3
            elif key == ord("3"):
                self.set_fullscreen()
                self._print_status()

            # F
            elif key == ord("f"):
                self.toggle_fullscreen()
                self._print_status()

            # V
            elif key == ord("v"):
                self.set_vsync(not self.vsync)
                self._print_status()

            # ESC
            elif key == 27:
                self.stop()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(self, delta_time):
        # Automatically stop after 10 minutes if something
        # goes wrong and the test is left running.
        if time.perf_counter() - self._start_time > 600:
            print()
            print("Safety timeout reached.")
            self.stop()

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self):
        """
        Minimal render test.

        The important part of this test is the public window API,
        not rendering functionality.
        """
        pass


    # ==========================================================
    # STATUS
    # ==========================================================

    def _print_status(self):
        status = (
            self.window_mode.value,
            self.vsync,
            self.renderer.width,
            self.renderer.height,
        )

        if status == self._last_status:
            return

        self._last_status = status

        print(
            f"Mode: {self.window_mode.value}"
        )

        print(
            f"VSync: {self.vsync}"
        )

        print(
            f"Size: "
            f"{self.renderer.width} x "
            f"{self.renderer.height}"
        )

        print()


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    game = WindowTestGame()

    try:
        game.run()

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")

    finally:
        print()
        print("=" * 40)
        print(" Game window test finished.")
        print("=" * 40)