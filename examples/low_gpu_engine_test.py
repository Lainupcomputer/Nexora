from __future__ import annotations

from nexora.core.engine import Engine
from nexora.rendering.gpu.texture import GPUTexture


class GPUEngineTest:
    def __init__(self):
        self.engine: Engine | None = None
        self.texture: GPUTexture | None = None

        self.sprite_width = 96
        self.sprite_height = 96

    def initialize(self):
        print("Loading: assets\\demo_sprite.png")

        # --------------------------------------------------------------
        # Load image through Nexora's SDL3 asset system.
        # --------------------------------------------------------------

        image = self.engine.assets.load_texture(
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

        # --------------------------------------------------------------
        # Upload CPU image data to the GPU.
        #
        # GPU resource creation stays on the rendering thread.
        # --------------------------------------------------------------

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

        self.engine.renderer.sprite(
            self.texture,
            self.engine.renderer.width / 2,
            self.engine.renderer.height / 2,
            width=self.sprite_width,
            height=self.sprite_height,
        )

    def handle_event(self, event):
        pass

    def shutdown(self):
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None


def main():
    game = GPUEngineTest()

    engine = Engine(
        game,
        width=1280,
        height=720,
        title="Nexora GPU Engine Test",
    )

    game.engine = engine

    try:
        engine.run()
    finally:
        game.shutdown()


if __name__ == "__main__":
    main()