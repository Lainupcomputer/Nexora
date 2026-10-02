from __future__ import annotations

"""Minimal sprite rendering example using Nexora's public Renderer API.

Run from the project root:

    python -Xgil=0 examples/basic/sprite_example.py

Controls:

    ESC -> Exit
"""

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class SpriteExample(Game):
    SPRITE_PATH = "characters/punk_idle_8x64x128.png"
    FRAME_WIDTH = 64
    FRAME_HEIGHT = 128
    COLUMNS = 8
    DISPLAY_SCALE = 2.0

    def __init__(self) -> None:
        super().__init__(
            project_name="SpriteExample",
            title="Nexora - Sprite Example",
            width=960,
            height=540,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.texture: GPUTexture | None = None
        self.frame = 0
        self.elapsed = 0.0

    def initialize(self) -> None:
        self.input.bind("exit", "ESCAPE")
        self.texture = self.assets.load_texture(self.SPRITE_PATH)

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        self.elapsed += float(delta_time)
        if self.elapsed >= 0.12:
            self.elapsed %= 0.12
            self.frame = (self.frame + 1) % self.COLUMNS

        super().update(delta_time)

    def render(self, interpolation: float) -> None:
        del interpolation

        if self.texture is None:
            return

        frame_u = 1.0 / float(self.COLUMNS)
        uv = (
            self.frame * frame_u,
            0.0,
            frame_u,
            1.0,
        )

        self.renderer.sprite(
            self.texture,
            0.0,
            0.0,
            width=self.FRAME_WIDTH * self.DISPLAY_SCALE,
            height=self.FRAME_HEIGHT * self.DISPLAY_SCALE,
            uv=uv,
        )


if __name__ == "__main__":
    SpriteExample().run()
