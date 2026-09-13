from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class PostProcessingExample(Game):
    """
    Nexora post-processing showcase.

    Controls
    --------
    1
        Toggle grayscale

    2
        Toggle vignette

    3
        Toggle chromatic aberration

    4
        Toggle film grain

    5
        Toggle scanlines

    6
        Toggle pixelation

    7
        Toggle distortion

    8
        Toggle cold tint

    9
        Toggle low-health effect

    0
        Reset all effects

    F1
        Cinematic preset

    F2
        Horror preset

    F3
        Retro preset

    F4
        Damaged preset

    P
        Enable / disable post-processing

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Post Processing Showcase",
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

        # ======================================================
        # Toggle state
        # ======================================================

        self.grayscale_enabled = False
        self.vignette_enabled = False
        self.chromatic_enabled = False
        self.grain_enabled = False
        self.scanlines_enabled = False
        self.pixelation_enabled = False
        self.distortion_enabled = False
        self.tint_enabled = False
        self.low_health_enabled = False

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
            "grayscale",
            "1",
        )

        self.input.bind(
            "vignette",
            "2",
        )

        self.input.bind(
            "chromatic",
            "3",
        )

        self.input.bind(
            "grain",
            "4",
        )

        self.input.bind(
            "scanlines",
            "5",
        )

        self.input.bind(
            "pixelation",
            "6",
        )

        self.input.bind(
            "distortion",
            "7",
        )

        self.input.bind(
            "tint",
            "8",
        )

        self.input.bind(
            "low_health",
            "9",
        )

        self.input.bind(
            "reset",
            "0",
        )

        self.input.bind(
            "preset_cinematic",
            "F1",
        )

        self.input.bind(
            "preset_horror",
            "F2",
        )

        self.input.bind(
            "preset_retro",
            "F3",
        )

        self.input.bind(
            "preset_damaged",
            "F4",
        )

        self.input.bind(
            "toggle_post",
            "P",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "PostProcessingExample"
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

        self.renderer.camera.set_position(
            self.world_width * 0.5,
            self.world_height * 0.5,
        )

        self.renderer.camera.set_zoom(
            1.0
        )

        # ------------------------------------------------------
        # Post processing
        # ------------------------------------------------------

        post = (
            self.renderer.post_processing
        )

        post.enable()

        post.effects.reset()

        # ------------------------------------------------------
        # Information
        # ------------------------------------------------------

        self._print_controls()

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
    # Console info
    # ==========================================================

    def _print_controls(
        self,
    ) -> None:
        print()
        print("=" * 60)
        print(" Nexora Post Processing Showcase")
        print("=" * 60)
        print()
        print("1    Grayscale")
        print("2    Vignette")
        print("3    Chromatic aberration")
        print("4    Film grain")
        print("5    Scanlines")
        print("6    Pixelation")
        print("7    Distortion")
        print("8    Cold tint")
        print("9    Low health")
        print("0    Reset")
        print()
        print("F1   Cinematic preset")
        print("F2   Horror preset")
        print("F3   Retro preset")
        print("F4   Damaged preset")
        print()
        print("P    Post-processing on/off")
        print("ESC  Exit")
        print()

    # ==========================================================
    # Toggle helpers
    # ==========================================================

    def _toggle_grayscale(
        self,
    ) -> None:
        post = (
            self.renderer.post_processing
        )

        effects = post.effects

        self.grayscale_enabled = (
            not self.grayscale_enabled
        )

        if self.grayscale_enabled:
            effects.grayscale(
                1.0
            )
        else:
            effects.disable_grayscale()

    def _toggle_vignette(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.vignette_enabled = (
            not self.vignette_enabled
        )

        if self.vignette_enabled:
            effects.vignette(
                0.7
            )
        else:
            effects.disable_vignette()

    def _toggle_chromatic(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.chromatic_enabled = (
            not self.chromatic_enabled
        )

        if self.chromatic_enabled:
            effects.chromatic_aberration(
                6.0
            )
        else:
            effects.disable_chromatic_aberration()

    def _toggle_grain(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.grain_enabled = (
            not self.grain_enabled
        )

        if self.grain_enabled:
            effects.film_grain(
                0.65
            )
        else:
            effects.disable_film_grain()

    def _toggle_scanlines(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.scanlines_enabled = (
            not self.scanlines_enabled
        )

        if self.scanlines_enabled:
            effects.scanlines(
                0.7,
                frequency=1.0,
            )
        else:
            effects.disable_scanlines()

    def _toggle_pixelation(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.pixelation_enabled = (
            not self.pixelation_enabled
        )

        if self.pixelation_enabled:
            effects.pixelation(
                10.0
            )
        else:
            effects.disable_pixelation()

    def _toggle_distortion(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.distortion_enabled = (
            not self.distortion_enabled
        )

        if self.distortion_enabled:
            effects.distortion(
                0.8,
                speed=2.0,
            )
        else:
            effects.disable_distortion()

    def _toggle_tint(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.tint_enabled = (
            not self.tint_enabled
        )

        if self.tint_enabled:
            effects.cold_tint(
                1.0
            )
        else:
            effects.clear_tint()

    def _toggle_low_health(
        self,
    ) -> None:
        effects = (
            self.renderer
            .post_processing
            .effects
        )

        self.low_health_enabled = (
            not self.low_health_enabled
        )

        if self.low_health_enabled:
            effects.low_health(
                0.15,
                strength=1.0,
            )
        else:
            effects.disable_low_health()

    # ==========================================================
    # Toggle state reset
    # ==========================================================

    def _reset_toggle_state(
        self,
    ) -> None:
        self.grayscale_enabled = False
        self.vignette_enabled = False
        self.chromatic_enabled = False
        self.grain_enabled = False
        self.scanlines_enabled = False
        self.pixelation_enabled = False
        self.distortion_enabled = False
        self.tint_enabled = False
        self.low_health_enabled = False

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        post = (
            self.renderer.post_processing
        )

        effects = post.effects

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Post processing on/off
        # ------------------------------------------------------

        if self.input.action(
            "toggle_post"
        ).pressed:
            if post.enabled:
                post.disable()

                print(
                    "Post-processing OFF"
                )
            else:
                post.enable()

                print(
                    "Post-processing ON"
                )

        # ------------------------------------------------------
        # Individual effects
        # ------------------------------------------------------

        if self.input.action(
            "grayscale"
        ).pressed:
            self._toggle_grayscale()

        if self.input.action(
            "vignette"
        ).pressed:
            self._toggle_vignette()

        if self.input.action(
            "chromatic"
        ).pressed:
            self._toggle_chromatic()

        if self.input.action(
            "grain"
        ).pressed:
            self._toggle_grain()

        if self.input.action(
            "scanlines"
        ).pressed:
            self._toggle_scanlines()

        if self.input.action(
            "pixelation"
        ).pressed:
            self._toggle_pixelation()

        if self.input.action(
            "distortion"
        ).pressed:
            self._toggle_distortion()

        if self.input.action(
            "tint"
        ).pressed:
            self._toggle_tint()

        if self.input.action(
            "low_health"
        ).pressed:
            self._toggle_low_health()

        # ------------------------------------------------------
        # Reset
        # ------------------------------------------------------

        if self.input.action(
            "reset"
        ).pressed:
            effects.reset()

            self._reset_toggle_state()

            print(
                "Post-processing reset"
            )

        # ------------------------------------------------------
        # Cinematic preset
        # ------------------------------------------------------

        if self.input.action(
            "preset_cinematic"
        ).pressed:
            effects.reset()

            effects.cinematic()

            self._reset_toggle_state()

            print(
                "Preset: cinematic"
            )

        # ------------------------------------------------------
        # Horror preset
        # ------------------------------------------------------

        if self.input.action(
            "preset_horror"
        ).pressed:
            effects.reset()

            effects.horror()

            self._reset_toggle_state()

            print(
                "Preset: horror"
            )

        # ------------------------------------------------------
        # Retro preset
        # ------------------------------------------------------

        if self.input.action(
            "preset_retro"
        ).pressed:
            effects.reset()

            effects.retro()

            self._reset_toggle_state()

            print(
                "Preset: retro"
            )

        # ------------------------------------------------------
        # Damaged preset
        # ------------------------------------------------------

        if self.input.action(
            "preset_damaged"
        ).pressed:
            effects.reset()

            effects.damaged()

            self._reset_toggle_state()

            print(
                "Preset: damaged"
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

        center_x = (
            self.world_width
            * 0.5
        )

        center_y = (
            self.world_height
            * 0.5
        )

        # ------------------------------------------------------
        # Sprite grid
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
        # Center sprite
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            center_x,
            center_y,
            width=320.0,
            height=320.0,
            rotation=0.0,
        )

        # ------------------------------------------------------
        # Side sprites
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            center_x - 350.0,
            center_y - 100.0,
            width=220.0,
            height=220.0,
            rotation=-0.25,
        )

        self.renderer.sprite(
            self.texture,
            center_x + 350.0,
            center_y - 100.0,
            width=220.0,
            height=220.0,
            rotation=0.25,
        )

        # ------------------------------------------------------
        # Color reference bars
        # ------------------------------------------------------

        self.renderer.rect(
            center_x - 330.0,
            center_y + 280.0,
            180.0,
            110.0,
            color=(
                1.0,
                0.1,
                0.1,
                1.0,
            ),
        )

        self.renderer.rect(
            center_x - 110.0,
            center_y + 280.0,
            180.0,
            110.0,
            color=(
                0.1,
                1.0,
                0.1,
                1.0,
            ),
        )

        self.renderer.rect(
            center_x + 110.0,
            center_y + 280.0,
            180.0,
            110.0,
            color=(
                0.1,
                0.25,
                1.0,
                1.0,
            ),
        )

        self.renderer.rect(
            center_x + 330.0,
            center_y + 280.0,
            180.0,
            110.0,
            color=(
                1.0,
                0.85,
                0.1,
                1.0,
            ),
        )

        # ------------------------------------------------------
        # White reference
        # ------------------------------------------------------

        self.renderer.rect(
            center_x,
            center_y + 430.0,
            400.0,
            55.0,
            color=(
                1.0,
                1.0,
                1.0,
                1.0,
            ),
        )

        # ------------------------------------------------------
        # Black reference
        # ------------------------------------------------------

        self.renderer.rect(
            center_x,
            center_y + 500.0,
            400.0,
            55.0,
            color=(
                0.05,
                0.05,
                0.05,
                1.0,
            ),
        )

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
    PostProcessingExample().run()