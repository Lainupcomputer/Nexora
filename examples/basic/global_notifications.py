from __future__ import annotations

from nexora import Game
from nexora.scene import Scene


class GlobalNotificationsExample(Game):
    """
    Demonstrates Nexora's global NotificationCenter.

    The NotificationCenter belongs to Game, not to an individual
    scene. Notifications therefore survive scene changes.

    Controls
    --------

    SPACE
        Switch between Menu and Game scene

    1
        Global info notification

    2
        Global success notification

    3
        Global warning notification

    4
        Global error notification

    S
        Manual save

    Q
        Quick save

    A
        Autosave

    L
        Load manual save

    K
        Quick load

    O
        Load latest autosave

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Global Notifications",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,

            # --------------------------------------------------
            # Save demo
            # --------------------------------------------------

            save_path="saves/global_notification_example",

            save_signing_key=(
                b"nexora-global-notification-example-"
                b"0123456789abcdef"
            ),

            quick_save_enabled=True,

            autosave_enabled=True,
            autosave_slots=3,
        )

        # ======================================================
        # Demo state
        # ======================================================

        self.demo_value = 0

        self.notification_number = 1

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
            "switch_scene",
            "SPACE",
        )

        self.input.bind(
            "notify_info",
            "1",
        )

        self.input.bind(
            "notify_success",
            "2",
        )

        self.input.bind(
            "notify_warning",
            "3",
        )

        self.input.bind(
            "notify_error",
            "4",
        )

        self.input.bind(
            "manual_save",
            "S",
        )

        self.input.bind(
            "quick_save",
            "Q",
        )

        self.input.bind(
            "auto_save",
            "A",
        )

        self.input.bind(
            "manual_load",
            "L",
        )

        self.input.bind(
            "quick_load",
            "K",
        )

        self.input.bind(
            "auto_load",
            "O",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scenes
        # ------------------------------------------------------

        menu_scene = Scene(
            "Menu"
        )

        game_scene = Scene(
            "Game"
        )

        self.scenes.load(
            menu_scene
        )

        self.scenes.load(
            game_scene
        )

        self.scenes.change_scene(
            "Menu"
        )

        # ------------------------------------------------------
        # Startup notification
        # ------------------------------------------------------

        self.notifications.success(
            "Global NotificationCenter is ready.",
            title="Nexora",
            duration=4.0,
        )

        self._print_controls()

    # ==========================================================
    # CONSOLE
    # ==========================================================

    def _print_controls(
        self,
    ) -> None:
        print()
        print("=" * 68)
        print(" Nexora Global Notifications + Save Events Example")
        print("=" * 68)
        print()
        print("SPACE   Switch Menu <-> Game")
        print()
        print("1       Info notification")
        print("2       Success notification")
        print("3       Warning notification")
        print("4       Error notification")
        print()
        print("S       Manual save")
        print("Q       Quick save")
        print("A       Autosave")
        print()
        print("L       Load manual save")
        print("K       Quick load")
        print("O       Load latest autosave")
        print()
        print("ESC     Exit")
        print()

    # ==========================================================
    # DEMO STATE
    # ==========================================================

    def _build_save_data(
        self,
    ) -> dict:
        """
        Temporary manual state generation.

        Later this will be replaced by Game.save_state().
        """

        return {
            "demo_value": (
                self.demo_value
            ),
            "scene": (
                self.scenes.active_scene_name
            ),
            "frame": (
                self.frame
            ),
        }

    def _apply_save_data(
        self,
        data: dict,
    ) -> None:
        """
        Temporary manual state restoration.

        Later this will be replaced by Game.load_state().
        """

        self.demo_value = int(
            data.get(
                "demo_value",
                0,
            )
        )

        scene_name = data.get(
            "scene"
        )

        if (
            isinstance(
                scene_name,
                str,
            )
            and self.scenes.get(
                scene_name
            )
            is not None
        ):
            self.scenes.change_scene(
                scene_name
            )

    # ==========================================================
    # SCENE SWITCHING
    # ==========================================================

    def _switch_scene(
        self,
    ) -> None:
        current = (
            self.scenes.active_scene_name
        )

        if current == "Menu":
            target = "Game"

        else:
            target = "Menu"

        # ------------------------------------------------------
        # Push notification BEFORE scene change.
        #
        # Because the NotificationCenter is global, this toast
        # continues to animate after the scene has changed.
        # ------------------------------------------------------

        self.notifications.info(
            f"{current} -> {target}",
            title="Scene Change",
            duration=4.0,
        )

        self.scenes.change_scene(
            target
        )

        print(
            f"Scene: {current} -> {target}"
        )

    # ==========================================================
    # TEST NOTIFICATIONS
    # ==========================================================

    def _next_notification_number(
        self,
    ) -> int:
        number = (
            self.notification_number
        )

        self.notification_number += 1

        return number

    def _show_info(
        self,
    ) -> None:
        number = (
            self._next_notification_number()
        )

        self.notifications.info(
            f"Global info #{number}",
            title="Information",
            duration=3.0,
        )

    def _show_success(
        self,
    ) -> None:
        number = (
            self._next_notification_number()
        )

        self.notifications.success(
            f"Global success #{number}",
            title="Success",
            duration=3.0,
        )

    def _show_warning(
        self,
    ) -> None:
        number = (
            self._next_notification_number()
        )

        self.notifications.warning(
            f"Global warning #{number}",
            title="Warning",
            duration=4.0,
        )

    def _show_error(
        self,
    ) -> None:
        number = (
            self._next_notification_number()
        )

        self.notifications.error(
            f"Global error #{number}",
            title="Error",
            duration=4.5,
        )

    # ==========================================================
    # MANUAL SAVE
    # ==========================================================

    def _manual_save(
        self,
    ) -> None:
        self.demo_value += 1

        print(
            "Manual save:",
            self.demo_value,
        )

        # ------------------------------------------------------
        # No explicit notification here.
        #
        # SaveNotificationHandler receives the SaveEvent and
        # creates the notification automatically.
        # ------------------------------------------------------

        self.saves.save(
            "demo",
            self._build_save_data(),
            name="Global Notification Demo",
            playtime=self.total_time,
        )

    # ==========================================================
    # QUICK SAVE
    # ==========================================================

    def _quick_save(
        self,
    ) -> None:
        self.demo_value += 1

        print(
            "Quick save:",
            self.demo_value,
        )

        self.saves.quick_save(
            self._build_save_data(),
            playtime=self.total_time,
        )

    # ==========================================================
    # AUTOSAVE
    # ==========================================================

    def _auto_save(
        self,
    ) -> None:
        self.demo_value += 1

        print(
            "Autosave:",
            self.demo_value,
        )

        self.saves.auto_save(
            self._build_save_data(),
            playtime=self.total_time,
        )

    # ==========================================================
    # MANUAL LOAD
    # ==========================================================

    def _manual_load(
        self,
    ) -> None:
        if not self.saves.exists(
            "demo"
        ):
            self.notifications.warning(
                "No manual save exists yet.",
                title="Load Game",
                duration=3.0,
            )

            return

        save = self.saves.load(
            "demo"
        )

        self._apply_save_data(
            save.data
        )

        print(
            "Manual load:",
            self.demo_value,
        )

    # ==========================================================
    # QUICK LOAD
    # ==========================================================

    def _quick_load(
        self,
    ) -> None:
        if not self.saves.has_quick_save():
            self.notifications.warning(
                "No quick save exists yet.",
                title="Quick Load",
                duration=3.0,
            )

            return

        save = (
            self.saves.quick_load()
        )

        self._apply_save_data(
            save.data
        )

        print(
            "Quick load:",
            self.demo_value,
        )

    # ==========================================================
    # AUTO LOAD
    # ==========================================================

    def _auto_load(
        self,
    ) -> None:
        if not self.saves.has_auto_save():
            self.notifications.warning(
                "No autosave exists yet.",
                title="Autosave",
                duration=3.0,
            )

            return

        save = (
            self.saves.load_latest_auto_save()
        )

        self._apply_save_data(
            save.data
        )

        print(
            "Autosave load:",
            self.demo_value,
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        if self.input.action(
            "switch_scene"
        ).pressed:
            self._switch_scene()

        # ------------------------------------------------------
        # Notifications
        # ------------------------------------------------------

        if self.input.action(
            "notify_info"
        ).pressed:
            self._show_info()

        if self.input.action(
            "notify_success"
        ).pressed:
            self._show_success()

        if self.input.action(
            "notify_warning"
        ).pressed:
            self._show_warning()

        if self.input.action(
            "notify_error"
        ).pressed:
            self._show_error()

        # ------------------------------------------------------
        # Save
        # ------------------------------------------------------

        if self.input.action(
            "manual_save"
        ).pressed:
            self._manual_save()

        if self.input.action(
            "quick_save"
        ).pressed:
            self._quick_save()

        if self.input.action(
            "auto_save"
        ).pressed:
            self._auto_save()

        # ------------------------------------------------------
        # Load
        # ------------------------------------------------------

        if self.input.action(
            "manual_load"
        ).pressed:
            self._manual_load()

        if self.input.action(
            "quick_load"
        ).pressed:
            self._quick_load()

        if self.input.action(
            "auto_load"
        ).pressed:
            self._auto_load()

        # ------------------------------------------------------
        # Normal scene + global overlay update
        # ------------------------------------------------------

        super().update(
            delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        active_scene = (
            self.scenes.active_scene_name
        )

        # ------------------------------------------------------
        # Draw visibly different backgrounds so scene changes
        # are obvious.
        # ------------------------------------------------------

        if active_scene == "Menu":
            self.renderer.rect(
                0.0,
                0.0,
                1280.0,
                720.0,
                color=(
                    0.08,
                    0.10,
                    0.16,
                    1.0,
                ),
            )

            self.renderer.rect(
                0.0,
                0.0,
                420.0,
                220.0,
                color=(
                    0.12,
                    0.25,
                    0.50,
                    1.0,
                ),
            )

        else:
            self.renderer.rect(
                0.0,
                0.0,
                1280.0,
                720.0,
                color=(
                    0.13,
                    0.08,
                    0.10,
                    1.0,
                ),
            )

            self.renderer.rect(
                0.0,
                0.0,
                420.0,
                220.0,
                color=(
                    0.50,
                    0.16,
                    0.20,
                    1.0,
                ),
            )

        # ------------------------------------------------------
        # IMPORTANT
        #
        # Game.render() renders:
        #
        #     scene stack
        #     active scene
        #     global NotificationCenter
        #
        # in that order.
        #
        # Therefore notifications are always on top.
        # ------------------------------------------------------

        super().render(
            interpolation
        )


if __name__ == "__main__":
    GlobalNotificationsExample().run()