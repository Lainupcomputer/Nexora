from __future__ import annotations

from nexora import Game
from nexora.nodes import Panel
from nexora.scene import Scene


class UIPanelBorderTest(Game):
    def __init__(self) -> None:
        super().__init__(
            title="Nexora - UI Panel Border Test",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.scene = Scene("MainScene")

        # --------------------------------------------------
        # Panel
        # --------------------------------------------------

        self.panel = self.scene.ui.create_child(
            "TestPanel",
            node_type=Panel,
        )

        self.panel.size = (
            500.0,
            300.0,
        )

        self.panel.anchor = (
            0.5,
            0.5,
        )

        self.panel.position = (
            0.0,
            0.0,
        )

        self.panel.background = (
            40,
            120,
            220,
            255,
        )

        self.panel.border_color = (
            255,
            255,
            255,
            255,
        )

        self.panel.border_width = 6.0
        self.panel.border_radius = 30.0

    def initialize(self) -> None:
        print()
        print("UI Panel Rounded Corner Test")
        print()
        print("MainScene")
        print("└── UI")
        print("    └── TestPanel")
        print()

        print(
            f"Panel size: "
            f"{self.panel.size}"
        )

        print(
            f"Panel anchor: "
            f"{self.panel.anchor}"
        )

        print(
            f"Panel position: "
            f"{self.panel.position}"
        )

        print(
            f"Border color: "
            f"{self.panel.border_color}"
        )

        print(
            f"Border width: "
            f"{self.panel.border_width}"
        )

        print(
            f"Border radius: "
            f"{self.panel.border_radius}"
        )

    def update(self, dt: float) -> None:
        pass

    def render(self, interpolation: float) -> None:
        self.scene.ui.set_viewport_size(
            self.renderer.width,
            self.renderer.height,
        )

        self.scene.render(
            interpolation,
        )

        self.scene.ui.render(
            self.renderer,
        )

    def handle_event(self, event) -> None:
        pass

    def shutdown(self) -> None:
        pass


if __name__ == "__main__":
    game = UIPanelBorderTest()
    game.run()
