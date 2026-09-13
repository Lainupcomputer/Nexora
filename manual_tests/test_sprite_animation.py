from __future__ import annotations

import sdl3

from nexora.animation import AnimationClip
from nexora.core.game import Game
from nexora.nodes import AnimatedSprite
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class SpriteAnimationTest(Game):
    """
    Manual integration test for AnimatedSprite.

    Tests the complete automatic engine path:

        Scene.update()
            -> Node.update_tree()
            -> AnimatedSprite.update()
            -> Animator.update()

        Game.render()
            -> Scene.render_nodes()
            -> Node.render_tree()
            -> AnimatedSprite.render()
            -> Renderer.sprite()

    The animated sprite itself is NOT updated or rendered manually.
    """

    FRAME_WIDTH = 96
    FRAME_HEIGHT = 96

    COLUMNS = 4
    ROWS = 1

    def __init__(
        self,
    ) -> None:
        super().__init__()

        # ======================================================
        # Scene
        # ======================================================

        self.scene = Scene(
            "SpriteAnimationTest"
        )

        # ======================================================
        # Runtime resources
        # ======================================================

        self.texture: GPUTexture | None = None

        self.sprite: AnimatedSprite | None = None

        self._last_frame_index = -1

    # ==============================================================
    # Initialize
    # ==============================================================

    def initialize(
        self,
    ) -> None:
        print("=" * 60)
        print(" Nexora AnimatedSprite Test")
        print("=" * 60)
        print()

        # ----------------------------------------------------------
        # Sprite-sheet dimensions
        # ----------------------------------------------------------

        texture_width = (
            self.FRAME_WIDTH
            * self.COLUMNS
        )

        texture_height = (
            self.FRAME_HEIGHT
            * self.ROWS
        )

        # ----------------------------------------------------------
        # Generate test sprite sheet
        # ----------------------------------------------------------

        pixels = (
            self._create_test_sprite_sheet()
        )

        # ----------------------------------------------------------
        # Create GPU texture
        # ----------------------------------------------------------

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            texture_width,
            texture_height,
            data=pixels,
            bytes_per_pixel=4,
        )

        # ----------------------------------------------------------
        # Create AnimatedSprite through Scene
        # ----------------------------------------------------------

        node = self.scene.create_node(
            "TestSprite",
            node_type=AnimatedSprite,
        )

        assert isinstance(
            node,
            AnimatedSprite,
        )

        self.sprite = node

        # ----------------------------------------------------------
        # Sprite configuration
        # ----------------------------------------------------------

        self.sprite.texture = (
            self.texture
        )

        self.sprite.width = 256.0
        self.sprite.height = 256.0

        self.sprite.origin = (
            0.5,
            0.5,
        )

        self.sprite.transform.x = 0.0
        self.sprite.transform.y = 0.0

        # ----------------------------------------------------------
        # Animation
        # ----------------------------------------------------------

        clip = AnimationClip.from_row(
            "test_animation",
            row=0,
            start_column=0,
            frame_count=self.COLUMNS,
            columns=self.COLUMNS,
            rows=self.ROWS,
            fps=4.0,
            loop=True,
        )

        self.sprite.add_animation(
            clip
        )

        # Install callback before play(), so frame 0 is reported too.
        self.sprite.animator.on_frame_changed = (
            self._on_frame_changed
        )

        self.sprite.play(
            "test_animation"
        )

        # ----------------------------------------------------------
        # Information
        # ----------------------------------------------------------

        print("Generated sprite sheet:")

        print(
            f"  Size: "
            f"{texture_width} x "
            f"{texture_height}"
        )

        print(
            f"  Frame size: "
            f"{self.FRAME_WIDTH} x "
            f"{self.FRAME_HEIGHT}"
        )

        print(
            f"  Frames: "
            f"{clip.frame_count}"
        )

        print(
            "  FPS: 4"
        )

        print()

        print("Expected:")

        print(
            "  A large animated square should "
            "appear in the center."
        )

        print(
            "  It should cycle through four "
            "different frames."
        )

        print()

        print("Controls:")

        print(
            "  SPACE -> pause / resume"
        )

        print(
            "  R     -> restart animation"
        )

        print(
            "  1     -> speed 0.5x"
        )

        print(
            "  2     -> speed 1.0x"
        )

        print(
            "  3     -> speed 2.0x"
        )

        print(
            "  F     -> flip horizontally"
        )

        print(
            "  V     -> flip vertically"
        )

        print(
            "  ESC   -> close"
        )

        print()

        print(
            "The AnimatedSprite is updated "
            "and rendered automatically."
        )

        print()

    # ==============================================================
    # Sprite sheet generation
    # ==============================================================

    def _create_test_sprite_sheet(
        self,
    ) -> bytes:
        """
        Generate a horizontal four-frame RGBA sprite sheet.

        Every frame has a different color and a different number
        of vertical white markers so UV errors are immediately
        visible.
        """

        width = (
            self.FRAME_WIDTH
            * self.COLUMNS
        )

        height = (
            self.FRAME_HEIGHT
            * self.ROWS
        )

        pixels = bytearray(
            width
            * height
            * 4
        )

        # ----------------------------------------------------------
        # Frame colors
        # ----------------------------------------------------------

        frame_colors = (
            (
                230,
                70,
                70,
                255,
            ),
            (
                70,
                210,
                90,
                255,
            ),
            (
                70,
                120,
                230,
                255,
            ),
            (
                230,
                200,
                70,
                255,
            ),
        )

        # ----------------------------------------------------------
        # Draw frames
        # ----------------------------------------------------------

        for frame_index in range(
            self.COLUMNS
        ):
            (
                base_r,
                base_g,
                base_b,
                base_a,
            ) = frame_colors[
                frame_index
            ]

            frame_start_x = (
                frame_index
                * self.FRAME_WIDTH
            )

            for y in range(
                self.FRAME_HEIGHT
            ):
                for local_x in range(
                    self.FRAME_WIDTH
                ):
                    x = (
                        frame_start_x
                        + local_x
                    )

                    r = base_r
                    g = base_g
                    b = base_b
                    a = base_a

                    # ----------------------------------------------
                    # White border
                    # ----------------------------------------------

                    border = (
                        local_x < 5
                        or local_x
                        >= self.FRAME_WIDTH - 5
                        or y < 5
                        or y
                        >= self.FRAME_HEIGHT - 5
                    )

                    if border:
                        r = 255
                        g = 255
                        b = 255

                    # ----------------------------------------------
                    # Frame markers
                    #
                    # Frame 0 -> 1 stripe
                    # Frame 1 -> 2 stripes
                    # Frame 2 -> 3 stripes
                    # Frame 3 -> 4 stripes
                    # ----------------------------------------------

                    marker_count = (
                        frame_index
                        + 1
                    )

                    for marker in range(
                        marker_count
                    ):
                        marker_x = (
                            12
                            + marker
                            * 18
                        )

                        if (
                            marker_x
                            <= local_x
                            < marker_x + 8
                            and
                            24
                            <= y
                            < self.FRAME_HEIGHT - 24
                        ):
                            r = 255
                            g = 255
                            b = 255

                    # ----------------------------------------------
                    # Write RGBA
                    # ----------------------------------------------

                    offset = (
                        (
                            y
                            * width
                            + x
                        )
                        * 4
                    )

                    pixels[
                        offset
                    ] = r

                    pixels[
                        offset + 1
                    ] = g

                    pixels[
                        offset + 2
                    ] = b

                    pixels[
                        offset + 3
                    ] = a

        return bytes(
            pixels
        )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ----------------------------------------------------------
        # Normal Game update
        #
        # This should eventually call:
        #
        # Scene.update()
        #   -> root.update_tree()
        #   -> AnimatedSprite.update()
        #   -> Animator.update()
        #
        # No manual animator.update() here.
        # ----------------------------------------------------------

        super().update(
            delta_time
        )

        if self.sprite is None:
            return

        frame = (
            self.sprite.current_frame
        )

        if frame is None:
            return

        if (
            frame.index
            != self._last_frame_index
        ):
            self._last_frame_index = (
                frame.index
            )

            print(
                f"[Animation] "
                f"frame={frame.index} "
                f"uv={frame.uv}"
            )

    # ==============================================================
    # Input
    # ==============================================================

    def handle_event(
        self,
        event,
    ) -> None:
        if (
            event.type
            != sdl3.SDL_EVENT_KEY_DOWN
        ):
            return

        # Ignore key repeat where supported.
        if getattr(
            event.key,
            "repeat",
            False,
        ):
            return

        key = (
            event.key.key
        )

        # ----------------------------------------------------------
        # Exit
        # ----------------------------------------------------------

        if key == sdl3.SDLK_ESCAPE:
            self.stop()
            return

        if self.sprite is None:
            return

        # ----------------------------------------------------------
        # Pause / Resume
        # ----------------------------------------------------------

        if key == sdl3.SDLK_SPACE:
            if self.sprite.playing:
                self.sprite.pause()

                print(
                    "[Animation] paused"
                )

            else:
                self.sprite.resume()

                print(
                    "[Animation] resumed"
                )

            return

        # ----------------------------------------------------------
        # Restart
        # ----------------------------------------------------------

        if key == sdl3.SDLK_R:
            self.sprite.play(
                "test_animation",
                restart=True,
            )

            print(
                "[Animation] restarted"
            )

            return

        # ----------------------------------------------------------
        # Speed
        # ----------------------------------------------------------

        if key == sdl3.SDLK_1:
            self.sprite.animation_speed = (
                0.5
            )

            print(
                "[Animation] speed = 0.5x"
            )

            return

        if key == sdl3.SDLK_2:
            self.sprite.animation_speed = (
                1.0
            )

            print(
                "[Animation] speed = 1.0x"
            )

            return

        if key == sdl3.SDLK_3:
            self.sprite.animation_speed = (
                2.0
            )

            print(
                "[Animation] speed = 2.0x"
            )

            return

        # ----------------------------------------------------------
        # Horizontal flip
        # ----------------------------------------------------------

        if key == sdl3.SDLK_F:
            self.sprite.flip_x = (
                not self.sprite.flip_x
            )

            print(
                "[Sprite] "
                f"flip_x = "
                f"{self.sprite.flip_x}"
            )

            return

        # ----------------------------------------------------------
        # Vertical flip
        # ----------------------------------------------------------

        if key == sdl3.SDLK_V:
            self.sprite.flip_y = (
                not self.sprite.flip_y
            )

            print(
                "[Sprite] "
                f"flip_y = "
                f"{self.sprite.flip_y}"
            )

    # ==============================================================
    # Animation callback
    # ==============================================================

    def _on_frame_changed(
        self,
        frame,
    ) -> None:
        print(
            f"[Frame Changed] "
            f"index={frame.index}"
        )

    # ==============================================================
    # Shutdown
    # ==============================================================

    def shutdown(
        self,
    ) -> None:
        # ----------------------------------------------------------
        # AnimatedSprite references the texture but does not own it.
        # The test created it, so the test destroys it.
        # ----------------------------------------------------------

        if self.texture is not None:
            self.texture.destroy()

            self.texture = None

        super().shutdown()


def main() -> None:
    game = SpriteAnimationTest()

    game.run()


if __name__ == "__main__":
    main()