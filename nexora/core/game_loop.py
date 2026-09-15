from __future__ import annotations

from contextlib import nullcontext
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

    All frame timing is handled by the central Time instance.
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

        self.target_fps = int(
            target_fps
        )

        if fixed_delta_time <= 0.0:
            raise ValueError(
                "fixed_delta_time must be greater than zero"
            )

        # ------------------------------------------------------
        # Central timing system
        # ------------------------------------------------------

        self.time = Time(
            fixed_delta_time=float(
                fixed_delta_time
            ),
            max_delta_time=0.25,
        )

        # ------------------------------------------------------
        # Engine services
        # ------------------------------------------------------

        self.input = engine.input
        self.renderer = engine.renderer
        self.gpu_context = engine.gpu_context
        self.audio = engine.audio

        self.running = False

        # ------------------------------------------------------
        # FPS limiting
        # ------------------------------------------------------

        self._frame_duration = (
            1.0 / self.target_fps
            if self.target_fps > 0
            else 0.0
        )

    # ==========================================================
    # TIMING PROPERTIES
    # ==========================================================

    @property
    def delta_time(
        self,
    ) -> float:
        return self.time.delta_time

    @property
    def unscaled_delta_time(
        self,
    ) -> float:
        return self.time.unscaled_delta_time

    @property
    def fixed_delta_time(
        self,
    ) -> float:
        return self.time.fixed_delta_time

    @property
    def total_time(
        self,
    ) -> float:
        return self.time.total_time

    @property
    def frame(
        self,
    ) -> int:
        return self.time.frame

    @property
    def interpolation(
        self,
    ) -> float:
        return self.time.interpolation

    # ==========================================================
    # MAIN LOOP
    # ==========================================================

    def run(
        self,
    ) -> None:
        if self.running:
            return

        self.running = True

        self.time.reset()

        try:
            while self.running:
                frame_start = (
                    time.perf_counter()
                )

                # --------------------------------------------------
                # Timing
                # --------------------------------------------------

                self.time.begin_frame()

                # --------------------------------------------------
                # SDL events
                # --------------------------------------------------

                events = list(
                    self.gpu_context.poll_events()
                )

                self.input.begin_frame(
                    events
                )

                # --------------------------------------------------
                # Optional engine services
                # --------------------------------------------------

                console = getattr(
                    self.engine,
                    "console",
                    None,
                )

                debug_overlay = getattr(
                    self.engine,
                    "debug_overlay",
                    None,
                )

                action_pressed = getattr(
                    self.input,
                    "action_pressed",
                    None,
                )

                # --------------------------------------------------
                # Render scope helper
                # --------------------------------------------------
                #
                # Real Renderer has overlay_scope().
                #
                # Lightweight test renderers may not implement it.
                # In that case nullcontext() keeps the old behavior.
                # --------------------------------------------------

                def overlay_scope():
                    factory = getattr(
                        self.renderer,
                        "overlay_scope",
                        None,
                    )

                    if factory is None:
                        return nullcontext()

                    return factory()

                # --------------------------------------------------
                # Global engine input
                # --------------------------------------------------

                if (
                    console is not None
                    and getattr(
                        action_pressed,
                        "debug_console",
                        False,
                    )
                ):
                    console.toggle()

                if (
                    debug_overlay is not None
                    and getattr(
                        action_pressed,
                        "debug_overlay",
                        False,
                    )
                ):
                    debug_overlay.toggle()

                if (
                    debug_overlay is not None
                    and getattr(
                        action_pressed,
                        "physics_debug",
                        False,
                    )
                ):
                    physics_debug = getattr(
                        debug_overlay,
                        "physics",
                        None,
                    )

                    if physics_debug is not None:
                        physics_debug.toggle()

                # --------------------------------------------------
                # Debug console update
                # --------------------------------------------------

                if console is not None:
                    console.update(
                        self.time.unscaled_delta_time
                    )

                # --------------------------------------------------
                # Debug overlay update
                # --------------------------------------------------

                if debug_overlay is not None:
                    debug_overlay.update(
                        self.time.unscaled_delta_time
                    )

                # --------------------------------------------------
                # Engine + game event handling
                # --------------------------------------------------

                for event in events:
                    if self._handle_engine_event(
                        event
                    ):
                        break

                    if not self.running:
                        break

                    if (
                        console is not None
                        and console.consumes_event(
                            event
                        )
                    ):
                        continue

                    self.game.handle_event(
                        event
                    )

                # --------------------------------------------------
                # Quit handling
                # --------------------------------------------------

                if not self.running:
                    if console is not None:
                        console.end_frame()

                    self.input.end_frame()
                    break

                # --------------------------------------------------
                # Variable update
                # --------------------------------------------------

                self.game.update(
                    self.time.delta_time
                )

                # --------------------------------------------------
                # Fixed update
                # --------------------------------------------------

                while self.time.should_fixed_update():
                    self.game.fixed_update(
                        self.time.fixed_delta_time
                    )

                    self.time.consume_fixed_update()

                    if not self.running:
                        break

                if not self.running:
                    if console is not None:
                        console.end_frame()

                    self.input.end_frame()
                    break

                # --------------------------------------------------
                # Audio
                # --------------------------------------------------

                self.audio.player.update()

                # --------------------------------------------------
                # Render
                # --------------------------------------------------

                if self.renderer.begin_frame():
                    try:
                        # ------------------------------------------
                        # Game / Scene
                        # ------------------------------------------

                        self.game.render(
                            self.time.interpolation
                        )

                        # ------------------------------------------
                        # Global debug overlay
                        # ------------------------------------------

                        if debug_overlay is not None:
                            with overlay_scope():
                                debug_overlay.render(
                                    self.renderer
                                )

                        # ------------------------------------------
                        # Global debug console
                        # ------------------------------------------

                        if console is not None:
                            with overlay_scope():
                                console.render(
                                    self.renderer
                                )

                    finally:
                        self.renderer.end_frame()

                # --------------------------------------------------
                # End input frame
                # --------------------------------------------------

                if console is not None:
                    console.end_frame()

                self.input.end_frame()

                # --------------------------------------------------
                # FPS limiter
                # --------------------------------------------------

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
                        time.sleep(
                            remaining
                        )

        finally:
            self.running = False

    # ==========================================================
    # ENGINE EVENT HANDLING
    # ==========================================================

    def _handle_engine_event(
        self,
        event,
    ) -> bool:
        """
        Handle engine-level SDL events.

        Returns True when the event was consumed by the engine.
        """

        event_type = getattr(
            event,
            "type",
            None,
        )

        # ------------------------------------------------------
        # Global SDL quit
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_QUIT
        ):
            self.stop()
            return True

        # ------------------------------------------------------
        # Window close request
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_WINDOW_CLOSE_REQUESTED
        ):
            self.stop()
            return True

        # ------------------------------------------------------
        # Window pixel size changed
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED
        ):
            self._handle_resize_event(
                event
            )

            return False

        # ------------------------------------------------------
        # Window resized
        # ------------------------------------------------------

        if (
            event_type
            == sdl3.SDL_EVENT_WINDOW_RESIZED
        ):
            self._handle_resize_event(
                event
            )

            return False

        return False

    # ==========================================================
    # WINDOW RESIZE
    # ==========================================================

    def _handle_resize_event(
        self,
        event,
    ) -> None:
        try:
            width = int(
                event.window.data1
            )

            height = int(
                event.window.data2
            )

            if (
                width <= 0
                or height <= 0
            ):
                return

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

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
    ) -> None:
        self.running = False