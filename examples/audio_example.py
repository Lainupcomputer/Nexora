from __future__ import annotations

from nexora import Game
from nexora.audio import AudioSource


class AudioExample(Game):
    """
    Nexora audio example.

    Controls
    --------
    F
        Play sound effect

    ESC
        Exit
    """

    def __init__(self) -> None:
        super().__init__(
            title="Nexora - Audio Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.sound = None
        self.source: AudioSource | None = None

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self) -> None:
        self.input.bind("play_sound", "F")
        self.input.bind("escape", "ESCAPE")

        # ------------------------------------------------------
        # Load sound
        # ------------------------------------------------------

        print("Loading: assets\\demo_sound.wav")

        self.sound = self.audio.load(
            "assets/demo_sound.wav"
        )

        print(
            f"Audio loaded: "
            f"{self.sound.duration:.2f}s"
        )

        print(
            f"Format: "
            f"{self.sound.frequency} Hz, "
            f"{self.sound.channels} channel(s)"
        )

        # ------------------------------------------------------
        # Create playback source
        # ------------------------------------------------------

        self.source = AudioSource(
            self.sound,
            bus=self.audio.get_bus("SFX"),
        )

        print("Audio initialized.")

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(self, dt: float) -> None:
        if self.input.action("escape").pressed:
            self.stop()
            return

        if self.input.action("play_sound").pressed:
            if self.source is None:
                return

            self.audio.player.play(self.source)

            print("SFX PLAY")

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self) -> None:
        pass

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(self) -> None:
        if self.source is not None:
            self.source.stop()
            self.source = None


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    game = AudioExample()
    game.run()