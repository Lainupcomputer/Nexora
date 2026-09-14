from __future__ import annotations

from dataclasses import dataclass

import pytest

from nexora.save import (
    SaveEvent,
    SaveEventState,
    SaveKind,
    SaveNotificationHandler,
    SaveOperation,
)


# ==============================================================
# DUMMY NOTIFICATION CENTER
# ==============================================================


@dataclass
class NotificationCall:
    level: str
    text: str
    title: str | None
    duration: float


class DummyNotificationCenter:
    """
    Minimal NotificationCenter replacement for unit tests.

    No renderer, scene or GPU is required.
    """

    def __init__(
        self,
    ) -> None:
        self.calls: list[
            NotificationCall
        ] = []

    def info(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> None:
        self.calls.append(
            NotificationCall(
                level="info",
                text=text,
                title=title,
                duration=duration,
            )
        )

    def success(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> None:
        self.calls.append(
            NotificationCall(
                level="success",
                text=text,
                title=title,
                duration=duration,
            )
        )

    def warning(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> None:
        self.calls.append(
            NotificationCall(
                level="warning",
                text=text,
                title=title,
                duration=duration,
            )
        )

    def error(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> None:
        self.calls.append(
            NotificationCall(
                level="error",
                text=text,
                title=title,
                duration=duration,
            )
        )


# ==============================================================
# HELPERS
# ==============================================================


def make_event(
    *,
    operation: SaveOperation,
    kind: SaveKind,
    state: SaveEventState,
    slot: str = "slot_1",
    error: BaseException | None = None,
) -> SaveEvent:
    return SaveEvent(
        operation=operation,
        kind=kind,
        state=state,
        slot=slot,
        error=error,
    )


# ==============================================================
# DEFAULT STARTED BEHAVIOUR
# ==============================================================


def test_started_notifications_are_hidden_by_default() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.STARTED,
        )
    )

    assert center.calls == []


def test_started_notifications_can_be_enabled() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center,
        show_started=True,
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.STARTED,
        )
    )

    assert len(
        center.calls
    ) == 1

    call = center.calls[0]

    assert call.level == "info"
    assert call.text == "Saving game..."
    assert call.title == "Save Game"


# ==============================================================
# MANUAL SAVE
# ==============================================================


def test_manual_save_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.COMPLETED,
        )
    )

    assert len(
        center.calls
    ) == 1

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Game saved."
    assert call.title == "Save Game"


def test_manual_save_failed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.FAILED,
            error=OSError(
                "disk failure"
            ),
        )
    )

    assert len(
        center.calls
    ) == 1

    call = center.calls[0]

    assert call.level == "error"
    assert call.text == "Saving game failed."
    assert call.title == "Save Game"


# ==============================================================
# QUICK SAVE
# ==============================================================


def test_quick_save_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.QUICK,
            state=SaveEventState.COMPLETED,
            slot="quicksave",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Quick save created."
    assert call.title == "Quick Save"


def test_quick_save_failed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.QUICK,
            state=SaveEventState.FAILED,
            slot="quicksave",
            error=RuntimeError(
                "failure"
            ),
        )
    )

    call = center.calls[0]

    assert call.level == "error"
    assert call.text == "Quick save failed."
    assert call.title == "Quick Save"


# ==============================================================
# AUTOSAVE
# ==============================================================


def test_autosave_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.AUTO,
            state=SaveEventState.COMPLETED,
            slot="autosave_1",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Game autosaved."
    assert call.title == "Autosave"


def test_autosave_failed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.AUTO,
            state=SaveEventState.FAILED,
            slot="autosave_1",
            error=RuntimeError(
                "autosave failure"
            ),
        )
    )

    call = center.calls[0]

    assert call.level == "error"
    assert call.text == "Autosave failed."
    assert call.title == "Autosave"


# ==============================================================
# MANUAL LOAD
# ==============================================================


def test_manual_load_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.LOAD,
            kind=SaveKind.MANUAL,
            state=SaveEventState.COMPLETED,
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Game loaded."
    assert call.title == "Load Game"


def test_manual_load_failed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.LOAD,
            kind=SaveKind.MANUAL,
            state=SaveEventState.FAILED,
            error=RuntimeError(
                "load failure"
            ),
        )
    )

    call = center.calls[0]

    assert call.level == "error"
    assert call.text == "Loading game failed."
    assert call.title == "Load Game"


# ==============================================================
# QUICK LOAD
# ==============================================================


def test_quick_load_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.LOAD,
            kind=SaveKind.QUICK,
            state=SaveEventState.COMPLETED,
            slot="quicksave",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Quick save loaded."
    assert call.title == "Quick Load"


# ==============================================================
# AUTOSAVE LOAD
# ==============================================================


def test_autosave_load_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.LOAD,
            kind=SaveKind.AUTO,
            state=SaveEventState.COMPLETED,
            slot="autosave_1",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Autosave loaded."
    assert call.title == "Autosave"


# ==============================================================
# DELETE
# ==============================================================


def test_manual_delete_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.DELETE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.COMPLETED,
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Save deleted."
    assert call.title == "Save Game"


def test_quick_delete_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.DELETE,
            kind=SaveKind.QUICK,
            state=SaveEventState.COMPLETED,
            slot="quicksave",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Quick save deleted."


def test_autosave_delete_completed_notification() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center
    )

    handler(
        make_event(
            operation=SaveOperation.DELETE,
            kind=SaveKind.AUTO,
            state=SaveEventState.COMPLETED,
            slot="autosave_1",
        )
    )

    call = center.calls[0]

    assert call.level == "success"
    assert call.text == "Autosave deleted."


# ==============================================================
# DURATIONS
# ==============================================================


def test_custom_notification_durations() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center,
        show_started=True,
        started_duration=1.25,
        completed_duration=2.75,
        failed_duration=5.5,
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.STARTED,
        )
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.COMPLETED,
        )
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.FAILED,
            error=RuntimeError(),
        )
    )

    assert (
        center.calls[0].duration
        == pytest.approx(
            1.25
        )
    )

    assert (
        center.calls[1].duration
        == pytest.approx(
            2.75
        )
    )

    assert (
        center.calls[2].duration
        == pytest.approx(
            5.5
        )
    )


def test_negative_durations_are_clamped_to_zero() -> None:
    center = DummyNotificationCenter()

    handler = SaveNotificationHandler(
        center,
        show_started=True,
        started_duration=-10.0,
        completed_duration=-5.0,
        failed_duration=-1.0,
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.STARTED,
        )
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.COMPLETED,
        )
    )

    handler(
        make_event(
            operation=SaveOperation.SAVE,
            kind=SaveKind.MANUAL,
            state=SaveEventState.FAILED,
        )
    )

    assert (
        center.calls[0].duration
        == 0.0
    )

    assert (
        center.calls[1].duration
        == 0.0
    )

    assert (
        center.calls[2].duration
        == 0.0
    )