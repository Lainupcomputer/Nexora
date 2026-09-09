from __future__ import annotations

from pathlib import Path

import pygame

from nexora import Engine


class SpriteGame:
    def __init__(self) -> None:
        self.engine = None
        self.renderer = None
        self.input = None
        self.window = None

        self.texture = None

        self.x = 0.0
        self.y = 0.0
        self.rotation = 0.0
        self.scale = 1.0

    def initialize(self) -> None:
        self.texture = self.engine.assets.load_texture(
            "demo_sprite.png"
        )

        self.x = 0.0
        self.y = 0.0

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.engine.stop()

    def fixed_update(self, delta_time: float) -> None:
        pass

    def update(self, delta_time: float) -> None:
        movement_speed = 300.0
        rotation_speed = 120.0
        scale_speed = 1.0

        # --------------------------------------------------------------
        # Movement
        # --------------------------------------------------------------

        if self.input.is_down("left"):
            self.x -= movement_speed * delta_time

        if self.input.is_down("right"):
            self.x += movement_speed * delta_time

        if self.input.is_down("up"):
            self.y -= movement_speed * delta_time

        if self.input.is_down("down"):
            self.y += movement_speed * delta_time

        # --------------------------------------------------------------
        # Rotation
        # --------------------------------------------------------------

        if self.input.is_down("rotate_left"):
            self.rotation += rotation_speed * delta_time

        if self.input.is_down("rotate_right"):
            self.rotation -= rotation_speed * delta_time

        # --------------------------------------------------------------
        # Scale
        # --------------------------------------------------------------

        if self.input.is_down("zoom_in"):
            self.scale += scale_speed * delta_time

        if self.input.is_down("zoom_out"):
            self.scale -= scale_speed * delta_time

        self.scale = max(
            0.25,
            min(4.0, self.scale),
        )

        # --------------------------------------------------------------
        # Camera
        # --------------------------------------------------------------

        self.renderer.camera.look_at(
            self.x,
            self.y,
        )

        self.renderer.camera.update(
            delta_time
        )

    def render(self) -> None:
        renderer = self.renderer

        # --------------------------------------------------------------
        # World grid
        # --------------------------------------------------------------

        grid_size = 100

        for x in range(-2000, 2001, grid_size):
            renderer.world_line(
                (x, -2000),
                (x, 2000),
                (50, 50, 60),
            )

        for y in range(-2000, 2001, grid_size):
            renderer.world_line(
                (-2000, y),
                (2000, y),
                (50, 50, 60),
            )

        # --------------------------------------------------------------
        # Sprite
        # --------------------------------------------------------------

        renderer.world_sprite(
            self.texture,
            self.x,
            self.y,
            scale=self.scale,
            rotation=self.rotation,
        )

        # --------------------------------------------------------------
        # Debug information
        # --------------------------------------------------------------

        renderer.text(
            "WASD / Arrow Keys: Move",
            20,
            20,
            size=22,
        )

        renderer.text(
            "Q / E: Rotate",
            20,
            50,
            size=22,
        )

        renderer.text(
            "Z / X: Scale",
            20,
            80,
            size=22,
        )

        renderer.text(
            "ESC: Quit",
            20,
            110,
            size=22,
        )

        renderer.text(
            f"Position: {self.x:.1f}, {self.y:.1f}",
            20,
            150,
            size=20,
        )

        renderer.text(
            f"Rotation: {self.rotation:.1f}°",
            20,
            180,
            size=20,
        )

        renderer.text(
            f"Scale: {self.scale:.2f}",
            20,
            210,
            size=20,
        )

    def shutdown(self) -> None:
        pass


def create_demo_texture() -> None:
    """
    Create a small demo texture automatically.

    This keeps the example self-contained and means no external
    image asset is required.
    """

    assets_path = Path("assets")

    assets_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    texture_path = assets_path / "demo_sprite.png"

    if texture_path.exists():
        return

    surface = pygame.Surface(
        (96, 96),
        pygame.SRCALPHA,
    )

    # --------------------------------------------------------------
    # Body
    # --------------------------------------------------------------

    pygame.draw.circle(
        surface,
        (240, 180, 40),
        (48, 48),
        42,
    )

    # --------------------------------------------------------------
    # Eyes
    # --------------------------------------------------------------

    pygame.draw.circle(
        surface,
        (30, 30, 35),
        (32, 38),
        8,
    )

    pygame.draw.circle(
        surface,
        (30, 30, 35),
        (64, 38),
        8,
    )

    # --------------------------------------------------------------
    # Mouth
    # --------------------------------------------------------------

    pygame.draw.arc(
        surface,
        (30, 30, 35),
        (28, 48, 40, 28),
        0,
        3.14,
        4,
    )

    # --------------------------------------------------------------
    # Nose
    # --------------------------------------------------------------

    pygame.draw.polygon(
        surface,
        (220, 70, 70),
        [
            (48, 48),
            (35, 62),
            (61, 62),
        ],
    )

    pygame.image.save(
        surface,
        texture_path,
    )


def main() -> None:
    pygame.init()

    # Create the demo texture before the AssetManager
    # attempts to load it.
    create_demo_texture()

    game = SpriteGame()

    engine = Engine(
        game,
        width=1280,
        height=720,
        title="Nexora - Sprite Example",
        target_fps=144,
    )

    # --------------------------------------------------------------
    # Movement
    # --------------------------------------------------------------

    engine.input.bind(
        "left",
        "A",
    )

    engine.input.bind(
        "right",
        "D",
    )

    engine.input.bind(
        "up",
        "W",
    )

    engine.input.bind(
        "down",
        "S",
    )

    engine.input.bind(
        "left",
        "LEFT",
    )

    engine.input.bind(
        "right",
        "RIGHT",
    )

    engine.input.bind(
        "up",
        "UP",
    )

    engine.input.bind(
        "down",
        "DOWN",
    )

    # --------------------------------------------------------------
    # Rotation
    # --------------------------------------------------------------

    engine.input.bind(
        "rotate_left",
        "Q",
    )

    engine.input.bind(
        "rotate_right",
        "E",
    )

    # --------------------------------------------------------------
    # Scale
    # --------------------------------------------------------------

    engine.input.bind(
        "zoom_in",
        "Z",
    )

    engine.input.bind(
        "zoom_out",
        "X",
    )

    # --------------------------------------------------------------
    # Start
    # --------------------------------------------------------------

    engine.run()


if __name__ == "__main__":
    main()

