from __future__ import annotations

from nexora import Game
from nexora.nodes import (
    NotificationAnchor,
    NotificationCenter,
)
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene


class NotificationCenterExample(Game):
    """
    Nexora NotificationCenter example.

    Controls
    --------
    1
        Info notification

    2
        Success notification

    3
        Warning notification

    4
        Error notification

    5
        Push several notifications

    D
        Dismiss latest notification

    C
        Clear all notifications immediately

    F1
        Top left

    F2
        Top center

    F3
        Top right

    F4
        Bottom left

    F5
        Bottom center

    F6
        Bottom right

    S
        Toggle slide animation

    A
        Toggle fade animation

    P
        Toggle progress bar

    ESC
        Exit
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Notification Center Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        # ======================================================
        # World
        # ======================================================

        self.world_width = 2400.0
        self.world_height = 1600.0

        # ======================================================
        # Texture
        # ======================================================

        self.texture: GPUTexture | None = None

        self.sprite_width = 96.0
        self.sprite_height = 96.0

        # ======================================================
        # Demo world
        # ======================================================

        self.objects: list[
            tuple[
                float,
                float,
                float,
            ]
        ] = []

        # ======================================================
        # Notifications
        # ======================================================

        self.notifications: (
            NotificationCenter | None
        ) = None

        self.latest_notification_id: (
            int | None
        ) = None

        self.notification_counter: int = 1

    # ==========================================================
    # Initialize
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input.bind(
            "info",
            "1",
        )

        self.input.bind(
            "success",
            "2",
        )

        self.input.bind(
            "warning",
            "3",
        )

        self.input.bind(
            "error",
            "4",
        )

        self.input.bind(
            "multiple",
            "5",
        )

        self.input.bind(
            "dismiss",
            "D",
        )

        self.input.bind(
            "clear",
            "C",
        )

        self.input.bind(
            "anchor_top_left",
            "F1",
        )

        self.input.bind(
            "anchor_top_center",
            "F2",
        )

        self.input.bind(
            "anchor_top_right",
            "F3",
        )

        self.input.bind(
            "anchor_bottom_left",
            "F4",
        )

        self.input.bind(
            "anchor_bottom_center",
            "F5",
        )

        self.input.bind(
            "anchor_bottom_right",
            "F6",
        )

        self.input.bind(
            "toggle_slide",
            "S",
        )

        self.input.bind(
            "toggle_fade",
            "A",
        )

        self.input.bind(
            "toggle_progress",
            "P",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "NotificationCenterExample"
        )

        self.scene = scene

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        print(
            r"Loading: assets\demo_sprite.png"
        )

        image = self.assets.load_texture(
            "demo_sprite.png"
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        self.sprite_width = float(
            image.width
        )

        self.sprite_height = float(
            image.height
        )

        # ------------------------------------------------------
        # World
        # ------------------------------------------------------

        self._create_world_objects()

        # ------------------------------------------------------
        # Camera
        # ------------------------------------------------------

        self.renderer.camera.set_position(
            self.world_width * 0.5,
            self.world_height * 0.5,
        )

        self.renderer.camera.set_zoom(
            1.0
        )

        # ------------------------------------------------------
        # Notification center
        # ------------------------------------------------------

        self.notifications = NotificationCenter(
            "Notifications",
            scene.world,
            self.renderer,
        )

        self.notifications.anchor = (
            NotificationAnchor.TOP_RIGHT
        )

        self.notifications.max_visible = 5

        self.notifications.width = 360.0
        self.notifications.height = 92.0

        self.notifications.margin = 24.0
        self.notifications.spacing = 12.0

        self.notifications.enter_duration = 0.35
        self.notifications.exit_duration = 0.30

        self.notifications.slide_enabled = True
        self.notifications.fade_enabled = True

        self.notifications.show_progress = True

        scene.add_node(
            self.notifications
        )

        # ------------------------------------------------------
        # Startup notification
        # ------------------------------------------------------

        self.notifications.success(
            "NotificationCenter ist bereit.",
            title="Nexora",
            duration=3.5,
        )

        # ------------------------------------------------------
        # Console info
        # ------------------------------------------------------

        self._print_controls()

    # ==========================================================
    # Demo world
    # ==========================================================

    def _create_world_objects(
        self,
    ) -> None:
        spacing = 200.0

        columns = int(
            self.world_width
            // spacing
        )

        rows = int(
            self.world_height
            // spacing
        )

        for y in range(
            rows + 1
        ):
            for x in range(
                columns + 1
            ):
                world_x = (
                    x * spacing
                )

                world_y = (
                    y * spacing
                )

                rotation = (
                    (x + y)
                    * 0.08
                )

                self.objects.append(
                    (
                        world_x,
                        world_y,
                        rotation,
                    )
                )

    # ==========================================================
    # Console
    # ==========================================================

    def _print_controls(
        self,
    ) -> None:
        print()
        print("=" * 62)
        print(" Nexora NotificationCenter Example")
        print("=" * 62)
        print()
        print("1    Info notification")
        print("2    Success notification")
        print("3    Warning notification")
        print("4    Error notification")
        print("5    Push multiple notifications")
        print()
        print("D    Dismiss latest notification")
        print("C    Clear all immediately")
        print()
        print("F1   Top left")
        print("F2   Top center")
        print("F3   Top right")
        print("F4   Bottom left")
        print("F5   Bottom center")
        print("F6   Bottom right")
        print()
        print("S    Toggle slide")
        print("A    Toggle fade")
        print("P    Toggle progress bar")
        print()
        print("ESC  Exit")
        print()

    # ==========================================================
    # Notifications
    # ==========================================================

    def _next_number(
        self,
    ) -> int:
        number = (
            self.notification_counter
        )

        self.notification_counter += 1

        return number

    def _push_info(
        self,
    ) -> None:
        if self.notifications is None:
            return

        number = self._next_number()

        self.latest_notification_id = (
            self.notifications.info(
                f"Dies ist Info #{number}.",
                title="Information",
                duration=3.0,
            )
        )

    def _push_success(
        self,
    ) -> None:
        if self.notifications is None:
            return

        number = self._next_number()

        self.latest_notification_id = (
            self.notifications.success(
                f"Aktion #{number} erfolgreich abgeschlossen.",
                title="Erfolg",
                duration=3.5,
            )
        )

    def _push_warning(
        self,
    ) -> None:
        if self.notifications is None:
            return

        number = self._next_number()

        self.latest_notification_id = (
            self.notifications.warning(
                f"Warnung #{number}: Bitte überprüfen.",
                title="Warnung",
                duration=4.0,
            )
        )

    def _push_error(
        self,
    ) -> None:
        if self.notifications is None:
            return

        number = self._next_number()

        self.latest_notification_id = (
            self.notifications.error(
                f"Fehler #{number} ist aufgetreten.",
                title="Fehler",
                duration=4.5,
            )
        )

    def _push_multiple(
        self,
    ) -> None:
        if self.notifications is None:
            return

        self.notifications.info(
            "Neuer Gegenstand aufgenommen.",
            title="Inventar",
            duration=4.0,
        )

        self.notifications.success(
            "Spielstand gespeichert.",
            title="Gespeichert",
            duration=4.0,
        )

        self.notifications.warning(
            "Inventar fast voll.",
            title="Inventar",
            duration=4.0,
        )

        self.notifications.error(
            "Verbindung unterbrochen.",
            title="Netzwerk",
            duration=4.0,
        )

        self.latest_notification_id = (
            self.notifications.info(
                "Quest wurde aktualisiert.",
                title="Quest",
                duration=4.0,
            )
        )

    # ==========================================================
    # Anchor
    # ==========================================================

    def _set_anchor(
        self,
        anchor: NotificationAnchor,
    ) -> None:
        if self.notifications is None:
            return

        self.notifications.anchor = anchor

        print(
            "Anchor:",
            anchor.value,
        )

        self.notifications.info(
            f"Anchor: {anchor.value}",
            duration=2.0,
        )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        notifications = (
            self.notifications
        )

        if notifications is None:
            return

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Notification types
        # ------------------------------------------------------

        if self.input.action(
            "info"
        ).pressed:
            self._push_info()

        if self.input.action(
            "success"
        ).pressed:
            self._push_success()

        if self.input.action(
            "warning"
        ).pressed:
            self._push_warning()

        if self.input.action(
            "error"
        ).pressed:
            self._push_error()

        if self.input.action(
            "multiple"
        ).pressed:
            self._push_multiple()

        # ------------------------------------------------------
        # Dismiss
        # ------------------------------------------------------

        if self.input.action(
            "dismiss"
        ).pressed:
            if (
                self.latest_notification_id
                is not None
            ):
                found = notifications.dismiss(
                    self.latest_notification_id
                )

                print(
                    "Dismiss:",
                    self.latest_notification_id,
                    found,
                )

        # ------------------------------------------------------
        # Clear
        # ------------------------------------------------------

        if self.input.action(
            "clear"
        ).pressed:
            notifications.clear()

            self.latest_notification_id = None

            print(
                "Notifications cleared."
            )

        # ------------------------------------------------------
        # Anchor
        # ------------------------------------------------------

        if self.input.action(
            "anchor_top_left"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.TOP_LEFT
            )

        if self.input.action(
            "anchor_top_center"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.TOP_CENTER
            )

        if self.input.action(
            "anchor_top_right"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.TOP_RIGHT
            )

        if self.input.action(
            "anchor_bottom_left"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.BOTTOM_LEFT
            )

        if self.input.action(
            "anchor_bottom_center"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.BOTTOM_CENTER
            )

        if self.input.action(
            "anchor_bottom_right"
        ).pressed:
            self._set_anchor(
                NotificationAnchor.BOTTOM_RIGHT
            )

        # ------------------------------------------------------
        # Slide
        # ------------------------------------------------------

        if self.input.action(
            "toggle_slide"
        ).pressed:
            notifications.slide_enabled = (
                not notifications.slide_enabled
            )

            print(
                "Slide:",
                notifications.slide_enabled,
            )

        # ------------------------------------------------------
        # Fade
        # ------------------------------------------------------

        if self.input.action(
            "toggle_fade"
        ).pressed:
            notifications.fade_enabled = (
                not notifications.fade_enabled
            )

            print(
                "Fade:",
                notifications.fade_enabled,
            )

        # ------------------------------------------------------
        # Progress
        # ------------------------------------------------------

        if self.input.action(
            "toggle_progress"
        ).pressed:
            notifications.show_progress = (
                not notifications.show_progress
            )

            print(
                "Progress:",
                notifications.show_progress,
            )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        super().update(
            delta_time
        )

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        if self.texture is None:
            return

        center_x = (
            self.world_width
            * 0.5
        )

        center_y = (
            self.world_height
            * 0.5
        )

        # ------------------------------------------------------
        # World grid
        # ------------------------------------------------------

        for (
            x,
            y,
            rotation,
        ) in self.objects:
            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=self.sprite_width,
                height=self.sprite_height,
                rotation=rotation,
            )

        # ------------------------------------------------------
        # Center sprite
        # ------------------------------------------------------

        self.renderer.sprite(
            self.texture,
            center_x,
            center_y,
            width=280.0,
            height=280.0,
            rotation=0.0,
        )

        # ------------------------------------------------------
        # Colored reference objects
        # ------------------------------------------------------

        self.renderer.rect(
            center_x - 350.0,
            center_y + 270.0,
            220.0,
            100.0,
            color=(
                0.15,
                0.55,
                1.0,
                1.0,
            ),
        )

        self.renderer.rect(
            center_x,
            center_y + 270.0,
            220.0,
            100.0,
            color=(
                0.2,
                0.8,
                0.4,
                1.0,
            ),
        )

        self.renderer.rect(
            center_x + 350.0,
            center_y + 270.0,
            220.0,
            100.0,
            color=(
                1.0,
                0.7,
                0.15,
                1.0,
            ),
        )

        # ------------------------------------------------------
        # Scene
        #
        # NotificationCenter is a scene node and is rendered by
        # the scene tree after the world objects.
        # ------------------------------------------------------

        super().render(
            interpolation
        )

    # ==========================================================
    # Shutdown
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        if self.texture is not None:
            self.texture.destroy()

            self.texture = None

        super().shutdown()


if __name__ == "__main__":
    NotificationCenterExample().run()