from __future__ import annotations

"""Play the converted DeathScene cutscene asset.

Run from the project root:

    python -Xgil=0 examples/cutscene/death_cutscene_example.py

Required files:

    MyGame/cutscenes/death_prologue.ncutscene
    assets/cutscenes/death/*.png
    assets/audio/death_scene/*.wav
"""

from nexora import Game
from nexora.cutscene import CutscenePlayerNode
from nexora.scene import Scene


class DeathCutsceneScene(Scene):
    def __init__(self, game: "DeathCutsceneExample") -> None:
        super().__init__("DeathCutscene")
        self.game = game

        self.player = CutscenePlayerNode(
            "DeathCutscenePlayer",
            self.world,
        )
        self.player.asset_path = "MyGame/cutscenes/death_prologue.ncutscene"
        self.player.loop = False
        self.player.play_on_enter = False

        # The runtime node creates its AnimatedSprite, optional lamp light
        # and CinematicCamera2D after the GPU services are available.
        self.add_node(self.player)
        self.player.register_event(
            "open_birth_scene",
            self._birth_scene_requested,
        )

        self.player.build(
            renderer=game.renderer,
            assets=game.assets,
            audio=game.audio,
            scene=self,
            signing_key=getattr(game, "_scene_signing_key", None),
            asset_path=self.player.asset_path,
        )

    def on_enter(self, previous_state) -> None:
        del previous_state
        self.player.play(restart=True)
        print("Playing MyGame/cutscenes/death_prologue.ncutscene")

    def update(self, delta_time: float) -> None:
        super().update(delta_time)

        if self.game.input.action_pressed.quit_example:
            self.game.stop()

    def _birth_scene_requested(self, parameters: dict) -> None:
        del parameters
        print("Death cutscene finished: open_birth_scene")
        print("Replace this handler with your BirthScene transition.")


class DeathCutsceneExample(Game):
    def __init__(self) -> None:
        super().__init__(
            # Reuse the project's normal Documents/Nexora settings and
            # shader cache instead of creating a second project profile.
            project_name="Nexora",
            title="Nexora - Death Cutscene Example",
            width=1280,
            height=720,
            resizable=True,
        )

    def initialize(self) -> None:
        self.input.bind("quit_example", "ESCAPE")
        self.scene = DeathCutsceneScene(self)


if __name__ == "__main__":
    DeathCutsceneExample().run()
