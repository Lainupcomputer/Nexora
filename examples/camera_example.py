from __future__ import annotations

import math

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class CameraExample(Game):
    """
    Nexora camera example.

    Controls
    --------
    WASD / Arrow keys
        Move the player

    Q / E
        Zoom out / in

    R
        Reset camera

    SPACE
        Camera shake

    ESC
        Exit
    """

    def __init__(self) -> None:
        super().__init__(
            title="Nexora - Camera Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        # ------------------------------------------------------
        # World
        # ------------------------------------------------------

        self.world_width = 2400.0
        self.world_height = 1600.0

        # ------------------------------------------------------
        # Player
        # ------------------------------------------------------

        self.player_x = self.world_width * 0.5
        self.player_y = self.world_height * 0.5

        self.player_speed = 350.0

        self.player_rotation = 0.0
        self.player_scale = 1.0

        # ------------------------------------------------------
        # Camera
        # ------------------------------------------------------

        self.camera_smooth = 0.12

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        self.texture: GPUTexture | None = None

        self.sprite_width = 96.0
        self.sprite_height = 96.0

        # ------------------------------------------------------
        # Demo objects
        # ------------------------------------------------------

        self.objects: list[tuple[float, float, float]] = []

        self._create_world_objects()

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self) -> None:
        self.input.bind("left", "A")
        self.input.bind("right", "D")
        self.input.bind("up", "W")
        self.input.bind("down", "S")

        self.input.bind("zoom_out", "Q")
        self.input.bind("zoom_in", "E")

        self.input.bind("reset_camera", "R")
        self.input.bind("shake", "SPACE")
        self.input.bind("escape", "ESCAPE")

        print("Loading: assets\\demo_sprite.png")

        image = self.assets.load_texture(
            "demo_sprite.png"
        )

        print(
            f"Image loaded: "
            f"{image.width}x{image.height}"
        )

        print(
            f"Pixel data: "
            f"{image.byte_size} bytes"
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
            f"GPU texture created: "
            f"{image.width}x{image.height}"
        )

        # ------------------------------------------------------
        # Configure camera
        # ------------------------------------------------------

        camera = self.renderer.camera

        camera.set_position(
            self.player_x,
            self.player_y,
        )

        camera.set_zoom(
            1.0,
            immediate=True,
        )

        camera.min_zoom = 0.5
        camera.max_zoom = 2.0
        camera.zoom_speed = 8.0

        # World bounds
        camera.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        # Dead zone around player
        camera.set_dead_zone(
            240.0,
            140.0,
        )

        print("Camera initialized.")

    # ==========================================================
    # WORLD
    # ==========================================================

    def _create_world_objects(self) -> None:
        """
        Create a grid of demo sprites.

        Everything is stored in world coordinates.
        """

        spacing = 300.0

        columns = int(
            self.world_width // spacing
        )

        rows = int(
            self.world_height // spacing
        )

        for y in range(rows + 1):
            for x in range(columns + 1):
                world_x = x * spacing
                world_y = y * spacing

                # Don't place an object exactly on the player.
                if (
                    abs(world_x - self.player_x) < 120.0
                    and abs(world_y - self.player_y) < 120.0
                ):
                    continue

                rotation = (
                    (x + y) * 0.15
                )

                self.objects.append(
                    (
                        world_x,
                        world_y,
                        rotation,
                    )
                )

    # ==========================================================
    # UPDATE
    # ==========================================================


    def update(self, dt):
        camera = self.renderer.camera

        if self.input.action("escape").pressed:
            self.stop()
            return

        move_x = 0.0
        move_y = 0.0

        if self.input.action("left").down:
            move_x -= 1

        if self.input.action("right").down:
            move_x += 1

        if self.input.action("up").down:
            move_y -= 1

        if self.input.action("down").down:
            move_y += 1

        length = math.hypot(move_x, move_y)

        if length > 0:
            move_x /= length
            move_y /= length

        self.player_x += move_x * self.player_speed * dt
        self.player_y += move_y * self.player_speed * dt

        half_width = self.sprite_width * 0.5
        half_height = self.sprite_height * 0.5

        self.player_x = max(
            half_width,
            min(
                self.world_width - half_width,
                self.player_x
            )
        )

        self.player_y = max(
            half_height,
            min(
                self.world_height - half_height,
                self.player_y
            )
        )

        if move_x != 0 or move_y != 0:
            self.player_rotation = math.atan2(
                move_y,
                move_x
            )

        if self.input.action("zoom_out").down:
            camera.zoom_by(-1.0 * dt)

        if self.input.action("zoom_in").down:
            camera.zoom_by(1.0 * dt)

        if self.input.action("reset_camera").pressed:
            camera.set_position(
                self.player_x,
                self.player_y
            )

            camera.set_zoom(
                1.0,
                immediate=True
            )

            camera.stop_shake()

        camera.follow(
            self.player_x,
            self.player_y,
            smooth=self.camera_smooth,
            delta_time=dt
        )

        camera.clamp(
            self.renderer.width,
            self.renderer.height
        )

        camera.update_zoom(dt)

        if self.input.action("shake").pressed:
            print("SHAKE AUSGELÖST")
            camera.shake(
                strength=20.0,
                duration=0.35
            )

        camera.update_shake(dt)
        if camera.shake_time > 0.0:
            print(
                f"SHAKE: x={camera.shake_x:.2f}, "
                f"y={camera.shake_y:.2f}"
            )


    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self) -> None:
        if self.texture is None:
            return

        # ------------------------------------------------------
        # World objects
        # ------------------------------------------------------

        for x, y, rotation in self.objects:
            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=self.sprite_width,
                height=self.sprite_height,
                rotation=rotation,
            )

        # ------------------------------------------------------
        # Player
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            self.player_x,
            self.player_y,
            width=self.sprite_width * self.player_scale,
            height=self.sprite_height * self.player_scale,
            rotation=self.player_rotation,
        )

    # ==========================================================
    # INPUT
    # ==========================================================

    def handle_event(self, event) -> None:
        # InputManager already processes keyboard events.
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
    game = CameraExample()

    # Physical keyboard -> Nexora actions
    game_input = game

    game.run()

