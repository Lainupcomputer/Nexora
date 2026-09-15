from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class RenderLayerTest(Game):
    IDLE_ASSET_PATH = "characters/punk_idle_8x64x128.png"
    WALK_ASSET_PATH = "characters/punk_walk_8x64x128.png"

    def __init__(self) -> None:
        super().__init__(
            project_name="RenderLayerTest",
            title="Nexora - Render Layer Test",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.idle_texture: GPUTexture | None = None
        self.walk_texture: GPUTexture | None = None

    def initialize(self) -> None:
        self.input.bind("exit", "ESCAPE")

        idle = self.assets.load_texture(self.IDLE_ASSET_PATH)
        walk = self.assets.load_texture(self.WALK_ASSET_PATH)
        device = self.engine.gpu_context.device

        self.idle_texture = GPUTexture(
            device,
            idle.width,
            idle.height,
            data=idle.pixels,
            bytes_per_pixel=idle.bytes_per_pixel,
        )
        self.walk_texture = GPUTexture(
            device,
            walk.width,
            walk.height,
            data=walk.pixels,
            bytes_per_pixel=walk.bytes_per_pixel,
        )

        print("Render layer test started")
        print("Expected order: background -> four sprites -> center marker")
        print("ESC -> Exit")

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return
        super().update(delta_time)

    def render(self, interpolation: float) -> None:
        if self.idle_texture is None or self.walk_texture is None:
            return

        # Background must stay behind everything.
        self.renderer.rect(
            0.0,
            0.0,
            1280.0,
            720.0,
            color=(0.025, 0.03, 0.04, 1.0),
            layer=-100,
        )

        frame_w = 1.0 / 8.0
        idle_uv = (0.0, 0.0, frame_w, 1.0)
        walk_uv = (3.0 * frame_w, 0.0, frame_w, 1.0)

        self.renderer.sprite(
            self.idle_texture,
            -360.0,
            0.0,
            width=128.0,
            height=256.0,
            uv=idle_uv,
            layer=0,
        )
        self.renderer.sprite(
            self.walk_texture,
            -120.0,
            0.0,
            width=128.0,
            height=256.0,
            uv=walk_uv,
            layer=0,
        )
        self.renderer.sprite(
            self.idle_texture,
            120.0,
            0.0,
            width=128.0,
            height=256.0,
            uv=idle_uv,
            layer=0,
        )
        self.renderer.sprite(
            self.walk_texture,
            360.0,
            0.0,
            width=128.0,
            height=256.0,
            uv=walk_uv,
            layer=0,
        )

        # Must appear above the sprites.
        self.renderer.rect(
            0.0,
            0.0,
            14.0,
            14.0,
            color=(1.0, 1.0, 1.0, 1.0),
            layer=100,
        )

    def shutdown(self) -> None:
        if self.idle_texture is not None:
            self.idle_texture.destroy()
            self.idle_texture = None
        if self.walk_texture is not None:
            self.walk_texture.destroy()
            self.walk_texture = None
        super().shutdown()


if __name__ == "__main__":
    RenderLayerTest().run()
