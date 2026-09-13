from __future__ import annotations

from nexora import Game
from nexora.nodes.camera import FreeCamera2D
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class FreeCameraExample(Game):
    """
    Nexora FreeCamera2D example.

    Controls
    --------
    WASD
        Move camera

    Left Shift
        Faster movement

    Mouse Wheel
        Zoom

    Middle Mouse Button
        Drag / pan camera

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
            title="Nexora - FreeCamera2D Example",
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

        self.free_camera: FreeCamera2D | None = None

        # ======================================================
        # Texture
        # ======================================================

        self.texture: GPUTexture | None = None

        self.sprite_width = 96.0
        self.sprite_height = 96.0

        # ======================================================
        # Demo objects
        # ======================================================

        self.objects: list[
            tuple[
                float,
                float,
                float,
            ]
        ] = []

        self._create_world_objects()

    # ==========================================================
    # Initialize
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Camera input
        # ------------------------------------------------------

        self.input.bind(
            "camera_left",
            "A",
        )

        self.input.bind(
            "camera_right",
            "D",
        )

        self.input.bind(
            "camera_up",
            "W",
        )

        self.input.bind(
            "camera_down",
            "S",
        )

        self.input.bind(
            "camera_boost",
            "LSHIFT",
        )

        # ------------------------------------------------------
        # Example input
        # ------------------------------------------------------

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
            "FreeCameraExample"
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
        # Free camera
        # ------------------------------------------------------

        self.free_camera = FreeCamera2D(
            "FreeCamera",
            scene.world,
            self.renderer,
            self.input,
        )

        scene.add_node(
            self.free_camera
        )

        # Start in the middle of the map.
        self.free_camera.set_position(
            self.world_width * 0.5,
            self.world_height * 0.5,
        )

        # Camera bounds.
        self.free_camera.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        # Movement.
        self.free_camera.set_move_speed(
            700.0
        )

        self.free_camera.set_boost_multiplier(
            2.5
        )

        # Zoom.
        self.free_camera.camera.min_zoom = 0.4
        self.free_camera.camera.max_zoom = 2.5
        self.free_camera.camera.zoom_speed = 8.0

        self.free_camera.set_zoom(
            1.0
        )

        print(
            "FreeCamera2D initialized."
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
        if self.free_camera is None:
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
        # Reset camera
        # ------------------------------------------------------

        if self.input.action(
            "reset_camera"
        ).pressed:
            self.free_camera.set_position(
                self.world_width * 0.5,
                self.world_height * 0.5,
            )

            self.free_camera.camera.set_zoom(
                1.0,
                immediate=True,
            )

            self.free_camera.stop_shake()

        # ------------------------------------------------------
        # Shake
        # ------------------------------------------------------

        if self.input.action(
            "shake"
        ).pressed:
            self.free_camera.shake(
                intensity=20.0,
                duration=0.35,
            )

        # ------------------------------------------------------
        # Scene update
        #
        # This updates FreeCamera2D automatically because it is
        # part of the scene node tree.
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
        # Demo grid
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
    FreeCameraExample().run()