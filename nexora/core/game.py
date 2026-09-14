from __future__ import annotations

from pathlib import Path

from nexora.core.engine import Engine
from nexora.rendering.gpu import WindowMode
from nexora.scene import (
    Scene,
    SceneManager,
)
from nexora.settings import SettingsStore


class Game:
    """
    Public high-level Nexora game API.

    SceneManager is the single source of truth for scene state.

    There is intentionally no separate Game._scene reference.

    Scene flow:

        Game
            -> SceneManager
                -> active_scene

    Scene stack rendering:

        Game
          PAUSED
        Pause
          ACTIVE

    Both scenes are rendered, but only the active scene receives
    input and regular updates.
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
        settings_path: str | Path = "settings.json",
        settings_defaults: dict | None = None,
    ) -> None:
        # ======================================================
        # Engine services
        # ======================================================

        self.engine: Engine | None = None

        self.renderer = None
        self.input = None
        self.window = None

        # ======================================================
        # Configuration
        # ======================================================

        self._title = str(
            title
        )

        self._width = int(
            width
        )

        self._height = int(
            height
        )

        self._target_fps = int(
            target_fps
        )

        self._fixed_delta_time = float(
            fixed_delta_time
        )

        self._resizable = bool(
            resizable
        )

        self._fullscreen = bool(
            fullscreen
        )

        self._window_mode = (
            window_mode
        )

        self._vsync = bool(
            vsync
        )

        # ======================================================
        # Runtime state
        # ======================================================

        self._running = False
        self._shutdown = False

        # ======================================================
        # Scenes
        # ======================================================

        self._scenes = SceneManager()

        # ======================================================
        # Settings
        # ======================================================

        self._settings = SettingsStore(
            settings_path,
            defaults=settings_defaults,
        )

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        """
        Called automatically by Engine.initialize().

        Override in a game subclass.
        """

        pass

    def shutdown(
        self,
    ) -> None:
        """
        Called automatically before the engine is shut down.

        All loaded scenes are destroyed here.
        """

        self._scenes.clear()

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
    ) -> None:
        """
        Start the game.
        """

        if self._shutdown:
            raise RuntimeError(
                "Cannot run a game that has already "
                "been shut down."
            )

        self.engine = Engine(
            self,
            width=self._width,
            height=self._height,
            title=self._title,
            target_fps=self._target_fps,
            fixed_delta_time=(
                self._fixed_delta_time
            ),
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

    def stop(
        self,
    ) -> None:
        """
        Stop the running game loop.
        """

        if self.engine is not None:
            self.engine.stop()

    # ==========================================================
    # EVENTS
    # ==========================================================

    def handle_event(
        self,
        event,
    ) -> None:
        """
        Handle an SDL3 event.

        Override in a game subclass when raw SDL events are
        required.
        """

        pass

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Update the currently active scene.

        Only SceneManager.active_scene receives:

            UI input
            node update
            ECS update

        Paused scenes in the scene stack remain loaded but do
        not update.
        """

        scene = (
            self._scenes.active_scene
        )

        if scene is None:
            return

        # ------------------------------------------------------
        # Keep UI viewport synchronized before input handling.
        # ------------------------------------------------------

        if self.renderer is not None:
            scene.ui.set_viewport_size(
                self.renderer.width,
                self.renderer.height,
            )

        # ------------------------------------------------------
        # UI input
        # ------------------------------------------------------

        if self.input is not None:
            scene.update_input(
                self.input
            )

        # ------------------------------------------------------
        # Scene update
        # ------------------------------------------------------

        scene.update(
            delta_time
        )

    # ==========================================================
    # FIXED UPDATE
    # ==========================================================

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        """
        Run fixed-timestep logic for the active scene only.
        """

        scene = (
            self._scenes.active_scene
        )

        if scene is None:
            return

        scene.fixed_update(
            fixed_delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        """
        Render the complete active scene stack.

        Example:

            Game       PAUSED
            Pause      ACTIVE

        Rendering order:

            Game
              ↓
            Pause

        This allows pause menus, inventories and other overlay
        scenes to be rendered on top of the game while the game
        itself remains paused.
        """

        if self.renderer is None:
            return

        render_scenes = (
            self._get_render_scenes()
        )

        if not render_scenes:
            return

        for scene in render_scenes:
            self._render_scene(
                scene,
                interpolation,
            )

    # ==========================================================
    # SCENE RENDERING
    # ==========================================================

    def _get_render_scenes(
        self,
    ) -> tuple[
        Scene,
        ...
    ]:
        """
        Return scenes in back-to-front render order.

        SceneManager.stack contains the paused scenes below the
        active scene.

        Example:

            stack:
                Game
                Pause

            active:
                Settings

            result:
                Game
                Pause
                Settings
        """

        active_scene = (
            self._scenes.active_scene
        )

        if active_scene is None:
            return ()

        return (
            *self._scenes.stack,
            active_scene,
        )

    def _render_scene(
        self,
        scene: Scene,
        interpolation: float,
    ) -> None:
        """
        Render one scene using the normal Nexora scene pipeline.
        """

        # ------------------------------------------------------
        # Synchronize UI viewport
        # ------------------------------------------------------

        scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        # ------------------------------------------------------
        # ECS rendering
        # ------------------------------------------------------

        scene.render(
            interpolation
        )

        # ------------------------------------------------------
        # Node rendering
        # ------------------------------------------------------

        scene.render_nodes(
            self.renderer,
            interpolation,
        )

        # ------------------------------------------------------
        # UI rendering
        # ------------------------------------------------------

        scene.ui.render(
            self.renderer
        )

    # ==========================================================
    # WINDOW
    # ==========================================================

    def set_windowed(
        self,
    ) -> None:
        self._require_window()

        self.window.set_windowed()

    def set_borderless(
        self,
    ) -> None:
        self._require_window()

        self.window.set_borderless()

    def set_fullscreen(
        self,
    ) -> None:
        self._require_window()

        self.window.set_fullscreen()

    def set_window_mode(
        self,
        mode: WindowMode | str,
    ) -> None:
        self._require_window()

        self.window.set_window_mode(
            mode
        )

    def toggle_fullscreen(
        self,
    ) -> None:
        self._require_window()

        self.window.toggle_fullscreen()

    def set_vsync(
        self,
        enabled: bool,
    ) -> None:
        self._require_window()

        self.window.set_vsync(
            enabled
        )

    # ==========================================================
    # SETTINGS
    # ==========================================================

    @property
    def settings(
        self,
    ) -> SettingsStore:
        return self._settings

    # ==========================================================
    # WINDOW PROPERTIES
    # ==========================================================

    @property
    def window_mode(
        self,
    ) -> WindowMode:
        self._require_window()

        return (
            self.window.window_mode
        )

    @property
    def vsync(
        self,
    ) -> bool:
        self._require_window()

        return bool(
            self.window.vsync
        )

    @property
    def fullscreen(
        self,
    ) -> bool:
        self._require_window()

        return bool(
            self.window.is_fullscreen
        )

    def _require_window(
        self,
    ) -> None:
        if self.window is None:
            raise RuntimeError(
                "Game has not been started."
            )

    # ==========================================================
    # SCENES
    # ==========================================================

    @property
    def scenes(
        self,
    ) -> SceneManager:
        """
        Access the game's SceneManager.
        """

        return self._scenes

    @property
    def scene(
        self,
    ) -> Scene | None:
        """
        Return the currently active scene.

        This is only a convenience alias for:

            game.scenes.active_scene

        SceneManager remains the single source of truth.
        """

        return (
            self._scenes.active_scene
        )

    @scene.setter
    def scene(
        self,
        value: Scene | None,
    ) -> None:
        """
        Convenience setter for the active scene.

        Existing code such as:

            self.scene = Scene("Game")

        remains supported.

        Internally this always goes through SceneManager.

        Setting scene to None deactivates the current scene
        without destroying it.
        """

        # ------------------------------------------------------
        # Deactivate
        # ------------------------------------------------------

        if value is None:
            self._scenes.deactivate()
            return

        # ------------------------------------------------------
        # Type validation
        # ------------------------------------------------------

        if not isinstance(
            value,
            Scene,
        ):
            raise TypeError(
                "scene must be a Scene instance or None."
            )

        # ------------------------------------------------------
        # Already active
        # ------------------------------------------------------

        if (
            self._scenes.active_scene
            is value
        ):
            return

        # ------------------------------------------------------
        # Ensure loaded
        # ------------------------------------------------------

        loaded_scene = (
            self._scenes.get(
                value.name
            )
        )

        if loaded_scene is None:
            self._scenes.load(
                value
            )

        elif loaded_scene is not value:
            raise ValueError(
                f"A different scene named "
                f"'{value.name}' is already loaded."
            )

        # ------------------------------------------------------
        # Activate
        # ------------------------------------------------------

        self._scenes.change_scene(
            value.name
        )

    # ==========================================================
    # AUDIO
    # ==========================================================

    @property
    def audio(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return self.engine.audio

    # ==========================================================
    # ASSETS
    # ==========================================================

    @property
    def assets(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return self.engine.assets

    # ==========================================================
    # LOGGER
    # ==========================================================

    @property
    def logger(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return self.engine.logger

    # ==========================================================
    # TIME
    # ==========================================================

    @property
    def time(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return self.engine.time

    @property
    def delta_time(
        self,
    ) -> float:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.delta_time
        )

    @property
    def total_time(
        self,
    ) -> float:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.total_time
        )

    @property
    def frame(
        self,
    ) -> int:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.frame
        )

    # ==========================================================
    # RUNTIME STATE
    # ==========================================================

    @property
    def running(
        self,
    ) -> bool:
        return self._running