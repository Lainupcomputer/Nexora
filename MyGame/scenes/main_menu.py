from __future__ import annotations

from collections.abc import Callable

from nexora.nodes import (
    Button,
    Label,
    VBoxContainer,
)
from nexora.scene import Scene


class MainMenuScene(Scene):
    def __init__(
        self,
        *,
        on_settings: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            "MainMenu"
        )

        self._on_settings_callback = (
            on_settings
        )

        self._on_quit_callback = (
            on_quit
        )

        self._built: bool = False

    # ==============================================================
    # Build
    # ==============================================================

    def build(
        self,
    ) -> None:
        if self._built:
            return

        self._built = True

        menu = self.ui.create_child(
            "MainMenuLayout",
            node_type=VBoxContainer,
        )

        menu.anchor = (
            0.5,
            0.5,
        )

        menu.pivot = (
            0.5,
            0.5,
        )

        menu.position = (
            0.0,
            0.0,
        )

        menu.size = (
            420.0,
            430.0,
        )

        menu.spacing = 18.0

        menu.alignment = (
            "center"
        )

        menu.padding_left = 30.0
        menu.padding_right = 30.0

        menu.padding_top = 25.0
        menu.padding_bottom = 25.0

        # ==========================================================
        # Title
        # ==========================================================

        title = menu.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "MY GAME"
        )

        title.scale = 1.8

        title.size = (
            320.0,
            75.0,
        )

        title.pivot = (
            0.5,
            0.5,
        )

        # ==========================================================
        # New Game
        # ==========================================================

        new_game = menu.create_child(
            "NewGame",
            node_type=Button,
        )

        new_game.text = (
            "Neues Spiel"
        )

        new_game.size = (
            320.0,
            55.0,
        )

        new_game.on_click = (
            self._on_new_game
        )

        # ==========================================================
        # Continue
        # ==========================================================

        continue_game = menu.create_child(
            "Continue",
            node_type=Button,
        )

        continue_game.text = (
            "Fortsetzen"
        )

        continue_game.size = (
            320.0,
            55.0,
        )

        continue_game.on_click = (
            self._on_continue
        )

        # ==========================================================
        # Settings
        # ==========================================================

        settings = menu.create_child(
            "Settings",
            node_type=Button,
        )

        settings.text = (
            "Einstellungen"
        )

        settings.size = (
            320.0,
            55.0,
        )

        settings.on_click = (
            self._on_settings
        )

        # ==========================================================
        # Quit
        # ==========================================================

        quit_button = menu.create_child(
            "Quit",
            node_type=Button,
        )

        quit_button.text = (
            "Beenden"
        )

        quit_button.size = (
            320.0,
            55.0,
        )

        quit_button.on_click = (
            self._on_quit
        )

    # ==============================================================
    # Callbacks
    # ==============================================================

    def _on_new_game(
        self,
    ) -> None:
        print(
            "[MainMenu] New Game"
        )

    def _on_continue(
        self,
    ) -> None:
        print(
            "[MainMenu] Continue"
        )

    def _on_settings(
        self,
    ) -> None:
        print(
            "[MainMenu] Settings"
        )

        if (
            self._on_settings_callback
            is not None
        ):
            self._on_settings_callback()

    def _on_quit(
        self,
    ) -> None:
        print(
            "[MainMenu] Quit"
        )

        if (
            self._on_quit_callback
            is not None
        ):
            self._on_quit_callback()