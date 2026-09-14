from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class GPUEngineTest(Game):
    def __init__(self):
        super().__init__(
            title="Nexora GPU Engine Test",
            width=1280,
            height=720,
        )

        self.texture: GPUTexture | None = None

        self.sprite_width = 96
        self.sprite_height = 96

    def initialize(self):
        print("Loading: assets\\demo_sprite.png")

        image = self.assets.load_texture(
            "demo_sprite.png"
        )

        print(
            f"Image loaded: "
            f"{image.width}x{image.height}"
        )

        print(
            f"Pixel data: "
            f"{image.byte_size} bytes"
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        self.sprite_width = image.width
        self.sprite_height = image.height

        print(
            f"GPU texture created: "
            f"{self.sprite_width}x{self.sprite_height}"
        )

    def update(self, dt):
        pass

    def render(self):
        if self.texture is None:
            return

        self.renderer.sprite(
            self.texture,
            0,
            0,
            width=self.sprite_width,
            height=self.sprite_height,
        )

    def handle_event(self, event):
        pass

    def shutdown(self):
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None


if __name__ == "__main__":
    game = GPUEngineTest()
    game.run()