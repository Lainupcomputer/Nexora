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
)

from nexora.settings import (
    SettingsStore,
)


class Game:
    """
    Public high-level Nexora game API.

    SceneManager is the single source of truth for normal
    game-scene state.

    Nexora additionally owns a persistent global overlay scene
    which is independent from SceneManager.

    The global overlay is used for systems which must survive
    normal scene changes, such as:

        - notifications
        - save notifications
        - future global overlays
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

        # ======================================================
        # Settings
        # ======================================================

        settings_path: str | Path = "settings.json",
        settings_defaults: dict | None = None,

        # ======================================================
        # Save system
        # ======================================================

        save_path: str | Path = "saves",

        save_signing_key: bytes | str = (
            b"nexora-default-save-signing-key-"
            b"change-this-for-your-game"
        ),

        save_version: int = 1,

        save_max_file_size: int = (
            64 * 1024 * 1024
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
        # Save configuration
        # ======================================================

        self._save_path = Path(
            save_path
        )

        self._save_signing_key = (
            save_signing_key
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

        self._scenes = (
            SceneManager()
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

        # ======================================================
        # Settings
        # ======================================================

        self._settings = (
            SettingsStore(
                settings_path,
                defaults=settings_defaults,
            )
        )

    # ==========================================================
    # GLOBAL OVERLAY
    # ==========================================================

    def _initialize_global_overlay(
        self,
    ) -> None:
        """
        Create persistent global UI systems.

        The global overlay is intentionally not managed by the
        normal SceneManager.

        Because of that, its lifecycle must be started manually.
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
        # Dedicated overlay scene
        # ======================================================

        overlay_scene = Scene(
            "__nexora_global_overlay__"
        )

        # ------------------------------------------------------
        # Viewport
        # ------------------------------------------------------

        overlay_scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        # ======================================================
        # Notification center
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

        notifications.enter_duration = 0.35
        notifications.exit_duration = 0.30

        notifications.slide_enabled = True
        notifications.fade_enabled = True

        notifications.show_progress = True

        overlay_scene.add_node(
            notifications
        )

        # ======================================================
        # IMPORTANT
        #
        # This scene is outside SceneManager.
        #
        # SceneManager.change_scene() normally calls enter().
        # Because this overlay bypasses SceneManager, we have
        # to enter it ourselves.
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
        # Save notification bridge
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

    # ==========================================================
    # GLOBAL OVERLAY SHUTDOWN
    # ==========================================================

    def _shutdown_global_overlay(
        self,
    ) -> None:
        """
        Destroy global overlay services.
        """

        # ======================================================
        # Remove SaveManager listener first
        # ======================================================

        if (
            self._save_notification_handler
            is not None
            and self.engine is not None
        ):
            self.saves.remove_listener(
                self._save_notification_handler
            )

        self._save_notification_handler = None

        # ======================================================
        # Overlay
        # ======================================================

        overlay_scene = (
            self._global_overlay_scene
        )

        self._global_overlay_scene = None
        self._notifications = None

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

        Override in game subclasses.
        """

        pass

    def shutdown(
        self,
    ) -> None:
        """
        Called automatically before Engine shutdown.
        """

        # ------------------------------------------------------
        # Global systems first
        # ------------------------------------------------------

        self._shutdown_global_overlay()

        # ------------------------------------------------------
        # Normal scenes
        # ------------------------------------------------------

        self._scenes.clear()

    # ==========================================================
    # ENGINE CREATION
    # ==========================================================

    def _create_engine(
        self,
    ) -> Engine:
        return Engine(
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

            window_mode=(
                self._window_mode
            ),

            vsync=self._vsync,

            # --------------------------------------------------
            # Save system
            # --------------------------------------------------

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
        # Persistent global services
        #
        # Engine construction has already injected:
        #
        #     renderer
        #     input
        #     window
        #     engine
        #
        # Therefore the global overlay can now be created.
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
        if self.engine is not None:
            self.engine.stop()

    # ==========================================================
    # EVENTS
    # ==========================================================

    def handle_event(
        self,
        event,
    ) -> None:
        pass

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Update normal game scene and persistent global overlay.
        """

        # ======================================================
        # Active normal scene
        # ======================================================

        scene = (
            self._scenes.active_scene
        )

        if scene is not None:
            # --------------------------------------------------
            # Viewport
            # --------------------------------------------------

            if self.renderer is not None:
                scene.ui.set_viewport_size(
                    self.renderer.width,
                    self.renderer.height,
                )

            # --------------------------------------------------
            # Input
            # --------------------------------------------------

            if self.input is not None:
                scene.update_input(
                    self.input
                )

            # --------------------------------------------------
            # Update
            # --------------------------------------------------

            scene.update(
                delta_time
            )

        # ======================================================
        # Global overlay
        #
        # This always updates, even when there is no normal
        # active scene.
        # ======================================================

        overlay = (
            self._global_overlay_scene
        )

        if overlay is not None:
            # --------------------------------------------------
            # Viewport synchronization
            # --------------------------------------------------

            if self.renderer is not None:
                overlay.ui.set_viewport_size(
                    self.renderer.width,
                    self.renderer.height,
                )

            # --------------------------------------------------
            # Node/world update
            #
            # NotificationCenter.update() runs through:
            #
            # overlay.root.update_tree()
            # --------------------------------------------------

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
        scene = (
            self._scenes.active_scene
        )

        if scene is not None:
            scene.fixed_update(
                fixed_delta_time
            )

        # ------------------------------------------------------
        # Global overlay generally doesn't need fixed updates,
        # but allowing it keeps the Scene lifecycle complete.
        # ------------------------------------------------------

        overlay = (
            self._global_overlay_scene
        )

        if overlay is not None:
            overlay.fixed_update(
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
        Render normal scene stack first and global overlay last.

        Rendering order:

            paused scene(s)
                ↓
            active scene
                ↓
            global overlay

        The global overlay is therefore always above normal
        game content.
        """

        if self.renderer is None:
            return

        # ======================================================
        # Normal scenes
        # ======================================================

        render_scenes = (
            self._get_render_scenes()
        )

        for scene in render_scenes:
            self._render_scene(
                scene,
                interpolation,
            )

        # ======================================================
        # Global overlay
        #
        # IMPORTANT:
        # Do NOT return when render_scenes is empty.
        # Notifications must also work during loading states
        # where no normal scene may currently be active.
        # ======================================================

        overlay = (
            self._global_overlay_scene
        )

        if overlay is not None:
            # --------------------------------------------------
            # Overlay world
            # --------------------------------------------------

            overlay.render(
                interpolation
            )

            # --------------------------------------------------
            # Overlay nodes
            #
            # NotificationCenter.render() runs here.
            # --------------------------------------------------

            overlay.render_nodes(
                self.renderer,
                interpolation,
            )

            # --------------------------------------------------
            # Future overlay UI nodes
            # --------------------------------------------------

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
        # ------------------------------------------------------
        # UI viewport
        # ------------------------------------------------------

        scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        # ------------------------------------------------------
        # ECS
        # ------------------------------------------------------

        scene.render(
            interpolation
        )

        # ------------------------------------------------------
        # Nodes
        # ------------------------------------------------------

        scene.render_nodes(
            self.renderer,
            interpolation,
        )

        # ------------------------------------------------------
        # UI
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
    # NOTIFICATIONS
    # ==========================================================

    @property
    def notifications(
        self,
    ) -> NotificationCenter:
        """
        Access Nexora's global NotificationCenter.

        Notifications survive normal scene changes.
        """

        if self._notifications is None:
            raise RuntimeError(
                "NotificationCenter is not available before "
                "the game has been started."
            )

        return self._notifications

    # ==========================================================
    # SETTINGS
    # ==========================================================

    @property
    def settings(
        self,
    ) -> SettingsStore:
        return self._settings

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

    # ==========================================================
    # SCENES
    # ==========================================================

    @property
    def scenes(
        self,
    ) -> SceneManager:
        return self._scenes

    @property
    def scene(
        self,
    ) -> Scene | None:
        return (
            self._scenes.active_scene
        )

    @scene.setter
    def scene(
        self,
        value: Scene | None,
    ) -> None:
        # ------------------------------------------------------
        # Deactivate
        # ------------------------------------------------------

        if value is None:
            self._scenes.deactivate()
            return

        # ------------------------------------------------------
        # Validation
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
        return self._running