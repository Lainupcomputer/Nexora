from __future__ import annotations

from pathlib import Path

from nexora.core.engine import Engine

from nexora.nodes import (
    NotificationAnchor,
    NotificationCenter,
)

from nexora.rendering.gpu import (
    WindowMode,
)

from nexora.save import (
    SaveManager,
    SaveNotificationHandler,
)

from nexora.scene import (
    Scene,
    SceneManager,
    SceneSerializer,
)


class Game:
    """
    Public high-level Nexora game API.

    A normal Nexora game only needs a project name.

    Example:

        class MyGame(Game):
            def initialize(self):
                self.scene = Scene("Game")

        MyGame(
            project_name="MyGame",
            title="My Game",
        ).run()

    Nexora automatically loads:

        nexora/core/defaults/engine.toml
        nexora/core/defaults/graphics.toml
        nexora/core/defaults/audio.toml
        nexora/core/defaults/keybinds.toml

    User overrides are stored under:

        Documents/<project_name>/settings/

    SceneManager is the single source of truth for game scene
    state.

    The global overlay is intentionally outside SceneManager so
    notifications can survive normal scene changes.
    """

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        title: str = "Nexora",

        # ======================================================
        # Optional runtime overrides
        #
        # None means:
        #
        #     use the corresponding settings file.
        #
        # These remain useful for tests, examples and games that
        # want to override settings programmatically.
        # ======================================================

        target_fps: int | None = None,
        fixed_delta_time: float | None = None,

        width: int | None = None,
        height: int | None = None,
        resizable: bool | None = None,
        fullscreen: bool | None = None,

        window_mode: (
            WindowMode
            | str
            | None
        ) = None,

        vsync: bool | None = None,
        frames_in_flight: int | None = None,

        # ======================================================
        # Save system
        #
        # Saves are still separate from the settings system for
        # now.
        # ======================================================

        save_path: str | Path | None = None,

        save_signing_key: bytes | str = (
            b"nexora-default-save-signing-key-"
            b"change-this-for-your-game"
        ),

        scene_signing_key: bytes | str | None = None,

        save_version: int = 1,

        save_max_file_size: int = (
            64
            * 1024
            * 1024
        ),

        quick_save_enabled: bool = True,
        quick_save_slot: str = "quicksave",

        autosave_enabled: bool = True,
        autosave_slots: int = 3,
        autosave_prefix: str = "autosave",
    ) -> None:
        # ======================================================
        # Engine services
        # ======================================================

        self.engine: Engine | None = None

        self.renderer = None
        self.input = None
        self.window = None
        self.graphics = None
        self.console = None

        # ======================================================
        # Project
        # ======================================================

        project_name = str(
            project_name
        ).strip()

        if not project_name:
            raise ValueError(
                "project_name cannot be empty."
            )

        self._project_name = (
            project_name
        )

        # ======================================================
        # Basic game configuration
        # ======================================================

        self._title = str(
            title
        )

        # ======================================================
        # Optional engine overrides
        # ======================================================

        self._target_fps = (
            int(
                target_fps
            )
            if target_fps is not None
            else None
        )

        self._fixed_delta_time = (
            float(
                fixed_delta_time
            )
            if fixed_delta_time is not None
            else None
        )

        # ======================================================
        # Optional graphics overrides
        # ======================================================

        self._width = (
            int(
                width
            )
            if width is not None
            else None
        )

        self._height = (
            int(
                height
            )
            if height is not None
            else None
        )

        self._resizable = (
            bool(
                resizable
            )
            if resizable is not None
            else None
        )

        self._fullscreen = (
            bool(
                fullscreen
            )
            if fullscreen is not None
            else None
        )

        self._window_mode = (
            window_mode
        )

        self._vsync = (
            bool(
                vsync
            )
            if vsync is not None
            else None
        )

        self._frames_in_flight = (
            int(
                frames_in_flight
            )
            if frames_in_flight is not None
            else None
        )


        
        # ======================================================
        # Save configuration
        # ======================================================

        self._save_path = (
            Path(
                save_path
            )
            if save_path is not None
            else None
        )

        self._save_signing_key = (
            save_signing_key
        )

        self._scene_signing_key = (
            scene_signing_key
            if scene_signing_key is not None
            else save_signing_key
        )

        self._save_version = int(
            save_version
        )

        self._save_max_file_size = int(
            save_max_file_size
        )

        self._quick_save_enabled = bool(
            quick_save_enabled
        )

        self._quick_save_slot = str(
            quick_save_slot
        )

        self._autosave_enabled = bool(
            autosave_enabled
        )

        self._autosave_slots = int(
            autosave_slots
        )

        self._autosave_prefix = str(
            autosave_prefix
        )

        # ======================================================
        # Runtime
        # ======================================================

        self._running = False
        self._shutdown = False

        # ======================================================
        # Scenes
        # ======================================================

        self._scene_serializer = SceneSerializer(
            signing_key=self._scene_signing_key,
        )

        self._scenes = (
            SceneManager(
                serializer=self._scene_serializer,
            )
        )

        # ======================================================
        # Global overlay
        # ======================================================

        self._global_overlay_scene: (
            Scene | None
        ) = None

        self._notifications: (
            NotificationCenter | None
        ) = None

        self._save_notification_handler: (
            SaveNotificationHandler | None
        ) = None

    # ==========================================================
    # PROJECT
    # ==========================================================

    @property
    def project_name(
        self,
    ) -> str:
        return (
            self._project_name
        )

    @property
    def title(
        self,
    ) -> str:
        return (
            self._title
        )

    # ==========================================================
    # GLOBAL OVERLAY
    # ==========================================================

    def _initialize_global_overlay(
        self,
    ) -> None:
        """
        Create persistent global UI services.

        The overlay lives outside SceneManager and therefore
        survives normal scene changes.
        """

        if (
            self._global_overlay_scene
            is not None
        ):
            return

        if self.renderer is None:
            raise RuntimeError(
                "Cannot initialize global overlay before "
                "the renderer is available."
            )

        # ======================================================
        # Overlay scene
        # ======================================================

        overlay_scene = (
            Scene(
                "__nexora_global_overlay__"
            )
        )

        overlay_scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        # ======================================================
        # Notifications
        # ======================================================

        notifications = (
            NotificationCenter(
                "GlobalNotifications",
                overlay_scene.world,
                self.renderer,
            )
        )

        notifications.anchor = (
            NotificationAnchor.TOP_RIGHT
        )

        notifications.max_visible = 5

        notifications.width = 360.0
        notifications.height = 92.0

        notifications.margin = 24.0
        notifications.spacing = 12.0

        notifications.enter_duration = (
            0.35
        )

        notifications.exit_duration = (
            0.30
        )

        notifications.slide_enabled = (
            True
        )

        notifications.fade_enabled = (
            True
        )

        notifications.show_progress = (
            True
        )

        overlay_scene.add_node(
            notifications
        )

        # ======================================================
        # Activate global overlay
        #
        # Scene has no activate() method. enter() is the lifecycle
        # API that switches the scene from CREATED to ACTIVE.
        # The overlay is not owned by SceneManager, so Game must
        # enter it explicitly.
        # ======================================================

        overlay_scene.enter()

        # ======================================================
        # Store
        # ======================================================

        self._global_overlay_scene = (
            overlay_scene
        )

        self._notifications = (
            notifications
        )

        # ======================================================
        # Save notifications
        # ======================================================

        handler = (
            SaveNotificationHandler(
                notifications,
                show_started=False,
            )
        )

        self._save_notification_handler = (
            handler
        )

        self.saves.add_listener(
            handler
        )

    def _shutdown_global_overlay(
        self,
    ) -> None:
        """
        Destroy global overlay services.
        """

        handler = (
            self._save_notification_handler
        )

        if (
            handler is not None
            and self.engine is not None
        ):
            self.saves.remove_listener(
                handler
            )

        self._save_notification_handler = (
            None
        )

        overlay_scene = (
            self._global_overlay_scene
        )

        self._global_overlay_scene = (
            None
        )

        self._notifications = (
            None
        )

        if overlay_scene is not None:
            overlay_scene.destroy()

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        """
        Called automatically by Engine.initialize().

        Override this method in the actual game.
        """

        pass

    def shutdown(
        self,
    ) -> None:
        """
        Called automatically before engine shutdown.
        """

        self._shutdown_global_overlay()

        self._scenes.clear()

    # ==========================================================
    # ENGINE CREATION
    # ==========================================================

    def _create_engine(
        self,
    ) -> Engine:
        """
        Create the Nexora Engine instance.

        All normal settings paths are resolved internally through
        project_name.
        """

        return Engine(
            self,

            project_name=(
                self._project_name
            ),

            title=(
                self._title
            ),

            # ==================================================
            # Engine overrides
            # ==================================================

            target_fps=(
                self._target_fps
            ),

            fixed_delta_time=(
                self._fixed_delta_time
            ),

            # ==================================================
            # Graphics overrides
            # ==================================================

            width=(
                self._width
            ),

            height=(
                self._height
            ),

            resizable=(
                self._resizable
            ),

            fullscreen=(
                self._fullscreen
            ),

            window_mode=(
                self._window_mode
            ),

            vsync=(
                self._vsync
            ),

            frames_in_flight=(
                self._frames_in_flight
            ),

            # ==================================================
            # Save system
            # ==================================================

            save_path=(
                self._save_path
            ),

            save_signing_key=(
                self._save_signing_key
            ),

            save_version=(
                self._save_version
            ),

            save_max_file_size=(
                self._save_max_file_size
            ),

            quick_save_enabled=(
                self._quick_save_enabled
            ),

            quick_save_slot=(
                self._quick_save_slot
            ),

            autosave_enabled=(
                self._autosave_enabled
            ),

            autosave_slots=(
                self._autosave_slots
            ),

            autosave_prefix=(
                self._autosave_prefix
            ),
        )

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

        if self.engine is not None:
            raise RuntimeError(
                "Game already owns an engine instance."
            )

        # ======================================================
        # Engine
        # ======================================================

        self.engine = (
            self._create_engine()
        )

        # ======================================================
        # Serialized scene runtime services
        # ======================================================

        self._scenes.bind_assets(
            self.engine.assets
        )

        self._scenes.bind_serialization_context_provider(
            lambda: {
                "game": self,
                "engine": self.engine,
                "renderer": self.renderer,
                "input": self.input,
                "assets": self.engine.assets,
                "audio": self.engine.audio,
            }
        )

        # ======================================================
        # Global services
        # ======================================================

        self._initialize_global_overlay()

        # ======================================================
        # Run
        # ======================================================

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
        Stop the running engine loop.
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
        Handle a raw SDL event.

        Override only when direct SDL events are required.
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
        Update the active game scene and persistent overlay.
        """

        scene = (
            self._scenes.active_scene
        )

        # ======================================================
        # Active scene
        # ======================================================

        if scene is not None:
            if self.renderer is not None:
                scene.ui.set_viewport_size(
                    self.renderer.width,
                    self.renderer.height,
                )

            if self.input is not None:
                scene.update_input(
                    self.input
                )

            scene.update(
                delta_time
            )

        # ======================================================
        # Global overlay
        # ======================================================

        overlay = (
            self._global_overlay_scene
        )

        if overlay is not None:
            if self.renderer is not None:
                overlay.ui.set_viewport_size(
                    self.renderer.width,
                    self.renderer.height,
                )

            overlay.update(
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
        Fixed timestep update.

        Only the active normal scene receives fixed gameplay
        updates.
        """

        scene = (
            self._scenes.active_scene
        )

        if scene is not None:
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
        Render the scene stack followed by the persistent global
        overlay.
        """

        if self.renderer is None:
            return

        # ======================================================
        # Game scenes
        # ======================================================

        for scene in (
            self._get_render_scenes()
        ):
            self._render_scene(
                scene,
                interpolation,
            )

        # ======================================================
        # Global overlay
        # ======================================================

        overlay = (
            self._global_overlay_scene
        )

        if overlay is not None:
            overlay.ui.set_viewport_size(
                self.renderer.width,
                self.renderer.height,
            )

            # Persistent notifications and other global overlay content are
            # screen-space UI and must not be affected by world lighting or
            # post-processing.
            with self.renderer.overlay_scope():
                overlay.render(
                    interpolation
                )

                overlay.render_nodes(
                    self.renderer,
                    interpolation,
                )

                overlay.ui.render(
                    self.renderer
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
        Render one scene using the normal Nexora pipeline.
        """

        scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        scene.render(
            interpolation
        )

        scene.render_nodes(
            self.renderer,
            interpolation,
        )

        # Scene UI is screen-space content. Queue it into the overlay phase so
        # fullscreen lighting/post effects only touch world rendering.
        with self.renderer.overlay_scope():
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
    # NOTIFICATIONS
    # ==========================================================

    @property
    def notifications(
        self,
    ) -> NotificationCenter:
        """
        Global notification center.

        Available after Game.run() has created the engine.
        """

        if self._notifications is None:
            raise RuntimeError(
                "NotificationCenter is not available before "
                "the game has been started."
            )

        return (
            self._notifications
        )

    # ==========================================================
    # ENGINE SETTINGS
    # ==========================================================

    @property
    def engine_settings(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.settings
        )

    def reload_engine_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reload_engine_settings()

    def reset_engine_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reset_engine_settings()

    # ==========================================================
    # GRAPHICS SETTINGS
    # ==========================================================

    @property
    def graphics_settings(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.graphics
        )

    def apply_graphics_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.apply_graphics_settings()

    def reset_graphics_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reset_graphics_settings()

    # ==========================================================
    # AUDIO SETTINGS
    # ==========================================================

    @property
    def audio_settings(
        self,
    ):
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.audio_settings
        )

    def apply_audio_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.apply_audio_settings()

    def reset_audio_settings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reset_audio_settings()

    # ==========================================================
    # PROJECT PATHS
    # ==========================================================

    @property
    def paths(
        self,
    ):
        """
        Access the resolved Nexora project paths.
        """

        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.paths
        )


    # ==========================================================
    # INPUT SETTINGS
    # ==========================================================

    def reload_input_bindings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reload_input_bindings()

    def save_input_bindings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.save_input_bindings()

    def reset_input_bindings(
        self,
    ) -> None:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        self.engine.reset_input_bindings()

    # ==========================================================
    # SAVES
    # ==========================================================

    @property
    def saves(
        self,
    ) -> SaveManager:
        if self.engine is None:
            raise RuntimeError(
                "Game has not been started."
            )

        return (
            self.engine.saves
        )

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

    @property
    def scene_serializer(
        self,
    ) -> SceneSerializer:
        return self._scene_serializer

    # ==========================================================
    # SCENES
    # ==========================================================

    @property
    def scenes(
        self,
    ) -> SceneManager:
        return (
            self._scenes
        )

    @property
    def scene(
        self,
    ) -> Scene | None:
        """
        Convenience alias for SceneManager.active_scene.
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
        Set the active scene.

        SceneManager remains the single source of truth.
        """

        if value is None:
            self._scenes.deactivate()

            return

        if not isinstance(
            value,
            Scene,
        ):
            raise TypeError(
                "scene must be a Scene instance or None."
            )

        if (
            self._scenes.active_scene
            is value
        ):
            return

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

        return (
            self.engine.audio
        )

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

        return (
            self.engine.assets
        )

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

        return (
            self.engine.logger
        )

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

        return (
            self.engine.time
        )

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
        return (
            self._running
        )