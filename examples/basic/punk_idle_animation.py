from __future__ import annotations

from nexora.animation import AnimationClip
from nexora.core.game import Game
from nexora.nodes import AnimatedSprite
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class PunkCharacterAnimationExample(Game):
    """
    Idle + walk character animation example.

    Sprite sheets:

        punk_idle_8x64x128.png
        punk_walk_8x64x128.png

    Both sheets:

        512 x 128 px
        8 columns
        1 row
        64 x 128 px per frame

    Controls:

        A       Move left
        D       Move right
        SHIFT   Sprint
        ESC     Exit

    Animation states:

        Standing -> idle
        Moving   -> walk

    Direction:

        Right -> flip_x = False
        Left  -> flip_x = True
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
    # ANIMATION
    # ==========================================================

    IDLE_FPS = 8.0
    WALK_FPS = 10.0

    # ==========================================================
    # CHARACTER
    # ==========================================================

    CHARACTER_SCALE = 2.0

    CHARACTER_WIDTH = (
        FRAME_WIDTH
        * CHARACTER_SCALE
    )

    CHARACTER_HEIGHT = (
        FRAME_HEIGHT
        * CHARACTER_SCALE
    )

    # ==========================================================
    # MOVEMENT
    # ==========================================================

    MOVE_SPEED = 220.0

    SPRINT_MULTIPLIER = 1.6

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
    ) -> None:
        super().__init__()

        # ======================================================
        # SCENE
        # ======================================================

        self.scene = Scene(
            "PunkCharacterAnimationExample"
        )

        # ======================================================
        # GPU RESOURCES
        # ======================================================

        self.idle_texture: (
            GPUTexture
            | None
        ) = None

        self.walk_texture: (
            GPUTexture
            | None
        ) = None

        # ======================================================
        # CHARACTER
        # ======================================================

        self.character: (
            AnimatedSprite
            | None
        ) = None

        # ======================================================
        # STATE
        # ======================================================

        self._animation_state = (
            "idle"
        )

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        print("=" * 60)
        print(" Nexora Punk Character Animation")
        print("=" * 60)
        print()

        # ======================================================
        # LOAD IDLE
        # ======================================================

        idle_image = (
            self.assets.load_texture(
                self.IDLE_ASSET_PATH,
            )
        )

        self._validate_sheet(
            "Idle",
            idle_image.width,
            idle_image.height,
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

        self._validate_sheet(
            "Walk",
            walk_image.width,
            walk_image.height,
        )

        print(
            f"Walk sheet: "
            f"{walk_image.width}x"
            f"{walk_image.height}"
        )

        # ======================================================
        # GPU TEXTURES
        # ======================================================

        self.idle_texture = GPUTexture(
            self.engine.gpu_context.device,
            idle_image.width,
            idle_image.height,
            data=bytes(
                idle_image.pixels
            ),
            bytes_per_pixel=4,
        )

        self.walk_texture = GPUTexture(
            self.engine.gpu_context.device,
            walk_image.width,
            walk_image.height,
            data=bytes(
                walk_image.pixels
            ),
            bytes_per_pixel=4,
        )

        # ======================================================
        # CREATE CHARACTER
        # ======================================================

        node = self.scene.create_node(
            "PunkCharacter",
            node_type=AnimatedSprite,
        )

        assert isinstance(
            node,
            AnimatedSprite,
        )

        self.character = node

        # ======================================================
        # CHARACTER CONFIGURATION
        # ======================================================

        self.character.texture = (
            self.idle_texture
        )

        self.character.width = (
            self.CHARACTER_WIDTH
        )

        self.character.height = (
            self.CHARACTER_HEIGHT
        )

        self.character.origin = (
            0.5,
            0.5,
        )

        self.character.transform.x = 0.0
        self.character.transform.y = 0.0

        # ======================================================
        # IDLE ANIMATION
        # ======================================================

        idle = AnimationClip.from_row(
            "idle",
            row=0,
            start_column=0,
            frame_count=(
                self.FRAME_COUNT
            ),
            columns=(
                self.COLUMNS
            ),
            rows=(
                self.ROWS
            ),
            fps=(
                self.IDLE_FPS
            ),
            loop=True,
        )

        self.character.add_animation(
            idle
        )

        # ======================================================
        # WALK ANIMATION
        # ======================================================

        walk = AnimationClip.from_row(
            "walk",
            row=0,
            start_column=0,
            frame_count=(
                self.FRAME_COUNT
            ),
            columns=(
                self.COLUMNS
            ),
            rows=(
                self.ROWS
            ),
            fps=(
                self.WALK_FPS
            ),
            loop=True,
        )

        self.character.add_animation(
            walk
        )

        # ======================================================
        # INITIAL STATE
        # ======================================================

        self.character.play(
            "idle"
        )

        # ======================================================
        # INFO
        # ======================================================

        print()
        print(
            f"Frame size: "
            f"{self.FRAME_WIDTH}x"
            f"{self.FRAME_HEIGHT}"
        )

        print(
            f"Display size: "
            f"{self.CHARACTER_WIDTH:.0f}x"
            f"{self.CHARACTER_HEIGHT:.0f}"
        )

        print()

        print(
            "Animations:"
        )

        print(
            f"  idle -> "
            f"{self.FRAME_COUNT} frames "
            f"@ {self.IDLE_FPS} FPS"
        )

        print(
            f"  walk -> "
            f"{self.FRAME_COUNT} frames "
            f"@ {self.WALK_FPS} FPS"
        )

        print()

        print(
            "Controls:"
        )

        print(
            "  A       -> Move left"
        )

        print(
            "  D       -> Move right"
        )

        print(
            "  SHIFT   -> Sprint"
        )

        print(
            "  ESC     -> Exit"
        )

        print()

    # ==========================================================
    # VALIDATE SHEET
    # ==========================================================

    def _validate_sheet(
        self,
        name: str,
        width: int,
        height: int,
    ) -> None:
        expected_width = (
            self.FRAME_WIDTH
            * self.COLUMNS
        )

        expected_height = (
            self.FRAME_HEIGHT
            * self.ROWS
        )

        if width != expected_width:
            raise ValueError(
                f"{name} sprite sheet has "
                f"invalid width. "
                f"Expected {expected_width}px, "
                f"got {width}px."
            )

        if height != expected_height:
            raise ValueError(
                f"{name} sprite sheet has "
                f"invalid height. "
                f"Expected {expected_height}px, "
                f"got {height}px."
            )

    # ==========================================================
    # CHANGE ANIMATION
    # ==========================================================

    def _set_animation(
        self,
        state: str,
    ) -> None:
        """
        Change animation state only when necessary.

        The texture and AnimationClip are switched together.
        """

        if self.character is None:
            return

        if state == self._animation_state:
            return

        # ======================================================
        # IDLE
        # ======================================================

        if state == "idle":
            if self.idle_texture is None:
                return

            self.character.texture = (
                self.idle_texture
            )

            self.character.play(
                "idle",
                restart=True,
            )

        # ======================================================
        # WALK
        # ======================================================

        elif state == "walk":
            if self.walk_texture is None:
                return

            self.character.texture = (
                self.walk_texture
            )

            self.character.play(
                "walk",
                restart=True,
            )

        else:
            raise ValueError(
                f"Unknown animation state: "
                f"{state!r}"
            )

        self._animation_state = (
            state
        )

        print(
            f"[Character] "
            f"animation -> {state}"
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ======================================================
        # EXIT
        # ======================================================

        if self.input.key_pressed(
            "ESCAPE"
        ):
            self.stop()

            return

        if self.character is None:
            super().update(
                delta_time
            )

            return

        # ======================================================
        # MOVEMENT INPUT
        # ======================================================

        direction = 0.0

        if self.input.key_down(
            "A"
        ):
            direction -= 1.0

        if self.input.key_down(
            "D"
        ):
            direction += 1.0

        # ======================================================
        # IDLE
        # ======================================================

        if direction == 0.0:
            self._set_animation(
                "idle"
            )

        # ======================================================
        # WALK
        # ======================================================

        else:
            self._set_animation(
                "walk"
            )

            # ==================================================
            # DIRECTION / FLIP
            # ==================================================

            if direction < 0.0:
                self.character.flip_x = (
                    True
                )

            else:
                self.character.flip_x = (
                    False
                )

            # ==================================================
            # SPEED
            # ==================================================

            speed = (
                self.MOVE_SPEED
            )

            if self.input.key_down(
                "LSHIFT"
            ):
                speed *= (
                    self.SPRINT_MULTIPLIER
                )

            # ==================================================
            # MOVE
            # ==================================================

            self.character.transform.x += (
                direction
                * speed
                * delta_time
            )

        # ======================================================
        # SCENE UPDATE
        # ======================================================

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
        super().render(
            interpolation
        )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        # ======================================================
        # IDLE TEXTURE
        # ======================================================

        if self.idle_texture is not None:
            self.idle_texture.destroy()

            self.idle_texture = None

        # ======================================================
        # WALK TEXTURE
        # ======================================================

        if self.walk_texture is not None:
            self.walk_texture.destroy()

            self.walk_texture = None

        self.character = None

        super().shutdown()


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    PunkCharacterAnimationExample().run()