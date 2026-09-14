from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class RenderMemoryTest(Game):
    """
    Minimal Nexora render-memory diagnostic.

    Controls
    --------
    1
        Empty render

    2
        One sprite

    3
        100 sprites

    4
        500 sprites

    ESC
        Exit

    Purpose
    -------
    This example isolates memory growth caused by the render path.

    Mode 1:
        begin_frame / end_frame only

    Mode 2:
        one sprite upload per frame

    Mode 3:
        moderate sprite batch

    Mode 4:
        larger sprite batch
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Render Memory Test",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.texture: GPUTexture | None = None

        self.sprite_width = 64.0
        self.sprite_height = 64.0

        self.mode = 1

        self.positions_100: list[
            tuple[
                float,
                float,
            ]
        ] = []

        self.positions_500: list[
            tuple[
                float,
                float,
            ]
        ] = []

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input.bind(
            "mode_empty",
            "1",
        )

        self.input.bind(
            "mode_one",
            "2",
        )

        self.input.bind(
            "mode_100",
            "3",
        )

        self.input.bind(
            "mode_500",
            "4",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

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
        # 100 sprite positions
        # ------------------------------------------------------

        spacing_x = 100.0
        spacing_y = 90.0

        for row in range(
            10
        ):
            for column in range(
                10
            ):
                x = (
                    -450.0
                    + column
                    * spacing_x
                )

                y = (
                    -300.0
                    + row
                    * spacing_y
                )

                self.positions_100.append(
                    (
                        x,
                        y,
                    )
                )

        # ------------------------------------------------------
        # 500 sprite positions
        # ------------------------------------------------------

        spacing_x = 52.0
        spacing_y = 52.0

        columns = 25
        rows = 20

        for row in range(
            rows
        ):
            for column in range(
                columns
            ):
                x = (
                    -620.0
                    + column
                    * spacing_x
                )

                y = (
                    -500.0
                    + row
                    * spacing_y
                )

                self.positions_500.append(
                    (
                        x,
                        y,
                    )
                )

        # ------------------------------------------------------
        # Info
        # ------------------------------------------------------

        print()
        print("=" * 60)
        print(" Nexora Render Memory Test")
        print("=" * 60)
        print()
        print("1  Empty render")
        print("2  One sprite")
        print("3  100 sprites")
        print("4  500 sprites")
        print("ESC Exit")
        print()
        print(
            "Current mode: EMPTY"
        )
        print()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Mode 1
        # ------------------------------------------------------

        if self.input.action(
            "mode_empty"
        ).pressed:
            self.mode = 1

            print()
            print(
                "Mode: EMPTY RENDER"
            )
            print()

        # ------------------------------------------------------
        # Mode 2
        # ------------------------------------------------------

        if self.input.action(
            "mode_one"
        ).pressed:
            self.mode = 2

            print()
            print(
                "Mode: ONE SPRITE"
            )
            print()

        # ------------------------------------------------------
        # Mode 3
        # ------------------------------------------------------

        if self.input.action(
            "mode_100"
        ).pressed:
            self.mode = 3

            print()
            print(
                "Mode: 100 SPRITES"
            )
            print()

        # ------------------------------------------------------
        # Mode 4
        # ------------------------------------------------------

        if self.input.action(
            "mode_500"
        ).pressed:
            self.mode = 4

            print()
            print(
                "Mode: 500 SPRITES"
            )
            print()

        super().update(
            delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        if self.texture is None:
            return

        # ======================================================
        # MODE 1
        #
        # Empty frame.
        #
        # Only Renderer.begin_frame() / end_frame() are executed
        # by the normal GameLoop.
        # ======================================================

        if self.mode == 1:
            return

        # ======================================================
        # MODE 2
        #
        # Exactly one sprite.
        # ======================================================

        if self.mode == 2:
            self.renderer.sprite(
                self.texture,
                0.0,
                0.0,
                width=self.sprite_width,
                height=self.sprite_height,
            )

            return

        # ======================================================
        # MODE 3
        #
        # 100 sprites.
        # ======================================================

        if self.mode == 3:
            for (
                x,
                y,
            ) in self.positions_100:
                self.renderer.sprite(
                    self.texture,
                    x,
                    y,
                    width=self.sprite_width,
                    height=self.sprite_height,
                )

            return

        # ======================================================
        # MODE 4
        #
        # 500 sprites.
        # ======================================================

        if self.mode == 4:
            for (
                x,
                y,
            ) in self.positions_500:
                self.renderer.sprite(
                    self.texture,
                    x,
                    y,
                    width=self.sprite_width,
                    height=self.sprite_height,
                )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        if self.texture is not None:
            self.texture.destroy()

            self.texture = None

        super().shutdown()


if __name__ == "__main__":
    RenderMemoryTest().run()