from __future__ import annotations

from pathlib import Path

from nexora.assets import AssetManager
from nexora.audio import AudioSystem
from nexora.core.game_loop import GameLoop
from nexora.debug.logger import Logger
from nexora.debug.overlay import DebugOverlay
from nexora.input import InputManager
from nexora.rendering import Renderer
from nexora.rendering.gpu import (
    GPUContext,
    WindowMode,
)
from nexora.save import SaveManager
from nexora.settings import GraphicsSettings
from nexora.threading.context import ThreadContext


class Engine:
    """
    Central Nexora Engine.

    Owns the main engine services and controls the game loop.

    Rendering is GPU-first and uses SDL_GPU directly.
    """

    def __init__(
        self,
        game,
        *,
        title: str = "Nexora",
        target_fps: int = 144,
        fixed_delta_time: float = 1.0 / 60.0,

        # ======================================================
        # Optional graphics overrides
        # ======================================================
        #
        # None means:
        #     use the value from graphics.toml
        #
        # Explicit values override the loaded graphics settings.
        # ======================================================

        width: int | None = None,
        height: int | None = None,
        resizable: bool | None = None,
        fullscreen: bool | None = None,
        window_mode: WindowMode | str | None = None,
        vsync: bool | None = None,
        frames_in_flight: int | None = None,

        # ======================================================
        # Graphics settings
        # ======================================================

        graphics_settings_path: str | Path | None = "settings",
        graphics_defaults_path: str | Path | None = None,
        graphics_project_path: str | Path | None = None,
        graphics_mod_paths: tuple[str | Path, ...] = (),

        # ======================================================
        # Input settings
        # ======================================================

        input_settings_path: str | Path | None = "settings",
        input_defaults_path: str | Path | None = None,
        input_project_bindings_path: str | Path | None = None,
        input_mod_binding_paths: tuple[str | Path, ...] = (),

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
        # Main thread
        # ======================================================

        ThreadContext.initialize()

        # ======================================================
        # Core services
        # ======================================================

        self.logger = Logger()
        self.assets = AssetManager()

        # ======================================================
        # Save system
        # ======================================================

        self.saves = SaveManager(
            save_path=save_path,
            signing_key=save_signing_key,
            save_version=save_version,
            max_file_size=save_max_file_size,
            quick_save_enabled=(
                quick_save_enabled
            ),
            quick_save_slot=(
                quick_save_slot
            ),
            autosave_enabled=(
                autosave_enabled
            ),
            autosave_slots=(
                autosave_slots
            ),
            autosave_prefix=(
                autosave_prefix
            ),
        )

        # ======================================================
        # Graphics settings
        # ======================================================

        self.graphics = GraphicsSettings(
            settings_path=(
                graphics_settings_path
            ),
            defaults_path=(
                graphics_defaults_path
            ),
            project_path=(
                graphics_project_path
            ),
            mod_paths=(
                graphics_mod_paths
            ),
        )

        graphics = (
            self.graphics.gpu_context_kwargs()
        )

        # ======================================================
        # Explicit graphics overrides
        # ======================================================

        if width is not None:
            graphics[
                "width"
            ] = int(
                width
            )

        if height is not None:
            graphics[
                "height"
            ] = int(
                height
            )

        if resizable is not None:
            graphics[
                "resizable"
            ] = bool(
                resizable
            )

        if vsync is not None:
            graphics[
                "vsync"
            ] = bool(
                vsync
            )

        if frames_in_flight is not None:
            graphics[
                "frames_in_flight"
            ] = int(
                frames_in_flight
            )

        # ======================================================
        # Window mode override
        # ======================================================

        loaded_window_mode = (
            graphics[
                "window_mode"
            ]
        )

        if window_mode is not None:
            resolved_window_mode = WindowMode(
                window_mode
            )

        elif fullscreen is not None:
            resolved_window_mode = (
                WindowMode.FULLSCREEN
                if fullscreen
                else WindowMode.WINDOWED
            )

        else:
            resolved_window_mode = WindowMode(
                loaded_window_mode
            )

        # ======================================================
        # GPU
        # ======================================================

        self.gpu_context = GPUContext(
            width=(
                graphics[
                    "width"
                ]
            ),
            height=(
                graphics[
                    "height"
                ]
            ),
            title=title,
            vsync=(
                graphics[
                    "vsync"
                ]
            ),
            resizable=(
                graphics[
                    "resizable"
                ]
            ),
            window_mode=(
                resolved_window_mode
            ),
            frames_in_flight=(
                graphics[
                    "frames_in_flight"
                ]
            ),
        )

        # ======================================================
        # Default font
        # ======================================================

        self.default_font = (
            self.assets.load_font(
                "fonts/Roboto-Regular.ttf",
                24.0,
            )
        )

        # ======================================================
        # Renderer
        # ======================================================

        self.renderer = Renderer(
            self.gpu_context,
            font=self.default_font,
        )

        # ======================================================
        # Post processing
        # ======================================================

        self.graphics.apply_post_processing(
            self.renderer
        )

        # ======================================================
        # Window
        # ======================================================

        self.window = (
            self.gpu_context
        )

        # ======================================================
        # Input
        # ======================================================

        input_kwargs = {
            "logger": self.logger,
            "settings_path": (
                input_settings_path
            ),
            "project_bindings_path": (
                input_project_bindings_path
            ),
            "mod_binding_paths": (
                input_mod_binding_paths
            ),
        }

        # Let InputManager use its internal Nexora default path
        # when no explicit defaults file was supplied.
        if input_defaults_path is not None:
            input_kwargs[
                "defaults_path"
            ] = input_defaults_path

        self.input = InputManager(
            **input_kwargs
        )

        # ======================================================
        # Audio
        # ======================================================

        self.audio = AudioSystem()

        # ======================================================
        # Game
        # ======================================================

        self.game = game

        self.game.engine = self
        self.game.renderer = self.renderer
        self.game.input = self.input
        self.game.window = self.window
        self.game.graphics = self.graphics

        # ======================================================
        # Game loop
        # ======================================================

        self.loop = GameLoop(
            self,
            target_fps=target_fps,
            fixed_delta_time=fixed_delta_time,
        )

        # ======================================================
        # Runtime
        # ======================================================

        self._initialized = False
        self._shutdown = False

        # ======================================================
        # Debug overlay
        # ======================================================

        self.debug_overlay = (
            DebugOverlay(
                self
            )
        )

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def time(
        self,
    ):
        return self.loop.time

    @property
    def delta_time(
        self,
    ) -> float:
        return (
            self.time.delta_time
        )

    @property
    def unscaled_delta_time(
        self,
    ) -> float:
        return (
            self.time.unscaled_delta_time
        )

    @property
    def total_time(
        self,
    ) -> float:
        return (
            self.time.total_time
        )

    @property
    def fixed_time(
        self,
    ) -> float:
        return (
            self.time.fixed_time
        )

    @property
    def frame(
        self,
    ) -> int:
        return (
            self.time.frame
        )

    @property
    def fixed_frame(
        self,
    ) -> int:
        return (
            self.time.fixed_frame
        )

    # ==========================================================
    # GRAPHICS
    # ==========================================================

    def apply_graphics_settings(
        self,
    ) -> None:
        """
        Reload and apply graphics settings that can safely
        change while the engine is running.

        Startup-only settings such as frames_in_flight require
        recreating the GPU context.
        """

        self.graphics.reload()

        self.graphics.apply_runtime(
            self.gpu_context,
            self.renderer,
        )

    def reset_graphics_settings(
        self,
    ) -> None:
        """
        Remove all user graphics overrides and restore the
        effective defaults/project/mod configuration.
        """

        self.graphics.reset_user()

        if self._initialized:
            self.graphics.apply_runtime(
                self.gpu_context,
                self.renderer,
            )

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        if self._initialized:
            return

        ThreadContext.assert_main_thread(
            "Engine.initialize"
        )

        self.input.initialize(
            self.gpu_context.window,
        )

        self.audio.initialize()

        initialize = getattr(
            self.game,
            "initialize",
            None,
        )

        if initialize is not None:
            initialize()

        self._initialized = True

        self.logger.info(
            "Nexora Engine initialized."
        )

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
    ) -> None:
        if self._shutdown:
            raise RuntimeError(
                "Cannot run an engine that has already "
                "been shut down."
            )

        if not self._initialized:
            self.initialize()

        ThreadContext.assert_main_thread(
            "Engine.run"
        )

        self.logger.info(
            "Nexora Engine started."
        )

        self.loop.run()

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
    ) -> None:
        self.loop.stop()

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        if self._shutdown:
            return

        ThreadContext.assert_main_thread(
            "Engine.shutdown"
        )

        shutdown = getattr(
            self.game,
            "shutdown",
            None,
        )

        if shutdown is not None:
            shutdown()

        try:
            self.audio.shutdown()

        except Exception as exc:
            self.logger.warning(
                "Audio shutdown failed: "
                f"{exc}"
            )

        try:
            self.debug_overlay.shutdown()

        except Exception as exc:
            self.logger.warning(
                "Debug overlay shutdown failed: "
                f"{exc}"
            )

        try:
            self.renderer.destroy()

        except Exception as exc:
            self.logger.warning(
                "Renderer shutdown failed: "
                f"{exc}"
            )

        try:
            self.assets.shutdown()

        except Exception as exc:
            self.logger.warning(
                "AssetManager shutdown failed: "
                f"{exc}"
            )

        try:
            self.gpu_context.destroy()

        except Exception as exc:
            self.logger.warning(
                "GPUContext shutdown failed: "
                f"{exc}"
            )

        self._shutdown = True

        self.logger.info(
            "Nexora Engine shut down."
        )