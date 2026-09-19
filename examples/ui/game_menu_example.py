"""Minimal GameMenu example.

Run from the Nexora Engine project root with:

    python -Xgil=0 examples/ui/game_menu_example.py

The example opens the menu once at startup so the node is immediately
visible. Remove the final ``self.game_menu.open()`` line in ``initialize``
to start in gameplay and open it with the configured ``pause`` action.
"""

from __future__ import annotations

from nexora import Game
from nexora.scene import Scene


class DemoGameplayScene(Scene):
    """Small scene that visibly stops updating while the menu is open."""

    def __init__(self, game: "GameMenuExample") -> None:
        super().__init__("DemoGameplay")
        self.game = game
        self.elapsed = 0.0

    def update(self, delta_time: float) -> None:
        self.elapsed += delta_time

    def render(self, interpolation: float) -> None:
        del interpolation

        renderer = self.game.renderer
        if renderer is None:
            return

        renderer.rect(
            -640.0,
            -360.0,
            1280.0,
            720.0,
            color=(0.035, 0.055, 0.085, 1.0),
        )

        renderer.rect(
            -310.0,
            -150.0,
            620.0,
            300.0,
            color=(0.09, 0.12, 0.16, 1.0),
            radius=10.0,
        )

        renderer.text(
            "NEXORA GAME MENU EXAMPLE",
            -205.0,
            -75.0,
            scale=1.25,
        )
        renderer.text(
            "The timer pauses together with this scene.",
            -205.0,
            -25.0,
            scale=0.9,
        )
        renderer.text(
            f"Gameplay time: {self.elapsed:06.1f}s",
            -205.0,
            25.0,
            scale=0.9,
        )
        renderer.text(
            "Press Escape to open or close the menu.",
            -205.0,
            85.0,
            scale=0.9,
        )


class GameMenuExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="GameMenuExample",
            title="Nexora GameMenu Example",
            width=1280,
            height=720,
            resizable=True,
        )

        self.gameplay: DemoGameplayScene | None = None
        self.game_menu = None

    def initialize(self) -> None:
        self.gameplay = DemoGameplayScene(self)
        self.scene = self.gameplay

        self.game_menu = self.create_game_menu(
            pause_on_open=True,
            on_save=self.save_example,
            on_options=self.open_options,
            on_main_menu=self.open_main_menu,
            on_quit=self.stop,
        )

        # The example starts with the menu visible for a quick test.
        # Delete this line to start closed and use the pause action instead.
        self.game_menu.open()

    def save_example(self) -> None:
        self.saves.quick_save(
            {
                "example": True,
                "scene": self.scene.name if self.scene is not None else None,
                "elapsed": (
                    self.gameplay.elapsed
                    if self.gameplay is not None
                    else 0.0
                ),
            },
            name="GameMenu Example Save",
        )
        print("[GameMenu] Example save created.")

    def open_options(self) -> None:
        print("[GameMenu] Options callback")

    def open_main_menu(self) -> None:
        print("[GameMenu] Main Menu callback")


if __name__ == "__main__":
    GameMenuExample().run()