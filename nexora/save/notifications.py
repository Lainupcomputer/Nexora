from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.save.events import (
    SaveEvent,
    SaveEventState,
    SaveKind,
    SaveOperation,
)


if TYPE_CHECKING:
    from nexora.nodes import NotificationCenter


class SaveNotificationHandler:
    """
    Bridge between SaveManager events and NotificationCenter.

    The SaveManager itself stays completely UI-independent.

    Example
    -------

        handler = SaveNotificationHandler(
            notifications
        )

        game.saves.add_listener(
            handler
        )

    By default STARTED events are not displayed because normal
    saves are usually fast enough that showing:

        Saving...
        Saved.

    would create unnecessary notification spam.

    STARTED notifications can still be enabled for asynchronous
    or slower save operations.
    """

    def __init__(
        self,
        notification_center: NotificationCenter,
        *,
        show_started: bool = False,
        started_duration: float = 1.5,
        completed_duration: float = 2.5,
        failed_duration: float = 4.0,
    ) -> None:
        self.notification_center = (
            notification_center
        )

        self.show_started = bool(
            show_started
        )

        self.started_duration = max(
            0.0,
            float(
                started_duration
            ),
        )

        self.completed_duration = max(
            0.0,
            float(
                completed_duration
            ),
        )

        self.failed_duration = max(
            0.0,
            float(
                failed_duration
            ),
        )

    # ==========================================================
    # EVENT ENTRY
    # ==========================================================

    def __call__(
        self,
        event: SaveEvent,
    ) -> None:
        """
        Handle one SaveManager event.
        """

        if (
            event.state
            == SaveEventState.STARTED
        ):
            self._handle_started(
                event
            )

            return

        if (
            event.state
            == SaveEventState.COMPLETED
        ):
            self._handle_completed(
                event
            )

            return

        if (
            event.state
            == SaveEventState.FAILED
        ):
            self._handle_failed(
                event
            )

    # ==========================================================
    # STARTED
    # ==========================================================

    def _handle_started(
        self,
        event: SaveEvent,
    ) -> None:
        if not self.show_started:
            return

        text = (
            self._started_message(
                event
            )
        )

        if text is None:
            return

        self.notification_center.info(
            text,
            title=self._title(
                event
            ),
            duration=(
                self.started_duration
            ),
        )

    # ==========================================================
    # COMPLETED
    # ==========================================================

    def _handle_completed(
        self,
        event: SaveEvent,
    ) -> None:
        text = (
            self._completed_message(
                event
            )
        )

        if text is None:
            return

        self.notification_center.success(
            text,
            title=self._title(
                event
            ),
            duration=(
                self.completed_duration
            ),
        )

    # ==========================================================
    # FAILED
    # ==========================================================

    def _handle_failed(
        self,
        event: SaveEvent,
    ) -> None:
        text = (
            self._failed_message(
                event
            )
        )

        if text is None:
            return

        self.notification_center.error(
            text,
            title=self._title(
                event
            ),
            duration=(
                self.failed_duration
            ),
        )

    # ==========================================================
    # TITLE
    # ==========================================================

    @staticmethod
    def _title(
        event: SaveEvent,
    ) -> str:
        if (
            event.operation
            == SaveOperation.SAVE
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick Save"

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosave"

            return "Save Game"

        if (
            event.operation
            == SaveOperation.LOAD
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick Load"

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosave"

            return "Load Game"

        if (
            event.operation
            == SaveOperation.DELETE
        ):
            return "Save Game"

        return "Save System"

    # ==========================================================
    # STARTED MESSAGE
    # ==========================================================

    @staticmethod
    def _started_message(
        event: SaveEvent,
    ) -> str | None:
        if (
            event.operation
            == SaveOperation.SAVE
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Creating quick save..."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosaving..."

            return "Saving game..."

        if (
            event.operation
            == SaveOperation.LOAD
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Loading quick save..."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Loading autosave..."

            return "Loading game..."

        if (
            event.operation
            == SaveOperation.DELETE
        ):
            return "Deleting save..."

        return None

    # ==========================================================
    # COMPLETED MESSAGE
    # ==========================================================

    @staticmethod
    def _completed_message(
        event: SaveEvent,
    ) -> str | None:
        if (
            event.operation
            == SaveOperation.SAVE
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick save created."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Game autosaved."

            return "Game saved."

        if (
            event.operation
            == SaveOperation.LOAD
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick save loaded."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosave loaded."

            return "Game loaded."

        if (
            event.operation
            == SaveOperation.DELETE
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick save deleted."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosave deleted."

            return "Save deleted."

        return None

    # ==========================================================
    # FAILED MESSAGE
    # ==========================================================

    @staticmethod
    def _failed_message(
        event: SaveEvent,
    ) -> str | None:
        if (
            event.operation
            == SaveOperation.SAVE
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Quick save failed."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Autosave failed."

            return "Saving game failed."

        if (
            event.operation
            == SaveOperation.LOAD
        ):
            if (
                event.kind
                == SaveKind.QUICK
            ):
                return "Loading quick save failed."

            if (
                event.kind
                == SaveKind.AUTO
            ):
                return "Loading autosave failed."

            return "Loading game failed."

        if (
            event.operation
            == SaveOperation.DELETE
        ):
            return "Deleting save failed."

        return None