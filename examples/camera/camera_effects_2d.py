from __future__ import annotations

from nexora import Game
from nexora.nodes import FixedCamera2D
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class CameraEffectsExample(Game):
    """
    Demonstrates the built-in Camera2D effects.

    Controls
    --------
    1
        Normal camera shake

    2
        Add trauma

    3
        Camera punch / recoil

    4
        White flash

    5
        Red damage flash

    6
        Fade out

    7
        Fade in

    8
        Enable letterbox

    9
        Disable letterbox

    0
        Combined impact effect

    R
        Reset all camera effects

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Camera Effects Example",
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
            "normal_shake",
            "1",
        )

        self.input.bind(
            "trauma",
            "2",
        )

        self.input.bind(
            "punch",
            "3",
        )

        self.input.bind(
            "white_flash",
            "4",
        )

        self.input.bind(
            "red_flash",
            "5",
        )

        self.input.bind(
            "fade_out",
            "6",
        )

        self.input.bind(
            "fade_in",
            "7",
        )

        self.input.bind(
            "letterbox_on",
            "8",
        )

        self.input.bind(
            "letterbox_off",
            "9",
        )

        self.input.bind(
            "combined_effect",
            "0",
        )

        self.input.bind(
            "reset",
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
            "CameraEffectsExample"
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
        # Camera
        # ------------------------------------------------------

        self.camera_node = FixedCamera2D(
            "EffectsCamera",
            scene.world,
            self.renderer,
            x=self.world_width * 0.5,
            y=self.world_height * 0.5,
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
        # Trauma configuration
        # ------------------------------------------------------

        self.camera_node.trauma_strength = 35.0

        self.camera_node.trauma_decay = 1.25

        self.camera_node.trauma_power = 2.0

        # ------------------------------------------------------
        # Information
        # ------------------------------------------------------

        print()
        print("=" * 50)
        print(" Nexora Camera Effects Example")
        print("=" * 50)
        print()
        print("1   Normal shake")
        print("2   Trauma shake")
        print("3   Camera punch")
        print("4   White flash")
        print("5   Red damage flash")
        print("6   Fade out")
        print("7   Fade in")
        print("8   Letterbox on")
        print("9   Letterbox off")
        print("0   Combined impact effect")
        print("R   Reset all effects")
        print("ESC Exit")
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
    # Normal shake
    # ==========================================================

    def _normal_shake(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.shake(
            intensity=25.0,
            duration=0.5,
        )

        print(
            "Normal shake"
        )

    # ==========================================================
    # Trauma
    # ==========================================================

    def _trauma(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.add_trauma(
            0.5
        )

        print(
            "Trauma +0.5"
        )

    # ==========================================================
    # Punch
    # ==========================================================

    def _punch(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.punch(
            35.0,
            -25.0,
            duration=0.22,
        )

        print(
            "Camera punch"
        )

    # ==========================================================
    # White flash
    # ==========================================================

    def _white_flash(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.flash(
            color=(
                1.0,
                1.0,
                1.0,
            ),
            alpha=0.9,
            duration=0.18,
        )

        print(
            "White flash"
        )

    # ==========================================================
    # Red damage flash
    # ==========================================================

    def _red_flash(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.flash(
            color=(
                1.0,
                0.05,
                0.05,
            ),
            alpha=0.7,
            duration=0.3,
        )

        print(
            "Red damage flash"
        )

    # ==========================================================
    # Fade
    # ==========================================================

    def _fade_out(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.fade_out(
            duration=1.0,
            color=(
                0.0,
                0.0,
                0.0,
            ),
            easing="ease_in_out",
            on_complete=self._fade_out_finished,
        )

        print(
            "Fade out started"
        )

    def _fade_out_finished(
        self,
    ) -> None:
        print(
            "Fade out finished"
        )

    def _fade_in(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.fade_in(
            duration=1.0,
            easing="ease_in_out",
            on_complete=self._fade_in_finished,
        )

        print(
            "Fade in started"
        )

    def _fade_in_finished(
        self,
    ) -> None:
        print(
            "Fade in finished"
        )

    # ==========================================================
    # Letterbox
    # ==========================================================

    def _letterbox_on(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.letterbox(
            90.0,
            duration=0.5,
            color=(
                0.0,
                0.0,
                0.0,
            ),
            easing="ease_in_out",
        )

        print(
            "Letterbox enabled"
        )

    def _letterbox_off(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        self.camera_node.clear_letterbox(
            duration=0.5,
            easing="ease_in_out",
        )

        print(
            "Letterbox disabled"
        )

    # ==========================================================
    # Combined effect
    # ==========================================================

    def _combined_effect(
        self,
    ) -> None:
        """
        Simulate a large impact or explosion.

        Combines:

            - trauma
            - camera punch
            - flash
            - traditional shake
        """

        if self.camera_node is None:
            return

        camera = self.camera_node

        # ------------------------------------------------------
        # Traditional shake
        # ------------------------------------------------------

        camera.shake(
            intensity=10.0,
            duration=0.3,
        )

        # ------------------------------------------------------
        # Trauma
        # ------------------------------------------------------

        camera.add_trauma(
            0.85
        )

        # ------------------------------------------------------
        # Directional punch
        # ------------------------------------------------------

        camera.punch(
            40.0,
            -30.0,
            duration=0.25,
        )

        # ------------------------------------------------------
        # Explosion flash
        # ------------------------------------------------------

        camera.flash(
            color=(
                1.0,
                0.85,
                0.55,
            ),
            alpha=0.9,
            duration=0.22,
        )

        print(
            "Combined impact effect"
        )

    # ==========================================================
    # Reset
    # ==========================================================

    def _reset_effects(
        self,
    ) -> None:
        if self.camera_node is None:
            return

        camera = self.camera_node

        # ------------------------------------------------------
        # Public Camera2D reset API
        # ------------------------------------------------------

        camera.reset_effects()

        # ------------------------------------------------------
        # Restore camera itself
        # ------------------------------------------------------

        camera.reset_position()

        camera.set_zoom(
            1.0
        )

        print(
            "All camera effects reset"
        )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if self.camera_node is None:
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
        # Effects
        # ------------------------------------------------------

        if self.input.action(
            "normal_shake"
        ).pressed:
            self._normal_shake()

        if self.input.action(
            "trauma"
        ).pressed:
            self._trauma()

        if self.input.action(
            "punch"
        ).pressed:
            self._punch()

        if self.input.action(
            "white_flash"
        ).pressed:
            self._white_flash()

        if self.input.action(
            "red_flash"
        ).pressed:
            self._red_flash()

        if self.input.action(
            "fade_out"
        ).pressed:
            self._fade_out()

        if self.input.action(
            "fade_in"
        ).pressed:
            self._fade_in()

        if self.input.action(
            "letterbox_on"
        ).pressed:
            self._letterbox_on()

        if self.input.action(
            "letterbox_off"
        ).pressed:
            self._letterbox_off()

        if self.input.action(
            "combined_effect"
        ).pressed:
            self._combined_effect()

        # ------------------------------------------------------
        # Reset
        # ------------------------------------------------------

        if self.input.action(
            "reset"
        ).pressed:
            self._reset_effects()

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
        # Center object
        #
        # The large center object makes movement effects much
        # easier to see.
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            self.world_width * 0.5,
            self.world_height * 0.5,
            width=280.0,
            height=280.0,
            rotation=0.0,
        )

        # ------------------------------------------------------
        # Scene
        #
        # Camera2D renders:
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
    CameraEffectsExample().run()