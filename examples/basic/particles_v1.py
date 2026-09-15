from __future__ import annotations

from nexora import Game
from nexora.nodes import ParticleEmitter2D
from nexora.particles import ParticlePresets
from nexora.scene import Scene


class ParticleExample(Game):
    def __init__(self) -> None:
        super().__init__(
            title="Nexora - Modular Particles V1",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )
        self.smoke = None
        self.sparks = None

    def initialize(self) -> None:
        self.scene = Scene("Particles")
        self.input.bind("exit", "ESCAPE")
        self.input.bind("burst", "SPACE")

        self.smoke = self.scene.create_node("Smoke", node_type=ParticleEmitter2D)
        self.smoke.transform.x = -180.0
        self.smoke.transform.y = 80.0
        self.smoke.config = ParticlePresets.smoke()
        self.smoke.config.layer = 100
        self.smoke.play()

        self.sparks = self.scene.create_node("Sparks", node_type=ParticleEmitter2D)
        self.sparks.transform.x = 180.0
        self.sparks.transform.y = 80.0
        self.sparks.config = ParticlePresets.sparks()
        self.sparks.config.layer = 100

        print("ESC   -> Exit")
        print("SPACE -> Spark burst")

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return
        if self.input.action("burst").pressed:
            self.sparks.restart()
        super().update(delta_time)


if __name__ == "__main__":
    ParticleExample().run()
