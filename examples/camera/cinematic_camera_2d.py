from __future__ import annotations

from nexora import Game
from nexora.nodes import (
    CinematicCamera2D,
    Node,
)
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class CinematicCameraExample(Game):
    """
    Nexora CinematicCamera2D example.

    Controls
    --------
    SPACE
        Start / restart cinematic sequence

    P
        Pause / resume cinematic

    L
        Toggle loop

    R
        Reset camera and effects

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - CinematicCamera2D Example",
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

        self.camera_node: CinematicCamera2D | None = None

        # ======================================================
        # Cinematic targets
        # ======================================================

        self.target_a: Node | None = None
        self.target_b: Node | None = None
        self.target_c: Node | None = None

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
            "cinematic_start",
            "SPACE",
        )

        self.input.bind(
            "cinematic_pause",
            "P",
        )

        self.input.bind(
            "cinematic_loop",
            "L",
        )

        self.input.bind(
            "camera_reset",
            "R",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "CinematicCameraExample"
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
        # World
        # ------------------------------------------------------

        self._create_world_objects()

        # ------------------------------------------------------
        # Cinematic targets
        # ------------------------------------------------------

        self.target_a = Node(
            "TargetA",
            scene.world,
        )

        self.target_a.transform.x = 600.0
        self.target_a.transform.y = 500.0

        scene.add_node(
            self.target_a
        )

        self.target_b = Node(
            "TargetB",
            scene.world,
        )

        self.target_b.transform.x = 1500.0
        self.target_b.transform.y = 950.0

        scene.add_node(
            self.target_b
        )

        self.target_c = Node(
            "TargetC",
            scene.world,
        )

        self.target_c.transform.x = 2400.0
        self.target_c.transform.y = 1400.0

        scene.add_node(
            self.target_c
        )

        # ------------------------------------------------------
        # Cinematic camera
        # ------------------------------------------------------

        self.camera_node = CinematicCamera2D(
            "CinematicCamera",
            scene.world,
            self.renderer,
        )

        scene.add_node(
            self.camera_node
        )

        # ------------------------------------------------------
        # Bounds
        # ------------------------------------------------------

        self.camera_node.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        # ------------------------------------------------------
        # Zoom limits
        # ------------------------------------------------------

        self.camera_node.camera.min_zoom = 0.5
        self.camera_node.camera.max_zoom = 2.5

        # ------------------------------------------------------
        # Starting state
        # ------------------------------------------------------

        self._reset_camera()

        # ------------------------------------------------------
        # Effect configuration
        # ------------------------------------------------------

        self.camera_node.trauma_strength = 35.0
        self.camera_node.trauma_decay = 1.25
        self.camera_node.trauma_power = 2.0

        # ------------------------------------------------------
        # Callbacks
        # ------------------------------------------------------

        self.camera_node.on_step_finished = (
            self._on_step_finished
        )

        self.camera_node.on_sequence_finished = (
            self._on_sequence_finished
        )

        # ------------------------------------------------------
        # Cinematic
        # ------------------------------------------------------

        self._build_cinematic()

        # ------------------------------------------------------
        # Info
        # ------------------------------------------------------

        print()
        print("=" * 55)
        print(" Nexora CinematicCamera2D Example")
        print("=" * 55)
        print()
        print("SPACE  Start / restart cinematic")
        print("P      Pause / resume")
        print("L      Toggle loop")
        print("R      Reset")
        print("ESC    Exit")
        print()
        print(
            f"Cinematic steps: "
            f"{self.camera_node.sequence_length}"
        )
        print()

    # ==========================================================
    # Demo world
    # ==========================================================

    def _create_world_objects(
        self,
    ) -> None:
        spacing = 220.0

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
                    * 0.12
                )

                self.objects.append(
                    (
                        world_x,
                        world_y,
                        rotation,
                    )
                )

    # ==========================================================
    # Cinematic
    # ==========================================================

    def _build_cinematic(
        self,
    ) -> None:
        camera = self.camera_node

        if (
            camera is None
            or self.target_a is None
            or self.target_b is None
            or self.target_c is None
        ):
            return

        camera.clear_sequence()

        # ------------------------------------------------------
        # Cinematic opening
        # ------------------------------------------------------

        camera.queue_letterbox(
            90.0,
            duration=0.6,
            easing="ease_in_out",
        )

        camera.wait(
            0.25
        )

        # ------------------------------------------------------
        # Move to first target
        # ------------------------------------------------------

        camera.move_to_node(
            self.target_a,
            duration=2.0,
            easing="ease_in_out",
        )

        camera.wait(
            0.6
        )

        # ------------------------------------------------------
        # Slow dramatic zoom
        # ------------------------------------------------------

        camera.zoom_to(
            1.5,
            duration=1.5,
            easing="ease_out",
        )

        camera.wait(
            0.5
        )

        # ------------------------------------------------------
        # Impact
        #
        # Flash + trauma + punch
        # ------------------------------------------------------

        camera.queue_flash(
            color=(
                1.0,
                0.85,
                0.5,
            ),
            alpha=0.85,
            duration=0.15,
        )

        camera.queue_trauma(
            0.65,
            wait=0.35,
        )

        camera.queue_punch(
            30.0,
            -20.0,
            duration=0.2,
        )

        camera.wait(
            0.35
        )

        # ------------------------------------------------------
        # Travel to target B
        # ------------------------------------------------------

        camera.move_zoom_to(
            self.target_b.transform.x,
            self.target_b.transform.y,
            zoom=1.0,
            duration=3.0,
            easing="ease_in_out",
        )

        camera.wait(
            0.75
        )

        # ------------------------------------------------------
        # Scene transition simulation
        # ------------------------------------------------------

        camera.queue_fade_out(
            duration=0.75,
            color=(
                0.0,
                0.0,
                0.0,
            ),
            easing="ease_in_out",
        )

        camera.wait(
            0.25
        )

        # ------------------------------------------------------
        # While black, jump camera to target C.
        #
        # duration=0.0 makes this an immediate move.
        # ------------------------------------------------------

        camera.move_to_node(
            self.target_c,
            duration=0.0,
            easing="linear",
        )

        camera.set_zoom(
            1.25
        )

        # ------------------------------------------------------
        # Reveal target C
        # ------------------------------------------------------

        camera.queue_fade_in(
            duration=0.75,
            easing="ease_in_out",
        )

        camera.wait(
            0.75
        )

        # ------------------------------------------------------
        # Heavy cinematic impact
        # ------------------------------------------------------

        camera.queue_shake(
            intensity=18.0,
            duration=0.4,
        )

        camera.queue_flash(
            color=(
                1.0,
                1.0,
                1.0,
            ),
            alpha=0.65,
            duration=0.12,
        )

        camera.queue_trauma(
            0.85,
            wait=0.5,
        )

        # ------------------------------------------------------
        # Pull back to center
        # ------------------------------------------------------

        camera.transform_to(
            self.world_width * 0.5,
            self.world_height * 0.5,
            zoom=1.0,
            duration=3.0,
            easing="ease_out",
        )

        camera.wait(
            0.75
        )

        # ------------------------------------------------------
        # Cinematic ending
        # ------------------------------------------------------

        camera.queue_clear_letterbox(
            duration=0.6,
            easing="ease_in_out",
        )

    # ==========================================================
    # Reset
    # ==========================================================

    def _reset_camera(
        self,
    ) -> None:
        camera = self.camera_node

        if camera is None:
            return

        camera.stop()

        camera.reset_effects()

        camera.set_position(
            300.0,
            300.0,
        )

        camera.set_zoom(
            1.0
        )

    # ==========================================================
    # Callbacks
    # ==========================================================

    def _on_step_finished(
        self,
        index: int,
    ) -> None:
        camera = self.camera_node

        if camera is None:
            return

        print(
            f"Step {index + 1}/"
            f"{camera.sequence_length} finished"
        )

    def _on_sequence_finished(
        self,
    ) -> None:
        print()
        print(
            "Cinematic sequence finished."
        )
        print()

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
        # Start / restart
        # ------------------------------------------------------

        if self.input.action(
            "cinematic_start"
        ).pressed:
            self._reset_camera()

            camera.restart()

            print()
            print(
                "Cinematic started."
            )

        # ------------------------------------------------------
        # Pause / resume
        # ------------------------------------------------------

        if self.input.action(
            "cinematic_pause"
        ).pressed:
            if camera.playing:
                camera.pause()

                print(
                    "Cinematic paused."
                )

            else:
                camera.resume()

                print(
                    "Cinematic resumed."
                )

        # ------------------------------------------------------
        # Loop
        # ------------------------------------------------------

        if self.input.action(
            "cinematic_loop"
        ).pressed:
            camera.loop = (
                not camera.loop
            )

            print(
                "Loop:",
                camera.loop,
            )

        # ------------------------------------------------------
        # Reset
        # ------------------------------------------------------

        if self.input.action(
            "camera_reset"
        ).pressed:
            self._reset_camera()

            print(
                "Camera reset."
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
        # Target A
        # ------------------------------------------------------

        if self.target_a is not None:
            x, y = (
                self.target_a.world_position
            )

            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=180.0,
                height=180.0,
                rotation=0.0,
            )

        # ------------------------------------------------------
        # Target B
        # ------------------------------------------------------

        if self.target_b is not None:
            x, y = (
                self.target_b.world_position
            )

            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=210.0,
                height=210.0,
                rotation=0.25,
            )

        # ------------------------------------------------------
        # Target C
        # ------------------------------------------------------

        if self.target_c is not None:
            x, y = (
                self.target_c.world_position
            )

            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=250.0,
                height=250.0,
                rotation=-0.25,
            )

        # ------------------------------------------------------
        # Scene
        #
        # This also renders Camera2D effects:
        #
        #   - letterbox
        #   - fade
        #   - flash
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
    CinematicCameraExample().run()