from __future__ import annotations

from typing import Any

from nexora.core.engine import Engine


class Game:
    """
    Public high-level Nexora game API.

    A Game owns the engine and provides the simple entry point
    used by game projects.
    """

    def __init__(
        self,
        *,
        title: str = "Nexora",
        width: int = 1280,
        height: int = 720,
        target_fps: int = 144,
        fixed_delta_time: float = 1.0 / 60.0,
        resizable: bool = True,
        fullscreen: bool = False,
        vsync: bool = False,
    ) -> None:
        self.engine: Engine | None = None

        self.renderer = None
        self.input = None
        self.window = None

        self._title = title
        self._width = width
        self._height = height
        self._target_fps = target_fps
        self._fixed_delta_time = fixed_delta_time
        self._resizable = resizable
        self._fullscreen = fullscreen
        self._vsync = vsync

        self._running = False
        self._shutdown = False

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(self) -> None:
        """
        Called automatically by Engine.initialize().

        Override this in subclasses to initialize game-specific
        state, entities, assets, etc.
        """
        pass

    def shutdown(self) -> None:
        """
        Called automatically before the engine is shut down.

        Override this in subclasses for game-specific cleanup.
        """
        pass

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self) -> None:
        """
        Start the game.

        Engine initialization happens automatically and all
        engine/GPU/SDL resources are cleaned up when the game exits.
        """

        if self._shutdown:
            raise RuntimeError(
                "Cannot run a game that has already been shut down."
            )

        self.engine = Engine(
            self,
            width=self._width,
            height=self._height,
            title=self._title,
            target_fps=self._target_fps,
            fixed_delta_time=self._fixed_delta_time,
            resizable=self._resizable,
            fullscreen=self._fullscreen,
            vsync=self._vsync,
        )

        self._running = True

        try:
            self.engine.run()
        finally:
            self._running = False

            if self.engine is not None:
                self.engine.shutdown()

            self._shutdown = True

    # ==========================================================
    # CONTROL
    # ==========================================================

    def stop(self) -> None:
        """Stop the running game loop."""

        if self.engine is not None:
            self.engine.stop()

    def handle_event(self, event) -> None:
        """Handle an SDL3 event.

        Override this in a game subclass to react to input,
        window events, and other SDL3 events.
        """
        pass


    def update(self, delta_time: float) -> None:
        """Update game logic."""
        pass


    def fixed_update(self, fixed_delta_time: float) -> None:
        """Update fixed-timestep game logic."""
        pass


    def render(self) -> None:
        """Render the game."""
        pass


    # ==========================================================
    # ENGINE SERVICES
    # ==========================================================

    @property
    def assets(self):
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.assets

    @property
    def logger(self):
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.logger

    @property
    def time(self):
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.time

    @property
    def delta_time(self) -> float:
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.delta_time

    @property
    def total_time(self) -> float:
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.total_time

    @property
    def frame(self) -> int:
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.frame

    @property
    def running(self) -> bool:
        return self._running