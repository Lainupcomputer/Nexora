from __future__ import annotations

import pygame

from nexora.core.time import Time
from nexora.input import InputManager


class GameLoop:
    def __init__(
        self,
        engine,
        target_fps: int = 144,
        fixed_delta_time: float = 1.0 / 60.0,
    ):
        self.engine = engine
        self.game = engine.game

        self.target_fps = target_fps

        self.clock = pygame.time.Clock()
        self.time = Time(
            fixed_delta_time=fixed_delta_time
        )

        self.input: InputManager = engine.input
        self.renderer = engine.renderer

        self.running = False

        self.delta_time = 0.0
        self.total_time = 0.0
        self.frame = 0

    def run(self) -> None:
        self.running = True

        self.input.initialize()

        while self.running:
            self.clock.tick(self.target_fps)

            self.time.begin_frame()

            self.delta_time = self.time.delta_time
            self.total_time = self.time.total_time
            self.frame = self.time.frame

            # ----------------------------------------------------------
            # Events + Input
            # ----------------------------------------------------------

            events = pygame.event.get()

            self.input.begin_frame(events)

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

                self.game.handle_event(event)

            # ----------------------------------------------------------
            # Fixed Update
            # ----------------------------------------------------------

            max_fixed_updates = 8
            fixed_updates = 0

            while (
                self.time.should_fixed_update()
                and fixed_updates < max_fixed_updates
            ):
                self.game.fixed_update(
                    self.time.fixed_delta_time
                )

                self.time.consume_fixed_update()
                fixed_updates += 1

            # ----------------------------------------------------------
            # Update
            # ----------------------------------------------------------

            self.game.update(
                self.time.delta_time
            )

            # ----------------------------------------------------------
            # Render
            # ----------------------------------------------------------

            self.renderer.begin_frame()

            self.game.render()

            self.renderer.end_frame()

            # ----------------------------------------------------------
            # End Input Frame
            # ----------------------------------------------------------

            self.input.end_frame()

    def stop(self) -> None:
        self.running = False

