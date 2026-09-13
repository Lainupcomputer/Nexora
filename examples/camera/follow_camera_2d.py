from __future__ import annotations

import math

from nexora import Game
from nexora.nodes import (
    AnimatedSprite,
    CharacterBody2D,
    FollowCamera2D,
)
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class FollowCameraExample(Game):
    """
    Nexora FollowCamera2D example.

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

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - FollowCamera2D Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        # ======================================================
        # World
        # ======================================================

        self.world_width = 2400.0
        self.world_height = 1600.0

        # ======================================================
        # Player
        # ======================================================

        self.player: CharacterBody2D | None = None

        self.player_sprite: AnimatedSprite | None = None

        self.player_speed = 350.0

        # ======================================================
        # Camera
        # ======================================================

        self.follow_camera: FollowCamera2D | None = None

        # ======================================================
        # Texture
        # ======================================================

        self.texture: GPUTexture | None = None

        self.sprite_width = 96.0
        self.sprite_height = 96.0

        # ======================================================
        # Demo world
        # ======================================================

        self.objects: list[
            tuple[
                float,
                float,
                float,
            ]
        ] = []

    # ==========================================================
    # Initialize
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

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
            "zoom_out",
            "Q",
        )

        self.input.bind(
            "zoom_in",
            "E",
        )

        self.input.bind(
            "reset_camera",
            "R",
        )

        self.input.bind(
            "shake",
            "SPACE",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "FollowCameraExample"
        )

        self.scene = scene

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        image = self.assets.load_texture(
            "demo_sprite.png"
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        self.sprite_width = float(
            image.width
        )

        self.sprite_height = float(
            image.height
        )

        # ------------------------------------------------------
        # Player body
        # ------------------------------------------------------

        self.player = CharacterBody2D(
            "Player",
            scene.world,
        )

        self.player.transform.x = (
            self.world_width * 0.5
        )

        self.player.transform.y = (
            self.world_height * 0.5
        )

        self.player.set_collision_size(
            self.sprite_width,
            self.sprite_height,
        )

        scene.add_node(
            self.player
        )

        # ------------------------------------------------------
        # Player sprite
        # ------------------------------------------------------

        self.player_sprite = AnimatedSprite(
            "PlayerSprite",
            scene.world,
        )

        self.player_sprite.texture = (
            self.texture
        )

        self.player_sprite.width = (
            self.sprite_width
        )

        self.player_sprite.height = (
            self.sprite_height
        )

        # CharacterBody2D uses top-left position.
        #
        # AnimatedSprite defaults to a centered origin,
        # therefore move the sprite to the middle of the body.
        self.player_sprite.transform.x = (
            self.sprite_width * 0.5
        )

        self.player_sprite.transform.y = (
            self.sprite_height * 0.5
        )

        self.player.add_child(
            self.player_sprite
        )

        # ------------------------------------------------------
        # Follow camera
        # ------------------------------------------------------

        self.follow_camera = FollowCamera2D(
            "PlayerCamera",
            scene.world,
            self.renderer,
        )

        self.player.add_child(
            self.follow_camera
        )

        self.follow_camera.set_smoothing(
            0.12
        )

        self.follow_camera.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        self.follow_camera.set_dead_zone(
            240.0,
            140.0,
        )

        # ------------------------------------------------------
        # Camera configuration
        # ------------------------------------------------------

        camera = (
            self.follow_camera.camera
        )

        camera.min_zoom = 0.5
        camera.max_zoom = 2.0
        camera.zoom_speed = 8.0

        self.follow_camera.set_zoom(
            1.0
        )

        self.follow_camera.snap_to_target()

        # ------------------------------------------------------
        # Demo world
        # ------------------------------------------------------

        self._create_world_objects()

    # ==========================================================
    # Demo world
    # ==========================================================

    def _create_world_objects(
        self,
    ) -> None:
        spacing = 300.0

        columns = int(
            self.world_width
            // spacing
        )

        rows = int(
            self.world_height
            // spacing
        )

        center_x = (
            self.world_width * 0.5
        )

        center_y = (
            self.world_height * 0.5
        )

        for y in range(
            rows + 1
        ):
            for x in range(
                columns + 1
            ):
                world_x = (
                    x * spacing
                )

                world_y = (
                    y * spacing
                )

                if (
                    abs(
                        world_x
                        - center_x
                    )
                    < 120.0
                    and abs(
                        world_y
                        - center_y
                    )
                    < 120.0
                ):
                    continue

                rotation = (
                    (x + y)
                    * 15.0
                )

                self.objects.append(
                    (
                        world_x,
                        world_y,
                        rotation,
                    )
                )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if (
            self.player is None
            or self.follow_camera is None
        ):
            return

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if (
            self.input.action(
                "escape"
            ).pressed
        ):
            self.stop()
            return

        # ------------------------------------------------------
        # Movement input
        # ------------------------------------------------------

        move_x = 0.0
        move_y = 0.0

        if self.input.action(
            "left"
        ).down:
            move_x -= 1.0

        if self.input.action(
            "right"
        ).down:
            move_x += 1.0

        if self.input.action(
            "up"
        ).down:
            move_y -= 1.0

        if self.input.action(
            "down"
        ).down:
            move_y += 1.0

        # ------------------------------------------------------
        # Normalize movement
        # ------------------------------------------------------

        length = math.hypot(
            move_x,
            move_y,
        )

        if length > 0.0:
            move_x /= length
            move_y /= length

        # ------------------------------------------------------
        # Move CharacterBody2D
        #
        # There is intentionally no TileCollision in this
        # example. We only use CharacterBody2D as the moving
        # scene entity the camera follows.
        # ------------------------------------------------------

        self.player.velocity.x = (
            move_x
            * self.player_speed
        )

        self.player.velocity.y = (
            move_y
            * self.player_speed
        )

        self.player.transform.x += (
            self.player.velocity.x
            * delta_time
        )

        self.player.transform.y += (
            self.player.velocity.y
            * delta_time
        )

        # ------------------------------------------------------
        # Keep player inside world
        # ------------------------------------------------------

        self.player.transform.x = max(
            0.0,
            min(
                self.world_width
                - self.player.collision_width,

                self.player.transform.x,
            ),
        )

        self.player.transform.y = max(
            0.0,
            min(
                self.world_height
                - self.player.collision_height,

                self.player.transform.y,
            ),
        )

        # ------------------------------------------------------
        # Player rotation
        # ------------------------------------------------------

        if (
            move_x != 0.0
            or move_y != 0.0
        ):
            self.player.transform.rotation = (
                math.degrees(
                    math.atan2(
                        move_y,
                        move_x,
                    )
                )
            )

        # ------------------------------------------------------
        # Zoom
        # ------------------------------------------------------

        if self.input.action(
            "zoom_out"
        ).down:
            self.follow_camera.camera.zoom_by(
                -1.0
                * delta_time
            )

        if self.input.action(
            "zoom_in"
        ).down:
            self.follow_camera.camera.zoom_by(
                1.0
                * delta_time
            )

        # ------------------------------------------------------
        # Reset camera
        # ------------------------------------------------------

        if self.input.action(
            "reset_camera"
        ).pressed:
            self.follow_camera.set_zoom(
                1.0
            )

            self.follow_camera.stop_shake()

            self.follow_camera.snap_to_target()

        # ------------------------------------------------------
        # Shake
        # ------------------------------------------------------

        if self.input.action(
            "shake"
        ).pressed:
            self.follow_camera.shake(
                intensity=20.0,
                duration=0.35,
            )

        # ------------------------------------------------------
        # Scene + FollowCamera update
        # ------------------------------------------------------

        super().update(
            delta_time
        )

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        if self.texture is None:
            return

        # ------------------------------------------------------
        # Demo objects
        # ------------------------------------------------------

        for (
            x,
            y,
            rotation,
        ) in self.objects:
            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=self.sprite_width,
                height=self.sprite_height,
                rotation=rotation,
            )

        # ------------------------------------------------------
        # Scene nodes
        #
        # This renders AnimatedSprite and all other visible nodes.
        # ------------------------------------------------------

        super().render(
            interpolation
        )

    # ==========================================================
    # Shutdown
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        super().shutdown()

        if self.texture is not None:
            self.texture.destroy()
            self.texture = None


if __name__ == "__main__":
    FollowCameraExample().run()