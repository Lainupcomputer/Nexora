from __future__ import annotations

from nexora import Game
from nexora.rendering.gpu.texture import GPUTexture


class RenderLayerFullTest(Game):
    """
    Visual stress test for Nexora's global render layer queue.

    This intentionally mixes different renderer types so a fixed
    per-batch draw order would immediately produce the wrong image.

    Controls:
        ESC -> Exit
    """

    IDLE_ASSET_PATH = "characters/punk_idle_8x64x128.png"
    WALK_ASSET_PATH = "characters/punk_walk_8x64x128.png"

    def __init__(self) -> None:
        super().__init__(
            project_name="RenderLayerFullTest",
            title="Nexora - Full Render Layer Test",
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

        print("=" * 64)
        print(" Nexora FULL Render Layer Test")
        print("=" * 64)
        print("Expected visual stack:")
        print("  -100 background rect")
        print("   -40 large dark circle behind sprites")
        print("     0 four sprites")
        print("    10 red diagonal line over sprites")
        print("    20 green ellipse over line")
        print("    30 yellow triangle")
        print("    40 cyan polygon")
        print("    50 same-layer submission-order demo")
        print("   100 white center marker + text")
        print("ESC -> Exit")

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        super().update(delta_time)

    def render(self, interpolation: float) -> None:
        if self.idle_texture is None or self.walk_texture is None:
            return

        # ------------------------------------------------------
        # Layer -100: background
        # ------------------------------------------------------

        self.renderer.rect(
            0.0,
            0.0,
            1280.0,
            720.0,
            color=(0.025, 0.03, 0.04, 1.0),
            layer=-100,
        )

        # ------------------------------------------------------
        # Layer -40: shape BEHIND sprites
        # ------------------------------------------------------

        self.renderer.circle(
            0.0,
            0.0,
            480.0,
            color=(0.08, 0.09, 0.12, 1.0),
            layer=-40,
        )

        # ------------------------------------------------------
        # Layer 0: multi-texture sprites
        # ------------------------------------------------------

        frame_w = 1.0 / 8.0
        idle_uv = (0.0, 0.0, frame_w, 1.0)
        walk_uv = (3.0 * frame_w, 0.0, frame_w, 1.0)

        positions = (
            (-360.0, self.idle_texture, idle_uv),
            (-120.0, self.walk_texture, walk_uv),
            (120.0, self.idle_texture, idle_uv),
            (360.0, self.walk_texture, walk_uv),
        )

        for x, texture, uv in positions:
            self.renderer.sprite(
                texture,
                x,
                0.0,
                width=128.0,
                height=256.0,
                uv=uv,
                layer=0,
            )

        # ------------------------------------------------------
        # Layer 10: line OVER sprites
        # ------------------------------------------------------

        self.renderer.line(
            -520.0,
            -180.0,
            520.0,
            180.0,
            width=10.0,
            color=(0.9, 0.1, 0.1, 1.0),
            layer=10,
        )

        # ------------------------------------------------------
        # Layer 20: ellipse OVER line
        # ------------------------------------------------------

        self.renderer.ellipse(
            0.0,
            0.0,
            300.0,
            120.0,
            color=(0.1, 0.75, 0.25, 0.72),
            layer=20,
        )

        # ------------------------------------------------------
        # Layer 30: triangle geometry
        # ------------------------------------------------------

        self.renderer.triangle(
            -90.0,
            120.0,
            90.0,
            120.0,
            0.0,
            -60.0,
            color=(0.95, 0.75, 0.1, 0.8),
            layer=30,
        )

        # ------------------------------------------------------
        # Layer 40: polygon geometry
        # ------------------------------------------------------

        self.renderer.polygon(
            (
                (-65.0, -150.0),
                (65.0, -150.0),
                (110.0, -95.0),
                (0.0, -45.0),
                (-110.0, -95.0),
            ),
            color=(0.1, 0.75, 0.9, 0.75),
            layer=40,
        )

        # ------------------------------------------------------
        # Layer 50: SAME-LAYER submission order
        #
        # Expected:
        #   rect -> circle -> line
        # so the white line must be topmost in this small demo.
        # ------------------------------------------------------

        demo_x = 480.0
        demo_y = -220.0

        self.renderer.rect(
            demo_x,
            demo_y,
            170.0,
            120.0,
            color=(0.25, 0.10, 0.35, 1.0),
            layer=50,
        )

        self.renderer.circle(
            demo_x,
            demo_y,
            90.0,
            color=(0.95, 0.35, 0.10, 1.0),
            layer=50,
        )

        self.renderer.line(
            demo_x - 65.0,
            demo_y,
            demo_x + 65.0,
            demo_y,
            width=8.0,
            color=(1.0, 1.0, 1.0, 1.0),
            layer=50,
        )

        # ------------------------------------------------------
        # Layer 100: final overlay
        # ------------------------------------------------------

        self.renderer.rect(
            0.0,
            0.0,
            14.0,
            14.0,
            color=(1.0, 1.0, 1.0, 1.0),
            layer=100,
        )

        self.renderer.text(
            "GLOBAL LAYERS OK",
            -115.0,
            -285.0,
            scale=1.0,
            layer=100,
        )

        self.renderer.text(
            "same layer: rect -> circle -> line",
            310.0,
            -295.0,
            scale=0.65,
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
    RenderLayerFullTest().run()
