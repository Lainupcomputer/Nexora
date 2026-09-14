from __future__ import annotations
import os

os.environ.setdefault(
    "SDL_GPU_DRIVER",
    "vulkan",
)


from pathlib import Path

from nexora.core.game import Game

from scenes.main_menu import MainMenuScene
from scenes.settings import SettingsScene


ROOT = Path(
    __file__
).resolve().parent


SETTINGS_PATH = (
    ROOT
    / "settings.json"
)


SETTINGS_DEFAULTS = {
    "video": {
        "fullscreen": False,
        "vsync": True,
    },
    "audio": {
        "master_volume": 1.0,
        "music_volume": 0.8,
        "sfx_volume": 0.8,
    },
}


class MyGame(Game):
    def __init__(
        self,
    ) -> None:
        # ==========================================================
        # Nexora
        # ==========================================================

        super().__init__(
            title="My Game",
            width=1280,
            height=720,
            resizable=True,
            settings_path=SETTINGS_PATH,
            settings_defaults=SETTINGS_DEFAULTS,
        )

        # ==========================================================
        # Apply saved startup settings
        #
        # The Engine has not been created yet, so changing the
        # startup values here is safe.
        # ==========================================================

        self._fullscreen = bool(
            self.settings.get(
                "video.fullscreen",
                False,
            )
        )

        self._vsync = bool(
            self.settings.get(
                "video.vsync",
                True,
            )
        )

        # ==========================================================
        # Scenes
        # ==========================================================

        self.main_menu = MainMenuScene(
            on_settings=self.open_settings,
            on_quit=self.stop,
        )

        self.settings_scene = SettingsScene(
            settings=self.settings,
            on_apply=self.apply_settings,
            on_back=self.open_main_menu,
        )

        # ==========================================================
        # Initial scene
        # ==========================================================

        self.scene = (
            self.main_menu
        )

    # ==============================================================
    # Initialize
    # ==============================================================

    def initialize(
        self,
    ) -> None:
        print(
            "=" * 60
        )

        print(
            " My Game"
        )

        print(
            "=" * 60
        )

        print()

        # ----------------------------------------------------------
        # Build scenes
        # ----------------------------------------------------------

        self.main_menu.build()
        self.settings_scene.build()

        # ----------------------------------------------------------
        # Initial scene
        # ----------------------------------------------------------

        self.open_main_menu()

        print(
            "[Game] Ready."
        )

        print()

    # ==============================================================
    # Scene navigation
    # ==============================================================

    def open_main_menu(
        self,
    ) -> None:
        print(
            "[Game] Open Main Menu"
        )

        self.scene = (
            self.main_menu
        )

    def open_settings(
        self,
    ) -> None:
        print(
            "[Game] Open Settings"
        )

        # Refresh controls from the actual SettingsStore before
        # displaying the scene.

        self.settings_scene.refresh_from_settings()

        self.scene = (
            self.settings_scene
        )

    # ==============================================================
    # Apply settings
    # ==============================================================

    def apply_settings(
        self,
    ) -> None:
        """
        Apply persistent settings to live engine services.

        The SettingsScene already wrote the new values into the
        SettingsStore before this callback is executed.
        """

        # ==========================================================
        # Fullscreen
        # ==========================================================

        fullscreen = bool(
            self.settings.get(
                "video.fullscreen",
                False,
            )
        )

        if fullscreen:
            self.set_fullscreen()

        else:
            self.set_windowed()

        # ==========================================================
        # VSync
        # ==========================================================

        vsync = bool(
            self.settings.get(
                "video.vsync",
                True,
            )
        )

        self.set_vsync(
            vsync
        )

        # ==========================================================
        # Audio
        # ==========================================================
        #
        # Values are already stored:
        #
        # audio.master_volume
        # audio.music_volume
        # audio.sfx_volume
        #
        # We connect these to Nexora's Audio API once we inspect
        # the exact current audio interface.

        master_volume = float(
            self.settings.get(
                "audio.master_volume",
                1.0,
            )
        )

        music_volume = float(
            self.settings.get(
                "audio.music_volume",
                0.8,
            )
        )

        sfx_volume = float(
            self.settings.get(
                "audio.sfx_volume",
                0.8,
            )
        )

        print(
            "[Settings] Applied:"
        )

        print(
            f"  fullscreen = {fullscreen}"
        )

        print(
            f"  vsync      = {vsync}"
        )

        print(
            f"  master     = {master_volume:.2f}"
        )

        print(
            f"  music      = {music_volume:.2f}"
        )

        print(
            f"  sfx        = {sfx_volume:.2f}"
        )

    # ==============================================================
    # Shutdown
    # ==============================================================

    def shutdown(
        self,
    ) -> None:
        # Make sure settings are persisted before the game exits.

        self.settings.save()

        super().shutdown()


# ==================================================================
# Entry point
# ==================================================================


def main() -> None:
    game = MyGame()

    game.run()


if __name__ == "__main__":
    main()