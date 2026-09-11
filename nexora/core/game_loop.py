from __future__ import annotations

import time

import sdl3

from nexora.core.time import Time


class GameLoop:
    """
    Main Nexora engine loop.

    SDL3 handles:
        - window events
        - keyboard
        - mouse
        - GPU window events

    InputManager receives the same SDL3 event stream.
    """

    def __init__(
        self,
        engine,
        *,
        target_fps: int = 60,
        fixed_delta_time: float = 1.0 / 60.0,
    ):
        self.engine = engine
        self.game = engine.game

        self.target_fps = int(target_fps)
        self.fixed_delta_time = float(fixed_delta_time)

        if self.fixed_delta_time <= 0.0:
            raise ValueError(
                "fixed_delta_time must be greater than zero"
            )

        self.time = Time(self.fixed_delta_time)

        self.input = engine.input
        self.renderer = engine.renderer
        self.gpu_context = engine.gpu_context
        self.audio = engine.audio

        self.running = False

        self._last_time = 0.0
        self._accumulator = 0.0

        self._frame_duration = (
            1.0 / self.target_fps
            if self.target_fps > 0
            else 0.0
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        if self.running:
            return

        self.running = True

        self.input.initialize()

        self._last_time = time.perf_counter()
        self._accumulator = 0.0

        try:
            while self.running:
                frame_start = time.perf_counter()

                # ------------------------------------------------------
                # Timing
                # ------------------------------------------------------

                current_time = time.perf_counter()

                delta = current_time - self._last_time
                self._last_time = current_time

                # Prevent giant simulation jumps.
                delta = min(delta, 0.25)

                self._accumulator += delta

                self.time.begin_frame()

                # ------------------------------------------------------
                # SDL3 EVENTS
                # ------------------------------------------------------

                events = list(
                    self.gpu_context.poll_events()
                )

                # Central input processing.
                self.input.begin_frame(events)

                # Engine + game event processing.
                for event in events:
                    if self._handle_engine_event(event):
                        break

                    if not self.running:
                        break

                    self.game.handle_event(event)

                if not self.running:
                    self.input.end_frame()
                    break

                # ------------------------------------------------------
                # Fixed update
                # ------------------------------------------------------

                while self._accumulator >= self.fixed_delta_time:
                    self.game.update(
                        self.fixed_delta_time
                    )

                    self._accumulator -= self.fixed_delta_time


                # ------------------------------------------------------
                # Audio
                # ------------------------------------------------------

                self.audio.player.update()

                
                # ------------------------------------------------------
                # Render
                # ------------------------------------------------------

                if self.renderer.begin_frame():
                    try:
                        self.game.render()
                    finally:
                        self.renderer.end_frame()

                # ------------------------------------------------------
                # End input frame
                # ------------------------------------------------------

                self.input.end_frame()

                # ------------------------------------------------------
                # FPS limiter
                # ------------------------------------------------------

                if self._frame_duration > 0.0:
                    elapsed = (
                        time.perf_counter()
                        - frame_start
                    )

                    remaining = (
                        self._frame_duration
                        - elapsed
                    )

                    if remaining > 0.0:
                        time.sleep(remaining)

        finally:
            self.running = False

    # ------------------------------------------------------------------
    # Engine event handling
    # ------------------------------------------------------------------

    def _handle_engine_event(self, event) -> bool:
        """
        Returns True when the event was consumed by the engine.
        """

        event_type = getattr(event, "type", None)

        # --------------------------------------------------------------
        # Global SDL quit
        # --------------------------------------------------------------

        if event_type == sdl3.SDL_EVENT_QUIT:
            print("[SDL] SDL_EVENT_QUIT")
            self.stop()
            return True

        # --------------------------------------------------------------
        # Window close request
        # --------------------------------------------------------------

        if event_type == sdl3.SDL_EVENT_WINDOW_CLOSE_REQUESTED:
            print("[SDL] SDL_EVENT_WINDOW_CLOSE_REQUESTED")
            self.stop()
            return True

        # --------------------------------------------------------------
        # Window resize
        # --------------------------------------------------------------

        if event_type == sdl3.SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
            try:
                width = int(event.window.data1)
                height = int(event.window.data2)

                if width > 0 and height > 0:
                    self.renderer.resize(
                        width,
                        height,
                    )

            except (
                AttributeError,
                TypeError,
                ValueError,
            ):
                pass

            return False

        if event_type == sdl3.SDL_EVENT_WINDOW_RESIZED:
            try:
                width = int(event.window.data1)
                height = int(event.window.data2)

                if width > 0 and height > 0:
                    self.renderer.resize(
                        width,
                        height,
                    )

            except (
                AttributeError,
                TypeError,
                ValueError,
            ):
                pass

            return False

        return False

    # ------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self.running = False