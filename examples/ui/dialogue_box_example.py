from __future__ import annotations

from pathlib import Path

from nexora.core.game import Game
from nexora.nodes import DialogueBox, DialogueChoice, DialoguePage
from nexora.scene import Scene


class DialogueBoxExample(Game):
    """Minimal narrative dialogue example.

    For portraits, load GPU textures once during initialization and pass
    them as ``portrait=...`` to ``DialoguePage``.
    """

    def __init__(self) -> None:
        super().__init__(
            title="Nexora Dialogue Box",
            width=1280,
            height=720,
            resizable=True,
        )

        scene = Scene("DialogueBoxExample")
        self.scene = scene
        self.save_data: dict[str, object] = {}

        self.dialogue = scene.ui.create_child(
            "Dialogue",
            node_type=DialogueBox,
        )
        self.dialogue.set_pages(
            [
                DialoguePage(
                    speaker="Jonas",
                    text=(
                        "Mein Leben war nie ruhig. "
                        "Aber heute muss ich ihr helfen."
                    ),
                ),
                DialoguePage(
                    speaker="Jonas",
                    text="Willst du dich mit Clara anfreunden?",
                    choices=(
                        DialogueChoice(
                            "Ja",
                            value=True,
                            callback=self._store_clara_choice,
                        ),
                        DialogueChoice(
                            "Nein",
                            value=False,
                            callback=self._store_clara_choice,
                        ),
                    ),
                ),
                DialoguePage(
                    speaker="Jonas",
                    text="Dann sehen wir uns morgen.",
                ),
            ]
        )

    def _store_clara_choice(self, choice: DialogueChoice) -> None:
        """Example callback: persist the selected answer in game state."""

        self.save_data["clara_friend"] = choice.value
        print(
            "[Dialogue] save_data['clara_friend'] = "
            f"{choice.value!r}"
        )

    @staticmethod
    def _find_typing_sound() -> Path | None:
        project_root = Path(__file__).resolve().parents[2]
        candidates = (
            project_root / "MyGame" / "assets" / "audio" / "dialogue" / "typing.wav",
            project_root / "assets" / "audio" / "dialogue" / "typing.wav",
        )
        return next((path for path in candidates if path.is_file()), None)

    def initialize(self) -> None:
        typing_path = self._find_typing_sound()
        if typing_path is not None:
            typing_sound = self.assets.sound(typing_path)
            self.dialogue.set_typing_sound(
                self.audio,
                typing_sound,
                volume=0.08,
                min_interval=0.07,
            )
        else:
            print(
                "[Dialogue] typing.wav nicht gefunden. Erwartet unter "
                "MyGame/assets/audio/dialogue/typing.wav"
            )

        self.dialogue.open()


if __name__ == "__main__":
    DialogueBoxExample().run()
