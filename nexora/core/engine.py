from __future__ import annotations


from nexora.core.game_loop import GameLoop
from nexora.debug.logger import Logger
from nexora.input import InputManager
from nexora.threading.context import ThreadContext
from nexora.rendering import Renderer
from nexora.rendering.gpu import GPUContext, WindowMode
from nexora.assets import AssetManager
from nexora.audio import AudioSystem

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
        width: int = 1280,
        height: int = 720,
        title: str = "Nexora",
        target_fps: int = 144,
        fixed_delta_time: float = 1.0 / 60.0,
        resizable: bool = True,
        fullscreen: bool = False,
        window_mode: WindowMode | str | None = None,
        vsync: bool = False,
    ) -> None:
        # ------------------------------------------------------
        # Main thread
        # ------------------------------------------------------

        ThreadContext.initialize()

        # ------------------------------------------------------
        # Core services
        # ------------------------------------------------------

        self.logger = Logger()
        self.assets = AssetManager()

        # ------------------------------------------------------
        # Window mode
        # ------------------------------------------------------

        if window_mode is None:
            window_mode = (
                WindowMode.FULLSCREEN
                if fullscreen
                else WindowMode.WINDOWED
            )
        else:
            window_mode = WindowMode(window_mode)

        # ------------------------------------------------------
        # GPU
        # ------------------------------------------------------

        self.gpu_context = GPUContext(
            width=width,
            height=height,
            title=title,
            vsync=vsync,
            resizable=resizable,
            window_mode=window_mode,
        )

        self.default_font = (
            self.assets.load_font(
                "fonts/Roboto-Regular.ttf",
                24.0,
            )
        )


        self.renderer = Renderer(
            self.gpu_context,
            font=self.default_font,
        )

        # ------------------------------------------------------
        # Window
        #
        # GPUContext owns the actual SDL window.
        # The public window reference exposes the same object.
        # ------------------------------------------------------

        self.window = self.gpu_context

        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input = InputManager(
            logger=self.logger,
        )

        self.audio = AudioSystem()

        # ------------------------------------------------------
        # Game
        # ------------------------------------------------------

        self.game = game

        self.game.engine = self
        self.game.renderer = self.renderer
        self.game.input = self.input
        self.game.window = self.window

        # ------------------------------------------------------
        # Game loop
        # ------------------------------------------------------

        self.loop = GameLoop(
            self,
            target_fps=target_fps,
            fixed_delta_time=fixed_delta_time,
        )

        self._initialized = False
        self._shutdown = False

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def time(self):
        return self.loop.time

    @property
    def delta_time(self) -> float:
        return self.time.delta_time

    @property
    def unscaled_delta_time(self) -> float:
        return self.time.unscaled_delta_time

    @property
    def total_time(self) -> float:
        return self.time.total_time

    @property
    def fixed_time(self) -> float:
        return self.time.fixed_time

    @property
    def frame(self) -> int:
        return self.time.frame

    @property
    def fixed_frame(self) -> int:
        return self.time.fixed_frame

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def initialize(self) -> None:
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

    def run(self) -> None:
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

    def stop(self) -> None:
        self.loop.stop()

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self.audio.shutdown()

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

        # ------------------------------------------------------
        # Destroy renderer first.
        #
        # GPU resources depend on the GPU device.
        # ------------------------------------------------------

        self.renderer.destroy()
        self.assets.shutdown()
        # ------------------------------------------------------
        # Destroy GPU context after all GPU resources.
        # ------------------------------------------------------

        self.gpu_context.destroy()

        self._shutdown = True

        self.logger.info(
            "Nexora Engine shut down."
        )