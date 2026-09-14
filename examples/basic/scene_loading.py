from __future__ import annotations

from nexora import Game

from nexora.nodes import (
    Label,
)

from nexora.scene import (
    FadeSceneTransition,
    LoadingScene,
    Scene,
    SceneLoadTask,
)


# ==============================================================
# HOME SCENE
# ==============================================================


class HomeScene(Scene):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            "Home"
        )

        title = self.ui.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "HQ - Press SPACE to enter Dungeon"
        )

        title.anchor = (
            0.5,
            0.5,
        )

        title.pivot = (
            0.5,
            0.5,
        )

        title.position = (
            0.0,
            0.0,
        )


# ==============================================================
# DUNGEON SCENE
# ==============================================================


class DungeonScene(Scene):
    def __init__(
        self,
        generated_data: dict,
    ) -> None:
        super().__init__(
            "Dungeon"
        )

        self.generated_data = (
            generated_data
        )

        title = self.ui.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "Dungeon generated - "
            "Press ESC to exit"
        )

        title.anchor = (
            0.5,
            0.5,
        )

        title.pivot = (
            0.5,
            0.5,
        )

        title.position = (
            0.0,
            -30.0,
        )

        info = self.ui.create_child(
            "Info",
            node_type=Label,
        )

        info.text = (
            f"Rooms: "
            f"{generated_data.get('rooms', 0)}"
        )

        info.anchor = (
            0.5,
            0.5,
        )

        info.pivot = (
            0.5,
            0.5,
        )

        info.position = (
            0.0,
            30.0,
        )


# ==============================================================
# GAME
# ==============================================================


class SceneLoadingExample(Game):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            title=(
                "Nexora - Scene Loading Example"
            ),
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.generated_data: dict = {}

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input.bind(
            "load_dungeon",
            "SPACE",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Loading scene
        # ------------------------------------------------------

        self.scenes.register(
            "Loading",
            lambda: LoadingScene(
                "Loading"
            ),
            keep_loaded=True,
        )

        # ------------------------------------------------------
        # Home
        # ------------------------------------------------------

        self.scenes.register(
            "Home",
            lambda: HomeScene(),
            keep_loaded=True,
        )

        # ------------------------------------------------------
        # Dungeon
        #
        # Factory uses data produced by SceneLoadTask.
        # ------------------------------------------------------

        self.scenes.register(
            "Dungeon",
            lambda: DungeonScene(
                self.generated_data
            ),
            keep_loaded=False,
        )

        # ------------------------------------------------------
        # Start
        # ------------------------------------------------------

        self.scenes.change_scene(
            "Home"
        )

        print()
        print("=" * 64)
        print(
            " Nexora Scene Loading Example"
        )
        print("=" * 64)
        print()

        print(
            "SPACE  Generate dungeon"
        )

        print(
            "ESC    Exit"
        )

        print()

    # ==========================================================
    # CREATE TASK
    # ==========================================================

    def _create_dungeon_task(
        self,
    ) -> SceneLoadTask:
        task = SceneLoadTask(
            "Dungeon"
        )

        # ------------------------------------------------------
        # Temporary generation state
        # ------------------------------------------------------

        generation = {
            "layout": 0,
            "rooms": 0,
            "enemies": 0,
            "loot": 0,
            "navigation": 0,
        }

        # ======================================================
        # Stage 1
        # ======================================================

        def prepare_seed() -> None:
            self.generated_data.clear()

            self.generated_data[
                "seed"
            ] = 1337

        task.add_stage(
            "seed",
            weight=0.5,
            status=(
                "Preparing dungeon seed..."
            ),
            callback=prepare_seed,
        )

        # ======================================================
        # Stage 2 - incremental
        # ======================================================

        def generate_layout(
            delta_time: float,
        ) -> bool:
            generation[
                "layout"
            ] += 1

            return (
                generation[
                    "layout"
                ]
                >= 60
            )

        task.add_stage(
            "layout",
            weight=2.0,
            status=(
                "Generating dungeon layout..."
            ),
            update=generate_layout,
        )

        # ======================================================
        # Stage 3
        # ======================================================

        def generate_rooms(
            delta_time: float,
        ) -> bool:
            generation[
                "rooms"
            ] += 1

            if (
                generation[
                    "rooms"
                ]
                >= 90
            ):
                self.generated_data[
                    "rooms"
                ] = 24

                return True

            return False

        task.add_stage(
            "rooms",
            weight=3.0,
            status=(
                "Building rooms..."
            ),
            update=generate_rooms,
        )

        # ======================================================
        # Stage 4
        # ======================================================

        def place_enemies(
            delta_time: float,
        ) -> bool:
            generation[
                "enemies"
            ] += 1

            return (
                generation[
                    "enemies"
                ]
                >= 50
            )

        task.add_stage(
            "enemies",
            weight=1.5,
            status=(
                "Placing enemies..."
            ),
            update=place_enemies,
        )

        # ======================================================
        # Stage 5
        # ======================================================

        def place_loot(
            delta_time: float,
        ) -> bool:
            generation[
                "loot"
            ] += 1

            return (
                generation[
                    "loot"
                ]
                >= 40
            )

        task.add_stage(
            "loot",
            weight=1.0,
            status=(
                "Placing loot..."
            ),
            update=place_loot,
        )

        # ======================================================
        # Stage 6
        # ======================================================

        def navigation(
            delta_time: float,
        ) -> bool:
            generation[
                "navigation"
            ] += 1

            return (
                generation[
                    "navigation"
                ]
                >= 70
            )

        task.add_stage(
            "navigation",
            weight=2.0,
            status=(
                "Preparing navigation..."
            ),
            update=navigation,
        )

        # ======================================================
        # Finalize
        # ======================================================

        def finalize() -> None:
            self.generated_data[
                "ready"
            ] = True

        task.add_stage(
            "finalize",
            weight=0.5,
            status=(
                "Finalizing dungeon..."
            ),
            callback=finalize,
        )

        return task

    # ==========================================================
    # START DUNGEON LOAD
    # ==========================================================

    def _load_dungeon(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Ensure an old transient dungeon is gone.
        # ------------------------------------------------------

        if self.scenes.is_loaded(
            "Dungeon"
        ):
            if not self.scenes.is_active(
                "Dungeon"
            ):
                self.scenes.unload(
                    "Dungeon"
                )

        task = (
            self._create_dungeon_task()
        )

        self.scenes.begin_loading(
            "Dungeon",
            task,
            loading_scene="Loading",
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ------------------------------------------------------
        # Escape
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Start dungeon generation
        # ------------------------------------------------------

        if (
            self.scenes.active_scene_name
            == "Home"
            and self.input.action(
                "load_dungeon"
            ).pressed
        ):
            self._load_dungeon()

        super().update(
            delta_time
        )


if __name__ == "__main__":
    SceneLoadingExample().run()