from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class SceneExample(Game):
    """
    Nexora scene hierarchy example.

    Controls
    --------
    WASD
        Move the player

    Q / E
        Rotate the player

    R / T
        Scale the player

    ESC
        Exit
    """

    def __init__(self) -> None:
        super().__init__(
            title="Nexora - Scene Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        self.scene = Scene("MainScene")

        self.world = self.scene.create_node(
            "World"
        )

        self.player = self.scene.create_node(
            "Player",
            parent=self.world,
        )

        self.weapon = self.scene.create_node(
            "Weapon",
            parent=self.player,
        )

        # ------------------------------------------------------
        # Transforms
        # ------------------------------------------------------

        self.player.transform.x = 0.0
        self.player.transform.y = 0.0

        self.weapon.transform.x = 120.0
        self.weapon.transform.y = 0.0
        self.weapon.transform.rotation = 45.0

        self.player_speed = 300.0
        self.rotation_speed = 120.0
        self.scale_speed = 1.0

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        self.texture: GPUTexture | None = None

        self.sprite_width = 96.0
        self.sprite_height = 96.0

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self) -> None:
        self.input.bind(
            "left",
            "A",
        )

        self.input.bind(
            "right",
            "D",
        )

        self.input.bind(
            "up",
            "W",
        )

        self.input.bind(
            "down",
            "S",
        )

        self.input.bind(
            "rotate_left",
            "Q",
        )

        self.input.bind(
            "rotate_right",
            "E",
        )

        self.input.bind(
            "scale_down",
            "R",
        )

        self.input.bind(
            "scale_up",
            "T",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        print(
            "Loading: assets\\demo_sprite.png"
        )

        image = self.assets.load_texture(
            "demo_sprite.png"
        )

        print(
            f"Image loaded: "
            f"{image.width}x{image.height}"
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        self.sprite_width = float(image.width)
        self.sprite_height = float(image.height)

        print(
            "GPU texture created."
        )

        print()
        print("Scene hierarchy:")
        print()
        print("MainScene")
        print("└── World")
        print("    └── Player")
        print("        └── Weapon")
        print()

        print(
            f"Player world position: "
            f"{self.player.world_position}"
        )

        print(
            f"Weapon world position: "
            f"{self.weapon.world_position}"
        )

        print(
            f"Weapon world rotation: "
            f"{self.weapon.world_rotation}"
        )

        print()
        print("Controls:")
        print("  WASD  - Move")
        print("  Q/E   - Rotate")
        print("  R/T   - Scale")
        print("  ESC   - Exit")
        print()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(self, dt: float) -> None:
        if self.input.action("escape").pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Movement
        # ------------------------------------------------------

        move_x = 0.0
        move_y = 0.0

        if self.input.action("left").down:
            move_x -= 1.0

        if self.input.action("right").down:
            move_x += 1.0

        if self.input.action("up").down:
            move_y -= 1.0

        if self.input.action("down").down:
            move_y += 1.0

        self.player.transform.x += (
            move_x * self.player_speed * dt
        )

        self.player.transform.y += (
            move_y * self.player_speed * dt
        )

        # ------------------------------------------------------
        # Rotation
        # ------------------------------------------------------

        if self.input.action("rotate_left").down:
            self.player.transform.rotation -= (
                self.rotation_speed * dt
            )

        if self.input.action("rotate_right").down:
            self.player.transform.rotation += (
                self.rotation_speed * dt
            )

        # ------------------------------------------------------
        # Scale
        # ------------------------------------------------------

        if self.input.action("scale_down").down:
            self.player.transform.scale_x -= (
                self.scale_speed * dt
            )

            self.player.transform.scale_y -= (
                self.scale_speed * dt
            )

        if self.input.action("scale_up").down:
            self.player.transform.scale_x += (
                self.scale_speed * dt
            )

            self.player.transform.scale_y += (
                self.scale_speed * dt
            )

        # Prevent the player from disappearing completely.
        self.player.transform.scale_x = max(
            0.25,
            self.player.transform.scale_x,
        )

        self.player.transform.scale_y = max(
            0.25,
            self.player.transform.scale_y,
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self) -> None:
        if self.texture is None:
            return

        # ------------------------------------------------------
        # Player
        # ------------------------------------------------------

        player_x, player_y = (
            self.player.world_position
        )

        player_scale_x, player_scale_y = (
            self.player.world_scale
        )

        self.renderer.sprite(
            self.texture,
            player_x,
            player_y,
            width=self.sprite_width * player_scale_x,
            height=self.sprite_height * player_scale_y,
            rotation=self.player.world_rotation,
        )

        # ------------------------------------------------------
        # Weapon / child node
        # ------------------------------------------------------

        weapon_x, weapon_y = (
            self.weapon.world_position
        )

        weapon_scale_x, weapon_scale_y = (
            self.weapon.world_scale
        )

        self.renderer.sprite(
            self.texture,
            weapon_x,
            weapon_y,
            width=(
                self.sprite_width
                * 0.5
                * weapon_scale_x
            ),
            height=(
                self.sprite_height
                * 0.5
                * weapon_scale_y
            ),
            rotation=self.weapon.world_rotation,
        )

    # ==========================================================
    # INPUT
    # ==========================================================

    def handle_event(self, event) -> None:
        pass

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(self) -> None:
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    game = SceneExample()
    game.run()