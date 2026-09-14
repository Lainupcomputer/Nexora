from __future__ import annotations
from nexora.nodes.node import Node
from nexora import Game

from nexora.nodes import (
    Camera2D,
    Node,
)

from nexora.scene import (
    FadeSceneTransition,
    Scene,
)


# ==============================================================
# BACKGROUND NODE
# ==============================================================


class BackgroundNode(Node):
    """
    Simple fullscreen colored background.

    Used only to make the two example scenes visually distinct.
    """

    def __init__(
        self,
        name: str,
        world,
        *,
        color,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.color = color

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        renderer.rect(
            0.0,
            0.0,
            renderer.width,
            renderer.height,
            color=self.color,
        )


# ==============================================================
# MENU SCENE
# ==============================================================


class MenuScene(Scene):
    def __init__(
        self,
        renderer,
    ) -> None:
        super().__init__(
            "Menu"
        )

        # ======================================================
        # Background
        # ======================================================

        background = BackgroundNode(
            "Background",
            self.world,
            color=(
                0.08,
                0.12,
                0.22,
                1.0,
            ),
        )

        self.add_node(
            background
        )

        # ======================================================
        # Primary Camera
        # ======================================================
        #
        # Assigning through Scene.camera automatically registers
        # this camera as the scene's primary camera.
        #
        # Scene transitions can therefore discover it without
        # the game having to pass the camera explicitly.
        # ======================================================

        self.camera = Camera2D(
            "MenuCamera",
            self.world,
            renderer,
        )

        # Camera is intentionally added after the background so
        # fullscreen camera effects render on top.
        self.add_node(
            self.camera
        )

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def on_enter(
        self,
        previous_state,
    ) -> None:
        print(
            "[Menu] enter from",
            previous_state.value,
        )

    def on_exit(
        self,
        previous_state,
    ) -> None:
        print(
            "[Menu] exit from",
            previous_state.value,
        )

    def on_pause(
        self,
    ) -> None:
        print(
            "[Menu] paused"
        )

    def on_resume(
        self,
    ) -> None:
        print(
            "[Menu] resumed"
        )


# ==============================================================
# GAME SCENE
# ==============================================================


class GameScene(Scene):
    def __init__(
        self,
        renderer,
    ) -> None:
        super().__init__(
            "Game"
        )

        # ======================================================
        # Background
        # ======================================================

        background = BackgroundNode(
            "Background",
            self.world,
            color=(
                0.18,
                0.07,
                0.06,
                1.0,
            ),
        )

        self.add_node(
            background
        )

        # ======================================================
        # Primary Camera
        # ======================================================

        self.camera = Camera2D(
            "GameCamera",
            self.world,
            renderer,
        )

        self.add_node(
            self.camera
        )

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def on_enter(
        self,
        previous_state,
    ) -> None:
        print(
            "[Game] enter from",
            previous_state.value,
        )

    def on_exit(
        self,
        previous_state,
    ) -> None:
        print(
            "[Game] exit from",
            previous_state.value,
        )

    def on_pause(
        self,
    ) -> None:
        print(
            "[Game] paused"
        )

    def on_resume(
        self,
    ) -> None:
        print(
            "[Game] resumed"
        )


# ==============================================================
# GAME
# ==============================================================


class SceneTransitionExample(Game):
    """
    Nexora SceneTransition example.

    Controls
    --------

    SPACE
        Toggle between Menu and Game using FadeSceneTransition.

    ESC
        Exit.

    Expected flow
    -------------

        Menu
          ↓
        fade to black
          ↓
        scene switch
          ↓
        fade from black
          ↓
        Game

    Cameras are discovered automatically through Scene.camera.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title=(
                "Nexora - Scene Transition Example"
            ),
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.menu_scene: (
            MenuScene | None
        ) = None

        self.game_scene: (
            GameScene | None
        ) = None

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ======================================================
        # Input
        # ======================================================

        self.input.bind(
            "switch_scene",
            "SPACE",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ======================================================
        # Scenes
        # ======================================================

        self.menu_scene = (
            MenuScene(
                self.renderer
            )
        )

        self.game_scene = (
            GameScene(
                self.renderer
            )
        )

        # ------------------------------------------------------
        # Load scenes
        # ------------------------------------------------------

        self.scenes.load(
            self.menu_scene
        )

        self.scenes.load(
            self.game_scene
        )

        # ------------------------------------------------------
        # Initial scene
        # ------------------------------------------------------

        self.scenes.change_scene(
            "Menu"
        )

        # ======================================================
        # Info
        # ======================================================

        print()
        print("=" * 64)
        print(
            " Nexora Scene Transition Example"
        )
        print("=" * 64)
        print()

        print(
            "SPACE  Menu <-> Game"
        )

        print(
            "ESC    Exit"
        )

        print()

        print(
            "Current scene:",
            self.scenes.active_scene_name,
        )

        print()

        print(
            "Menu camera:",
            self.menu_scene.camera.name,
        )

        print(
            "Game camera:",
            self.game_scene.camera.name,
        )

        print()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ======================================================
        # Exit
        # ======================================================

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ======================================================
        # Scene switch
        # ======================================================

        if self.input.action(
            "switch_scene"
        ).pressed:

            # --------------------------------------------------
            # SceneManager guards transitions too, but checking
            # here avoids intentionally throwing an exception
            # if SPACE is pressed during the fade.
            # --------------------------------------------------

            if not (
                self.scenes.transitioning
            ):
                self._toggle_scene()

        # ======================================================
        # Normal scene update
        # ======================================================

        super().update(
            delta_time
        )

    # ==========================================================
    # TOGGLE SCENE
    # ==========================================================

    def _toggle_scene(
        self,
    ) -> None:
        current = (
            self.scenes.active_scene_name
        )

        # ======================================================
        # MENU -> GAME
        # ======================================================

        if current == "Menu":
            print()
            print(
                "Transition: Menu -> Game"
            )

            self.scenes.change_scene(
                "Game",
                transition=(
                    FadeSceneTransition(
                        duration=1.0,
                        color=(
                            0.0,
                            0.0,
                            0.0,
                        ),
                        easing=(
                            "ease_in_out"
                        ),
                    )
                ),
            )

            return

        # ======================================================
        # GAME -> MENU
        # ======================================================

        if current == "Game":
            print()
            print(
                "Transition: Game -> Menu"
            )

            self.scenes.change_scene(
                "Menu",
                transition=(
                    FadeSceneTransition(
                        duration=1.0,
                        color=(
                            0.0,
                            0.0,
                            0.0,
                        ),
                        easing=(
                            "ease_in_out"
                        ),
                    )
                ),
            )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        super().shutdown()


# ==============================================================
# MAIN
# ==============================================================


if __name__ == "__main__":
    SceneTransitionExample().run()