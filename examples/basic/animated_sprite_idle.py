from __future__ import annotations

from nexora import Game
from nexora.animation import AnimationSet
from nexora.nodes import AnimatedSprite
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class AnimatedSpriteIdleExample(Game):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - AnimatedSprite Texture Test",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.texture: GPUTexture | None = None
        self.character: AnimatedSprite | None = None

    def initialize(
        self,
    ) -> None:
        self.input.bind(
            "exit",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "AnimatedSpriteTextureTest",
        )

        self.scene = scene

        # ------------------------------------------------------
        # Testweise die bekannte funktionierende Textur laden.
        # ------------------------------------------------------

        image = self.assets.load_texture(
            "demo_sprite.png",
        )

        print(
            f"Test-Sprite geladen: "
            f"{image.width}x{image.height}"
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        # ------------------------------------------------------
        # AnimatedSprite-Node
        # ------------------------------------------------------

        self.character = AnimatedSprite(
            "TestCharacter",
            scene.world,
        )

        scene.add_node(
            self.character,
        )

        self.character.texture = self.texture

        self.character.width = 256.0
        self.character.height = 256.0

        self.character.origin = (
            0.5,
            0.5,
        )

        # Bei (0, 0) liegt der Sprite genau in der Bildschirmmitte.
        self.character.transform.x = 0.0
        self.character.transform.y = 0.0

        # ------------------------------------------------------
        # Eine Frame-Animation:
        # demo_sprite.png ist kein Sprite-Sheet.
        # ------------------------------------------------------

        animations = AnimationSet(
            columns=1,
            rows=1,
        )

        animations.add_row(
            "idle",
            row=0,
            frame_count=1,
            fps=1.0,
            loop=True,
        )

        self.character.add_animations(
            animations,
        )

        self.character.play(
            "idle",
        )

        print(
            "Test-Sprite gestartet. "
            "ESC beendet das Beispiel."
        )

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

    def render(
        self,
        interpolation: float,
    ) -> None:
        # Hintergrund
        self.renderer.rect(
            0.0,
            0.0,
            1280.0,
            720.0,
            color=(
                0.025,
                0.03,
                0.04,
                1.0,
            ),
        )

        # Sichtbare Zielmarkierung hinter dem Sprite.
        self.renderer.rect(
            0.0,
            0.0,
            280.0,
            280.0,
            color=(
                0.10,
                0.18,
                0.20,
                1.0,
            ),
        )

        # Zeichnet die AnimatedSprite-Node.
        super().render(
            interpolation,
        )

    def shutdown(
        self,
    ) -> None:
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None

        super().shutdown()


if __name__ == "__main__":
    AnimatedSpriteIdleExample().run()