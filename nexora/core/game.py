from __future__ import annotations

from nexora.core.engine import Engine
from nexora.rendering.gpu import WindowMode
from nexora.scene import Scene, SceneManager


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
        window_mode: WindowMode | str | None = None,
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
        self._window_mode = window_mode
        self._vsync = vsync

        self._running = False
        self._shutdown = False
        self._scene: Scene | None = None
        self._scenes = SceneManager()

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(self) -> None:
        """
        Called automatically by Engine.initialize().
        """
        pass

    def shutdown(self) -> None:
        """
        Called automatically before the engine is shut down.
        """
        self._scenes.clear()
        self._scene = None

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self) -> None:
        """
        Start the game.
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
            window_mode=self._window_mode,
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
        """Handle an SDL3 event."""
        pass


    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Update input and game logic.
        """

        if self._scene is None:
            return

        # ----------------------------------------------------------
        # Keep UI viewport synchronized before input processing.
        # ----------------------------------------------------------

        if self.renderer is not None:
            self._scene.ui.set_viewport_size(
                self.renderer.width,
                self.renderer.height,
            )

        # ----------------------------------------------------------
        # UI input
        # ----------------------------------------------------------

        if self.input is not None:
            self._scene.update_input(
                self.input,
            )

        # ----------------------------------------------------------
        # Scene update
        # ----------------------------------------------------------

        self._scene.update(
            delta_time
        )
    
    def fixed_update(self, fixed_delta_time: float) -> None:
        """Update fixed-timestep game logic."""

        if self._scene is not None:
            self._scene.fixed_update(fixed_delta_time)

    def render(
        self,
        interpolation: float,
    ) -> None:
        if self._scene is None:
            return

        # ----------------------------------------------------------
        # ECS rendering
        # ----------------------------------------------------------

        self._scene.render(
            interpolation
        )

        # ----------------------------------------------------------
        # Scene node rendering
        # ----------------------------------------------------------

        self._scene.render_nodes(
            self.renderer,
            interpolation,
        )

        # ----------------------------------------------------------
        # UI
        # ----------------------------------------------------------

        self._scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        self._scene.ui.render(
            self.renderer,
        )
    # ==========================================================
    # WINDOW
    # ==========================================================

    def set_windowed(self) -> None:
        self._require_window()
        self.window.set_windowed()

    def set_borderless(self) -> None:
        self._require_window()
        self.window.set_borderless()

    def set_fullscreen(self) -> None:
        self._require_window()
        self.window.set_fullscreen()

    def set_window_mode(
        self,
        mode: WindowMode | str,
    ) -> None:
        self._require_window()
        self.window.set_window_mode(mode)

    def toggle_fullscreen(self) -> None:
        self._require_window()
        self.window.toggle_fullscreen()

    def set_vsync(self, enabled: bool) -> None:
        self._require_window()
        self.window.set_vsync(enabled)

    @property
    def window_mode(self) -> WindowMode:
        self._require_window()
        return self.window.window_mode

    @property
    def vsync(self) -> bool:
        self._require_window()
        return self.window.vsync

    @property
    def fullscreen(self) -> bool:
        self._require_window()
        return self.window.is_fullscreen

    def _require_window(self):
        if self.window is None:
            raise RuntimeError(
                "Game has not been started."
            )

    # ==========================================================
    # ENGINE SERVICES
    # ==========================================================

    @property
    def scenes(self) -> SceneManager:
        return self._scenes

    @property
    def scene(self) -> Scene | None:
        return self._scenes.active_scene

    @scene.setter
    def scene(self, value: Scene | None) -> None:
        if value is self._scene:
            return

        if self._scene is not None:
            self._scene.destroy()

        self._scene = value

        if value is not None:
            if not self._scenes.is_loaded(value.name):
                self._scenes.load(value)

            if self._scenes.active_scene is not value:
                self._scenes.activate(value.name)

    @property
    def audio(self):
        if self.engine is None:
            raise RuntimeError("Game has not been started.")

        return self.engine.audio

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