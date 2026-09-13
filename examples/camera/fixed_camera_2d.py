from __future__ import annotations

from nexora import Game
from nexora.nodes import FixedCamera2D
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class FixedCameraExample(Game):
    """
    Nexora FixedCamera2D example.

    Controls
    --------
    1
        Move fixed camera to position 1

    2
        Move fixed camera to position 2

    3
        Move fixed camera to position 3

    L
        Lock camera

    U
        Unlock camera

    R
        Reset camera to its fixed position

    Z
        Toggle zoom

    S
        Camera shake

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - FixedCamera2D Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        # ======================================================
        # World
        # ======================================================

        self.world_width = 3000.0
        self.world_height = 2000.0

        # ======================================================
        # Camera
        # ======================================================

        self.camera_node: FixedCamera2D | None = None

        self.zoomed: bool = False

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
            "camera_position_1",
            "1",
        )

        self.input.bind(
            "camera_position_2",
            "2",
        )

        self.input.bind(
            "camera_position_3",
            "3",
        )

        self.input.bind(
            "camera_lock",
            "L",
        )

        self.input.bind(
            "camera_unlock",
            "U",
        )

        self.input.bind(
            "camera_reset",
            "R",
        )

        self.input.bind(
            "camera_zoom",
            "Z",
        )

        self.input.bind(
            "camera_shake",
            "S",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "FixedCameraExample"
        )

        self.scene = scene

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        print(
            r"Loading: assets\demo_sprite.png"
        )

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
        # Demo world
        # ------------------------------------------------------

        self._create_world_objects()

        # ------------------------------------------------------
        # Fixed camera
        # ------------------------------------------------------

        self.camera_node = FixedCamera2D(
            "FixedCamera",
            scene.world,
            self.renderer,
            x=600.0,
            y=500.0,
        )

        scene.add_node(
            self.camera_node
        )

        # ------------------------------------------------------
        # Camera bounds
        # ------------------------------------------------------

        self.camera_node.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        # ------------------------------------------------------
        # Zoom
        # ------------------------------------------------------

        self.camera_node.camera.min_zoom = 0.5
        self.camera_node.camera.max_zoom = 2.5

        self.camera_node.set_zoom(
            1.0
        )

        # ------------------------------------------------------
        # Information
        # ------------------------------------------------------

        print(
            "FixedCamera2D initialized."
        )

        print()
        print(
            "Controls:"
        )
        print(
            "  1 / 2 / 3 = fixed positions"
        )
        print(
            "  L         = lock"
        )
        print(
            "  U         = unlock"
        )
        print(
            "  R         = reset"
        )
        print(
            "  Z         = toggle zoom"
        )
        print(
            "  S         = shake"
        )
        print(
            "  ESC       = exit"
        )

    # ==========================================================
    # Demo world
    # ==========================================================

    def _create_world_objects(
        self,
    ) -> None:
        spacing = 250.0

        columns = int(
            self.world_width
            // spacing
        )

        rows = int(
            self.world_height
            // spacing
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

                rotation = (
                    (x + y)
                    * 0.15
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
        camera = self.camera_node

        if camera is None:
            return

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Position 1
        # ------------------------------------------------------

        if self.input.action(
            "camera_position_1"
        ).pressed:
            camera.set_fixed_position(
                600.0,
                500.0,
            )

            print(
                "Fixed position: 1"
            )

        # ------------------------------------------------------
        # Position 2
        # ------------------------------------------------------

        if self.input.action(
            "camera_position_2"
        ).pressed:
            camera.set_fixed_position(
                1500.0,
                1000.0,
            )

            print(
                "Fixed position: 2"
            )

        # ------------------------------------------------------
        # Position 3
        # ------------------------------------------------------

        if self.input.action(
            "camera_position_3"
        ).pressed:
            camera.set_fixed_position(
                2400.0,
                1400.0,
            )

            print(
                "Fixed position: 3"
            )

        # ------------------------------------------------------
        # Lock
        # ------------------------------------------------------

        if self.input.action(
            "camera_lock"
        ).pressed:
            camera.lock()

            print(
                "Camera locked."
            )

        # ------------------------------------------------------
        # Unlock
        # ------------------------------------------------------

        if self.input.action(
            "camera_unlock"
        ).pressed:
            camera.unlock()

            print(
                "Camera unlocked."
            )

        # ------------------------------------------------------
        # Reset
        # ------------------------------------------------------

        if self.input.action(
            "camera_reset"
        ).pressed:
            camera.reset_position()

            print(
                "Camera reset."
            )

        # ------------------------------------------------------
        # Zoom
        # ------------------------------------------------------

        if self.input.action(
            "camera_zoom"
        ).pressed:
            self.zoomed = (
                not self.zoomed
            )

            if self.zoomed:
                camera.set_zoom(
                    1.5
                )

                print(
                    "Camera zoom: 1.5"
                )

            else:
                camera.set_zoom(
                    1.0
                )

                print(
                    "Camera zoom: 1.0"
                )

        # ------------------------------------------------------
        # Shake
        # ------------------------------------------------------

        if self.input.action(
            "camera_shake"
        ).pressed:
            camera.shake(
                intensity=20.0,
                duration=0.35,
            )

            print(
                "Camera shake."
            )

        # ------------------------------------------------------
        # Scene update
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
        # World grid
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
        # Fixed camera locations
        #
        # Larger sprites make the three camera positions easy
        # to identify while testing.
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            600.0,
            500.0,
            width=180.0,
            height=180.0,
            rotation=0.0,
        )

        self.renderer.sprite(
            self.texture,
            1500.0,
            1000.0,
            width=200.0,
            height=200.0,
            rotation=0.25,
        )

        self.renderer.sprite(
            self.texture,
            2400.0,
            1400.0,
            width=220.0,
            height=220.0,
            rotation=-0.25,
        )

        # ------------------------------------------------------
        # Scene nodes
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
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None

        super().shutdown()


if __name__ == "__main__":
    FixedCameraExample().run()