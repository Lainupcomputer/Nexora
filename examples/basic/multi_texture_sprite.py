from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class MultiTextureSpriteExample(Game):
    """
    Nexora multi-texture sprite rendering test.

    Uses two real sprite sheets:

        characters/punk_idle_8x64x128.png
        characters/punk_walk_8x64x128.png

    Submission order:

        idle
        walk
        idle
        walk

    Controls:

        ESC -> Exit
    """

    # ==========================================================
    # ASSETS
    # ==========================================================

    IDLE_ASSET_PATH = (
        "characters/punk_idle_8x64x128.png"
    )

    WALK_ASSET_PATH = (
        "characters/punk_walk_8x64x128.png"
    )

    # ==========================================================
    # SPRITE SHEET
    # ==========================================================

    FRAME_WIDTH = 64
    FRAME_HEIGHT = 128

    COLUMNS = 8
    ROWS = 1

    FRAME_COUNT = 8

    # ==========================================================
    # DISPLAY
    # ==========================================================

    DISPLAY_SCALE = 2.0

    DISPLAY_WIDTH = (
        FRAME_WIDTH
        * DISPLAY_SCALE
    )

    DISPLAY_HEIGHT = (
        FRAME_HEIGHT
        * DISPLAY_SCALE
    )

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
    ) -> None:
        super().__init__(
            project_name="MultiTextureSpriteExample",
            title="Nexora - Multi Texture Sprite Test",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.idle_texture: (
            GPUTexture
            | None
        ) = None

        self.walk_texture: (
            GPUTexture
            | None
        ) = None

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        print("=" * 60)
        print(
            " Nexora Multi Texture Sprite Test"
        )
        print("=" * 60)
        print()

        # ======================================================
        # INPUT
        # ======================================================

        self.input.bind(
            "exit",
            "ESCAPE",
        )

        # ======================================================
        # LOAD IDLE
        # ======================================================

        idle_image = (
            self.assets.load_texture(
                self.IDLE_ASSET_PATH,
            )
        )

        print(
            f"Idle sheet: "
            f"{idle_image.width}x"
            f"{idle_image.height}"
        )

        # ======================================================
        # LOAD WALK
        # ======================================================

        walk_image = (
            self.assets.load_texture(
                self.WALK_ASSET_PATH,
            )
        )

        print(
            f"Walk sheet: "
            f"{walk_image.width}x"
            f"{walk_image.height}"
        )

        print()

        # ======================================================
        # VALIDATE
        # ======================================================

        expected_width = (
            self.FRAME_WIDTH
            * self.COLUMNS
        )

        expected_height = (
            self.FRAME_HEIGHT
            * self.ROWS
        )

        if (
            idle_image.width
            != expected_width
        ):
            raise ValueError(
                "Idle sprite sheet width is invalid: "
                f"{idle_image.width} != "
                f"{expected_width}"
            )

        if (
            idle_image.height
            != expected_height
        ):
            raise ValueError(
                "Idle sprite sheet height is invalid: "
                f"{idle_image.height} != "
                f"{expected_height}"
            )

        if (
            walk_image.width
            != expected_width
        ):
            raise ValueError(
                "Walk sprite sheet width is invalid: "
                f"{walk_image.width} != "
                f"{expected_width}"
            )

        if (
            walk_image.height
            != expected_height
        ):
            raise ValueError(
                "Walk sprite sheet height is invalid: "
                f"{walk_image.height} != "
                f"{expected_height}"
            )

        print(
            f"Frame size: "
            f"{self.FRAME_WIDTH}x"
            f"{self.FRAME_HEIGHT}"
        )

        print(
            f"Display size: "
            f"{int(self.DISPLAY_WIDTH)}x"
            f"{int(self.DISPLAY_HEIGHT)}"
        )

        print()

        # ======================================================
        # GPU TEXTURES
        # ======================================================

        device = (
            self.engine.gpu_context.device
        )

        self.idle_texture = (
            GPUTexture(
                device,
                idle_image.width,
                idle_image.height,
                data=idle_image.pixels,
                bytes_per_pixel=(
                    idle_image.bytes_per_pixel
                ),
            )
        )

        self.walk_texture = (
            GPUTexture(
                device,
                walk_image.width,
                walk_image.height,
                data=walk_image.pixels,
                bytes_per_pixel=(
                    walk_image.bytes_per_pixel
                ),
            )
        )

        print(
            "GPU textures created."
        )

        print()

        print(
            "Submission order:"
        )

        print(
            "  1 -> idle texture"
        )

        print(
            "  2 -> walk texture"
        )

        print(
            "  3 -> idle texture"
        )

        print(
            "  4 -> walk texture"
        )

        print()

        print(
            "Expected:"
        )

        print(
            "  Four punk sprites"
        )

        print(
            "  Idle -> Walk -> Idle -> Walk"
        )

        print()

        print(
            "Controls:"
        )

        print(
            "  ESC -> Exit"
        )

        print()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if self.input.action(
            "exit",
        ).pressed:
            self.stop()

            return

        super().update(
            delta_time,
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        if (
            self.idle_texture is None
            or self.walk_texture is None
        ):
            return

        # ======================================================
        # UVs
        # ======================================================

        frame_width_uv = (
            1.0
            / float(
                self.COLUMNS
            )
        )

        # First frame of each sheet.
        idle_uv = (
            0.0,
            0.0,
            frame_width_uv,
            1.0,
        )

        # Use another frame from walk sheet so the
        # two textures are easier to distinguish.
        walk_frame_index = 3

        walk_uv = (
            frame_width_uv
            * walk_frame_index,
            0.0,
            frame_width_uv,
            1.0,
        )

        # ======================================================
        # SPRITE 1
        #
        # IDLE
        # ======================================================

        self.renderer.sprite(
            self.idle_texture,
            -360.0,
            0.0,
            width=(
                self.DISPLAY_WIDTH
            ),
            height=(
                self.DISPLAY_HEIGHT
            ),
            rotation=0.0,
            origin=(
                0.5,
                0.5,
            ),
            alpha=1.0,
            flip_x=False,
            flip_y=False,
            uv=idle_uv,
        )

        # ======================================================
        # SPRITE 2
        #
        # WALK
        # ======================================================

        self.renderer.sprite(
            self.walk_texture,
            -120.0,
            0.0,
            width=(
                self.DISPLAY_WIDTH
            ),
            height=(
                self.DISPLAY_HEIGHT
            ),
            rotation=0.0,
            origin=(
                0.5,
                0.5,
            ),
            alpha=1.0,
            flip_x=False,
            flip_y=False,
            uv=walk_uv,
        )

        # ======================================================
        # SPRITE 3
        #
        # IDLE AGAIN
        # ======================================================

        self.renderer.sprite(
            self.idle_texture,
            120.0,
            0.0,
            width=(
                self.DISPLAY_WIDTH
            ),
            height=(
                self.DISPLAY_HEIGHT
            ),
            rotation=0.0,
            origin=(
                0.5,
                0.5,
            ),
            alpha=1.0,
            flip_x=False,
            flip_y=False,
            uv=idle_uv,
        )

        # ======================================================
        # SPRITE 4
        #
        # WALK AGAIN
        # ======================================================

        self.renderer.sprite(
            self.walk_texture,
            360.0,
            0.0,
            width=(
                self.DISPLAY_WIDTH
            ),
            height=(
                self.DISPLAY_HEIGHT
            ),
            rotation=0.0,
            origin=(
                0.5,
                0.5,
            ),
            alpha=1.0,
            flip_x=False,
            flip_y=False,
            uv=walk_uv,
        )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        print()

        print(
            "Destroying multi-texture example..."
        )

        if (
            self.idle_texture
            is not None
        ):
            self.idle_texture.destroy()

            self.idle_texture = None

        if (
            self.walk_texture
            is not None
        ):
            self.walk_texture.destroy()

            self.walk_texture = None

        print(
            "Done."
        )

        super().shutdown()


if __name__ == "__main__":
    MultiTextureSpriteExample().run()