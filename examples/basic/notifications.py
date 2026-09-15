from __future__ import annotations

from nexora import Game


class NotificationExample(Game):
    def __init__(self) -> None:
        super().__init__(
            title="Nexora - Notification Test",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

    def initialize(self) -> None:
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
            "escape",
            "ESCAPE",
        )

        # Direkt beim Start sichtbar.
        self.notifications.success(
            "NotificationCenter funktioniert.",
            title="Nexora",
            duration=5.0,
        )

        print("1 = Info")
        print("2 = Success")
        print("3 = Warning")
        print("4 = Error")
        print("ESC = Exit")

    def update(
        self,
        delta_time: float,
    ) -> None:
        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        if self.input.action(
            "notify_info"
        ).pressed:
            self.notifications.info(
                "Normale Information",
                title="Info",
                duration=3.0,
            )

        if self.input.action(
            "notify_success"
        ).pressed:
            self.notifications.success(
                "Aktion erfolgreich.",
                title="Success",
                duration=3.0,
            )

        if self.input.action(
            "notify_warning"
        ).pressed:
            self.notifications.warning(
                "Das ist eine Warnung.",
                title="Warning",
                duration=4.0,
            )

        if self.input.action(
            "notify_error"
        ).pressed:
            self.notifications.error(
                "Testfehler aufgetreten.",
                title="Error",
                duration=5.0,
            )

        super().update(
            delta_time
        )


if __name__ == "__main__":
    NotificationExample().run()