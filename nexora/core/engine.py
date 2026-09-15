from __future__ import annotations

from pathlib import Path

from nexora.assets import AssetManager

from nexora.audio import (
    AudioChannel,
    AudioSystem,
)

from nexora.core.game_loop import (
    GameLoop,
)

from nexora.debug.logger import (
    Logger,
)

from nexora.debug.console import (
    DebugConsole,
)

from nexora.debug.overlay import (
    DebugOverlay,
)

from nexora.input import (
    InputManager,
)

from nexora.rendering import (
    Renderer,
)

from nexora.rendering.shaders import (
    ShaderCompiler,
)

from nexora.rendering.gpu import (
    GPUContext,
    WindowMode,
)

from nexora.save import (
    SaveManager,
)

from nexora.settings import (
    AudioSettings,
    EngineSettings,
    GraphicsSettings,
)

from nexora.threading.context import (
    ThreadContext,
)

from nexora.tween import (
    TweenManager,
)
from nexora.core.paths import (
    ProjectPaths,
)

class Engine:
    """
    Central Nexora Engine.

    Owns the main engine services and controls the game loop.

    Configuration is loaded automatically from:

        nexora/core/defaults/

    and user overrides from:

        Documents/<project_name>/settings/

    Settings are separated into:

        graphics.toml
        keybinds.toml
        audio.toml
        engine.toml
    """

    def __init__(
        self,
        game,
        *,
        project_name: str = "Nexora",
        title: str = "Nexora",

        # ======================================================
        # Optional engine timing overrides
        # ======================================================

        target_fps: int | None = None,
        fixed_delta_time: float | None = None,

        # ======================================================
        # Optional graphics overrides
        # ======================================================

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
        # ======================================================

        save_path: str | Path | None = None,

        save_signing_key: bytes | str = (
            b"nexora-default-save-signing-key-"
            b"change-this-for-your-game"
        ),

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
        # Main thread
        # ======================================================

        ThreadContext.initialize()

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

        self.project_name = (
            project_name
        )
        # ======================================================
        # Project paths
        # ======================================================

        self.paths = (
            ProjectPaths(
                self.project_name
            )
        )

        self.paths.ensure()

        # ======================================================
        # Core services
        # ======================================================

        self.logger = (
            Logger()
        )

        # ======================================================
        # Shader compilation
        # ======================================================
        #
        # HLSL sources live inside Nexora, but SPIR-V binaries are
        # compiled directly into this project's Documents runtime
        # directory. No nexora/shaders/bin -> Documents copy step.
        # ======================================================

        shader_build = ShaderCompiler(
            source_dir=(
                self.paths.shader_source_dir
            ),
            output_dir=(
                self.paths.shader_bin
            ),
            dxc_path=(
                self.paths.shader_compiler
            ),
        ).compile_all()

        if shader_build.built_count:
            self.logger.info(
                "Compiled "
                f"{shader_build.built_count} shader(s) "
                f"to {self.paths.shader_bin}"
            )

        self.assets = (
            AssetManager()
        )

        # ======================================================
        # Engine settings
        # ======================================================

        self.settings = (
            EngineSettings(
                project_name=(
                    self.project_name
                )
            )
        )

        # ======================================================
        # Timing
        # ======================================================

        resolved_target_fps = (
            int(
                target_fps
            )
            if target_fps is not None
            else int(
                self.settings
                .timing
                .target_fps
            )
        )

        resolved_fixed_delta_time = (
            float(
                fixed_delta_time
            )
            if fixed_delta_time is not None
            else float(
                self.settings
                .timing
                .fixed_delta_time
            )
        )

        if resolved_target_fps <= 0:
            raise ValueError(
                "target_fps must be greater than zero."
            )

        if resolved_fixed_delta_time <= 0.0:
            raise ValueError(
                "fixed_delta_time must be greater than zero."
            )

        # ======================================================
        # Save path
        # ======================================================

        resolved_save_path = (
            Path(
                save_path
            )
            if save_path is not None
            else self.paths.saves
        )

        
        # ======================================================
        # Save system
        # ======================================================

        self.saves = (
            SaveManager(
                save_path=(
                    resolved_save_path
                ),

                signing_key=(
                    save_signing_key
                ),

                save_version=(
                    save_version
                ),

                max_file_size=(
                    save_max_file_size
                ),

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
        )

        # ======================================================
        # Graphics settings
        # ======================================================

        self.graphics = (
            GraphicsSettings(
                project_name=(
                    self.project_name
                )
            )
        )

        graphics = (
            self.graphics
            .gpu_context_kwargs()
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
        # Window mode
        # ======================================================

        loaded_window_mode = (
            graphics[
                "window_mode"
            ]
        )

        if window_mode is not None:
            resolved_window_mode = (
                WindowMode(
                    window_mode
                )
            )

        elif fullscreen is not None:
            resolved_window_mode = (
                WindowMode.FULLSCREEN
                if fullscreen
                else WindowMode.WINDOWED
            )

        else:
            resolved_window_mode = (
                WindowMode(
                    loaded_window_mode
                )
            )

        # ======================================================
        # GPU
        # ======================================================

        self.gpu_context = (
            GPUContext(
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
        )

        # ======================================================
        # Asset GPU binding
        # ======================================================

        self.assets.bind_gpu(
            self.gpu_context
        )

        # ======================================================
        # Default font
        # ======================================================

        self.default_font = (
            self.assets.font(
                "fonts/Roboto-Regular.ttf",
                24.0,
            )
        )

        # ======================================================
        # Renderer
        # ======================================================

        self.renderer = (
            Renderer(
                self.gpu_context,

                shader_dir=(
                    self.paths.shader_bin
                ),

                font=(
                    self.default_font
                ),
            )
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

        self.input = (
            InputManager(
                logger=(
                    self.logger
                ),

                project_name=(
                    self.project_name
                ),
            )
        )

        # ======================================================
        # Audio settings
        # ======================================================

        self.audio_settings = (
            AudioSettings(
                project_name=(
                    self.project_name
                )
            )
        )

        # ======================================================
        # Technical audio settings
        # ======================================================

        audio_frequency = int(
            self.settings
            .audio
            .frequency
        )

        audio_channels = int(
            self.settings
            .audio
            .channels
        )

        target_queue_frames = int(
            self.settings
            .audio_buffer
            .target_queue_frames
        )

        max_update_frames = int(
            self.settings
            .audio_buffer
            .max_update_frames
        )

        if audio_frequency <= 0:
            raise ValueError(
                "audio.frequency must be greater than zero."
            )

        if audio_channels != 2:
            raise ValueError(
                "Nexora currently supports stereo "
                "audio output only."
            )

        if target_queue_frames <= 0:
            raise ValueError(
                "audio_buffer.target_queue_frames "
                "must be greater than zero."
            )

        if max_update_frames <= 0:
            raise ValueError(
                "audio_buffer.max_update_frames "
                "must be greater than zero."
            )

        # ======================================================
        # Audio system
        # ======================================================

        self.audio = (
            AudioSystem(
                frequency=(
                    audio_frequency
                ),

                channels=(
                    audio_channels
                ),

                target_queue_frames=(
                    target_queue_frames
                ),

                max_update_frames=(
                    max_update_frames
                ),
            )
        )

        # ======================================================
        # Asset audio binding
        # ======================================================

        self.assets.bind_audio_cache(
            self.audio.cache
        )

        # ======================================================
        # Apply user-facing audio settings
        # ======================================================

        self._apply_audio_settings()

        # ======================================================
        # Tween system
        # ======================================================

        self.tweens = (
            TweenManager()
        )

        # ======================================================
        # Game
        # ======================================================

        self.game = game

        self.game.engine = self

        self.game.renderer = (
            self.renderer
        )

        self.game.input = (
            self.input
        )

        self.game.window = (
            self.window
        )

        self.game.graphics = (
            self.graphics
        )

        self.game.tweens = (
            self.tweens
        )

        # ======================================================
        # Debug console
        # ======================================================

        self.console = (
            DebugConsole(
                self
            )
        )

        self.game.console = (
            self.console
        )

        # ======================================================
        # Game loop
        # ======================================================

        self.loop = (
            GameLoop(
                self,

                target_fps=(
                    resolved_target_fps
                ),

                fixed_delta_time=(
                    resolved_fixed_delta_time
                ),
            )
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

        self.debug_overlay.visible = bool(
            self.settings
            .debug
            .overlay
        )

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def time(
        self,
    ):
        return (
            self.loop.time
        )

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
    # ENGINE SETTINGS
    # ==========================================================

    def reload_engine_settings(
        self,
    ) -> None:
        """
        Reload engine.toml.

        Runtime-safe settings are applied immediately.

        Audio frequency and channel count are startup-only and
        require recreation of the audio device.
        """

        self.settings.reload()

        # ------------------------------------------------------
        # Debug overlay
        # ------------------------------------------------------

        self.debug_overlay.visible = bool(
            self.settings
            .debug
            .overlay
        )

        # ------------------------------------------------------
        # Audio buffering
        # ------------------------------------------------------

        self.audio.target_queue_frames = int(
            self.settings
            .audio_buffer
            .target_queue_frames
        )

        self.audio.max_update_frames = int(
            self.settings
            .audio_buffer
            .max_update_frames
        )

    def reset_engine_settings(
        self,
    ) -> None:
        """
        Remove all user engine overrides.
        """

        self.settings.reset_user()

        self.reload_engine_settings()

    # ==========================================================
    # GRAPHICS SETTINGS
    # ==========================================================

    def apply_graphics_settings(
        self,
    ) -> None:
        """
        Reload and apply runtime-safe graphics settings.
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
        Remove all user graphics overrides.
        """

        self.graphics.reset_user()

        if self._initialized:
            self.graphics.apply_runtime(
                self.gpu_context,
                self.renderer,
            )

    # ==========================================================
    # INPUT SETTINGS
    # ==========================================================

    def reload_input_bindings(
        self,
    ) -> None:
        """
        Reload effective key bindings.
        """

        self.input.reload_bindings()

    def save_input_bindings(
        self,
    ) -> None:
        """
        Store only user binding overrides.
        """

        self.input.save_bindings()

    def reset_input_bindings(
        self,
    ) -> None:
        """
        Remove all user key-binding overrides.
        """

        self.input.reset_bindings()

    # ==========================================================
    # AUDIO SETTINGS
    # ==========================================================

    def _apply_audio_settings(
        self,
    ) -> None:
        """
        Apply effective audio.toml values to AudioSystem.
        """

        # ======================================================
        # Mixer channel volumes
        # ======================================================

        channel_map = {
            "master": (
                AudioChannel.MASTER
            ),
            "music": (
                AudioChannel.MUSIC
            ),
            "sfx": (
                AudioChannel.SFX
            ),
            "ambient": (
                AudioChannel.AMBIENT
            ),
            "voice": (
                AudioChannel.VOICE
            ),
        }

        for (
            name,
            channel,
        ) in channel_map.items():
            volume = float(
                self.audio_settings.get(
                    f"volume.{name}"
                )
            )

            self.audio.set_volume(
                channel,
                volume,
            )

        # ======================================================
        # Audio buses
        # ======================================================

        bus_map = {
            "master": "Master",
            "music": "Music",
            "sfx": "SFX",
            "ambient": "Ambient",
            "voice": "Voice",
        }

        for (
            setting_name,
            bus_name,
        ) in bus_map.items():
            bus = (
                self.audio.get_bus(
                    bus_name
                )
            )

            bus.volume = float(
                self.audio_settings.get(
                    f"buses."
                    f"{setting_name}."
                    f"volume"
                )
            )

            bus.muted = bool(
                self.audio_settings.get(
                    f"buses."
                    f"{setting_name}."
                    f"muted"
                )
            )

    def apply_audio_settings(
        self,
    ) -> None:
        """
        Reload audio.toml and apply mixer / bus settings.
        """

        self.audio_settings.reload()

        self._apply_audio_settings()

    def reset_audio_settings(
        self,
    ) -> None:
        """
        Remove all user audio overrides.
        """

        self.audio_settings.reset_user()

        self._apply_audio_settings()

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

        # ======================================================
        # Input
        # ======================================================

        self.input.initialize(
            self.gpu_context.window,
        )

        # ======================================================
        # Audio
        # ======================================================

        self.audio.initialize()

        # ======================================================
        # Game
        # ======================================================

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

        # ======================================================
        # Game
        # ======================================================

        shutdown = getattr(
            self.game,
            "shutdown",
            None,
        )

        if shutdown is not None:
            shutdown()

        # ======================================================
        # Audio
        # ======================================================

        try:
            self.audio.shutdown()

        except Exception as exc:
            self.logger.warning(
                "Audio shutdown failed: "
                f"{exc}"
            )

        # ======================================================
        # Debug console
        # ======================================================

        try:
            self.console.shutdown()

        except Exception as exc:
            self.logger.warning(
                "Debug console shutdown failed: "
                f"{exc}"
            )

        # ======================================================
        # Debug overlay
        # ======================================================

        try:
            self.debug_overlay.shutdown()

        except Exception as exc:
            self.logger.warning(
                "Debug overlay shutdown failed: "
                f"{exc}"
            )

        # ======================================================
        # Renderer
        # ======================================================

        try:
            self.renderer.destroy()

        except Exception as exc:
            self.logger.warning(
                "Renderer shutdown failed: "
                f"{exc}"
            )

        # ======================================================
        # Assets
        # ======================================================

        try:
            self.assets.shutdown()

        except Exception as exc:
            self.logger.warning(
                "AssetManager shutdown failed: "
                f"{exc}"
            )

        # ======================================================
        # GPU
        # ======================================================

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