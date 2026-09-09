from __future__ import annotations

import pygame

from nexora.core.game_loop import GameLoop
from nexora.debug.logger import Logger
from nexora.input import InputManager
from nexora.threading.context import ThreadContext
from nexora.window.window import Window
from nexora.rendering import Renderer

class Engine:
    """
    Central Nexora Engine.

    Owns the main engine services and controls the game loop.
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
        vsync: bool = False,
    ) -> None:
        # --------------------------------------------------------------
        # Main thread
        # --------------------------------------------------------------

        ThreadContext.initialize()

        # --------------------------------------------------------------
        # Pygame
        # --------------------------------------------------------------

        pygame.init()

        # --------------------------------------------------------------
        # Core services
        # --------------------------------------------------------------

        self.logger = Logger()

        self.window = Window(
            width=width,
            height=height,
            title=title,
            resizable=resizable,
            fullscreen=fullscreen,
            vsync=vsync,
        )
        self.renderer = Renderer(
            self.window
        )

        self.input = InputManager(
            logger=self.logger,
        )

        self.game = game
        self.game.renderer = self.renderer

        # --------------------------------------------------------------
        # Game loop
        # --------------------------------------------------------------

        self.loop = GameLoop(
            self,
            target_fps=target_fps,
            fixed_delta_time=fixed_delta_time,
        )

        # --------------------------------------------------------------
        # Game references
        # --------------------------------------------------------------

        self.game.engine = self
        self.game.input = self.input
        self.game.window = self.window

        self._initialized = False
        self._shutdown = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def time(self):
        return self.loop.time

    @property
    def delta_time(self) -> float:
        return self.loop.delta_time

    @property
    def total_time(self) -> float:
        return self.loop.total_time

    @property
    def frame(self) -> int:
        return self.loop.frame

    @property
    def surface(self):
        return self.window.surface

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._initialized:
            return

        ThreadContext.assert_main_thread(
            "Engine.initialize"
        )

        self.input.initialize()

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

    def run(self) -> None:
        if self._shutdown:
            raise RuntimeError(
                "Cannot run an engine that has already been shut down."
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

    def stop(self) -> None:
        self.loop.stop()

    def shutdown(self) -> None:
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

        self.window.destroy()

        self._shutdown = True

        self.logger.info(
            "Nexora Engine shut down."
        )