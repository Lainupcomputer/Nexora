from __future__ import annotations

import os
import pickle

import pytest

from nexora.save import (
    SaveIntegrityError,
    SaveManager,
    SaveNotFoundError,
    UnsafeSaveDataError,
)

from nexora.save.codec import (
    restricted_loads,
)


TEST_KEY = (
    b"nexora-test-save-signing-key-"
    b"0123456789abcdef"
)


@pytest.fixture
def manager(
    tmp_path,
) -> SaveManager:
    return SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
    )


# ==============================================================
# SAVE / LOAD
# ==============================================================


def test_save_and_load(
    manager: SaveManager,
) -> None:
    data = {
        "player": {
            "health": 85,
            "position": (
                120.5,
                44.0,
            ),
        },
        "day": 4,
    }

    metadata = manager.save(
        "slot_1",
        data,
        name="Test Save",
        playtime=123.5,
    )

    assert (
        metadata.slot
        == "slot_1"
    )

    loaded = manager.load(
        "slot_1"
    )

    assert (
        loaded.data
        == data
    )

    assert (
        loaded.metadata.name
        == "Test Save"
    )

    assert (
        loaded.metadata.playtime
        == pytest.approx(
            123.5
        )
    )


# ==============================================================
# EXISTS
# ==============================================================


def test_exists(
    manager: SaveManager,
) -> None:
    assert (
        manager.exists(
            "slot_1"
        )
        is False
    )

    manager.save(
        "slot_1",
        {},
    )

    assert (
        manager.exists(
            "slot_1"
        )
        is True
    )


# ==============================================================
# DELETE
# ==============================================================


def test_delete(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {},
    )

    assert (
        manager.delete(
            "slot_1"
        )
        is True
    )

    assert (
        manager.exists(
            "slot_1"
        )
        is False
    )

    assert (
        manager.delete(
            "slot_1"
        )
        is False
    )


# ==============================================================
# LIST
# ==============================================================


def test_list_slots(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_2",
        {},
    )

    manager.save(
        "slot_1",
        {},
    )

    assert (
        manager.list_slots()
        == (
            "slot_1",
            "slot_2",
        )
    )


# ==============================================================
# MISSING
# ==============================================================


def test_missing_save(
    manager: SaveManager,
) -> None:
    with pytest.raises(
        SaveNotFoundError
    ):
        manager.load(
            "missing"
        )


# ==============================================================
# CUSTOM SAVE PATH
# ==============================================================


def test_change_save_path(
    manager: SaveManager,
    tmp_path,
) -> None:
    new_path = (
        tmp_path
        / "different"
        / "save"
        / "directory"
    )

    manager.save_path = (
        new_path
    )

    manager.save(
        "slot_1",
        {
            "value": 42,
        },
    )

    assert (
        new_path
        / "slot_1.nxs"
    ).is_file()


# ==============================================================
# PATH TRAVERSAL
# ==============================================================


@pytest.mark.parametrize(
    "slot",
    [
        "../evil",
        "..",
        "folder/save",
        "folder\\save",
        "slot.exe",
        "",
        " ",
    ],
)
def test_invalid_slot_name(
    manager: SaveManager,
    slot: str,
) -> None:
    with pytest.raises(
        ValueError
    ):
        manager.save(
            slot,
            {},
        )


# ==============================================================
# UNSAFE TYPES
# ==============================================================


class UnsafeObject:
    pass


def test_unsafe_object_is_rejected(
    manager: SaveManager,
) -> None:
    with pytest.raises(
        UnsafeSaveDataError
    ):
        manager.save(
            "slot_1",
            {
                "object": (
                    UnsafeObject()
                )
            },
        )


# ==============================================================
# TAMPERING
# ==============================================================


def test_modified_file_fails_integrity(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {
            "money": 100,
        },
    )

    path = manager.slot_path(
        "slot_1"
    )

    raw = bytearray(
        path.read_bytes()
    )

    raw[-1] ^= 0x01

    path.write_bytes(
        raw
    )

    with pytest.raises(
        SaveIntegrityError
    ):
        manager.load(
            "slot_1"
        )


# ==============================================================
# WRONG KEY
# ==============================================================


def test_wrong_signing_key_fails(
    manager: SaveManager,
    tmp_path,
) -> None:
    manager.save(
        "slot_1",
        {
            "value": 123,
        },
    )

    other_manager = SaveManager(
        tmp_path,
        signing_key=(
            b"completely-different-testing-key-"
            b"abcdefghijklmnop"
        ),
    )

    with pytest.raises(
        SaveIntegrityError
    ):
        other_manager.load(
            "slot_1"
        )


# ==============================================================
# RESTRICTED PICKLE
# ==============================================================


class MaliciousPickle:
    def __reduce__(
        self,
    ):
        return (
            os.system,
            (
                "echo THIS_MUST_NEVER_EXECUTE",
            ),
        )


def test_restricted_unpickler_blocks_reduce() -> None:
    payload = pickle.dumps(
        MaliciousPickle(),
        protocol=pickle.HIGHEST_PROTOCOL,
    )

    with pytest.raises(
        UnsafeSaveDataError
    ):
        restricted_loads(
            payload
        )


# ==============================================================
# PRIMITIVES
# ==============================================================


def test_supported_safe_types(
    manager: SaveManager,
) -> None:
    data = {
        "none": None,
        "bool": True,
        "int": 123,
        "float": 4.5,
        "str": "hello",
        "bytes": b"abc",
        "list": [
            1,
            2,
            3,
        ],
        "tuple": (
            4,
            5,
        ),
        "dict": {
            "nested": True,
        },
    }

    manager.save(
        "slot",
        data,
    )

    loaded = manager.load(
        "slot"
    )

    assert (
        loaded.data
        == data
    )


# ==============================================================
# ATOMIC OVERWRITE
# ==============================================================


def test_overwrite_slot(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {
            "value": 1,
        },
    )

    manager.save(
        "slot_1",
        {
            "value": 2,
        },
    )

    result = manager.load(
        "slot_1"
    )

    assert (
        result.data[
            "value"
        ]
        == 2
    )

# ==============================================================
# QUICK SAVE
# ==============================================================


def test_quick_save_and_load(
    manager: SaveManager,
) -> None:
    data = {
        "player": {
            "health": 50,
        },
    }

    metadata = manager.quick_save(
        data,
        playtime=12.5,
    )

    assert (
        metadata.slot
        == "quicksave"
    )

    assert (
        manager.has_quick_save()
        is True
    )

    loaded = (
        manager.quick_load()
    )

    assert (
        loaded.data
        == data
    )

    assert (
        loaded.metadata.name
        == "Quick Save"
    )

    assert (
        loaded.metadata.playtime
        == pytest.approx(
            12.5
        )
    )


def test_quick_save_can_use_custom_name(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 123,
        },
        name="Before Boss",
    )

    loaded = (
        manager.quick_load()
    )

    assert (
        loaded.metadata.name
        == "Before Boss"
    )


def test_quick_save_can_be_disabled(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        quick_save_enabled=False,
    )

    assert (
        manager.quick_save_enabled
        is False
    )

    with pytest.raises(
        RuntimeError,
        match="Quick saving is disabled",
    ):
        manager.quick_save(
            {
                "value": 1,
            }
        )


def test_quick_load_is_disabled_with_quick_save(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
    )

    manager.quick_save(
        {
            "value": 123,
        }
    )

    manager.quick_save_enabled = (
        False
    )

    assert (
        manager.has_quick_save()
        is False
    )

    with pytest.raises(
        RuntimeError,
        match="Quick saving is disabled",
    ):
        manager.quick_load()


def test_quick_save_can_be_enabled_again(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        quick_save_enabled=False,
    )

    manager.quick_save_enabled = (
        True
    )

    manager.quick_save(
        {
            "value": 999,
        }
    )

    loaded = (
        manager.quick_load()
    )

    assert (
        loaded.data[
            "value"
        ]
        == 999
    )


def test_custom_quick_save_slot(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        quick_save_slot=(
            "fast_slot"
        ),
    )

    assert (
        manager.quick_save_slot
        == "fast_slot"
    )

    manager.quick_save(
        {
            "value": 42,
        }
    )

    assert (
        manager.exists(
            "fast_slot"
        )
        is True
    )

    assert (
        manager.slot_path(
            "fast_slot"
        ).is_file()
    )


def test_quick_save_slot_can_change(
    manager: SaveManager,
) -> None:
    manager.quick_save_slot = (
        "manual_quick"
    )

    assert (
        manager.quick_save_slot
        == "manual_quick"
    )

    manager.quick_save(
        {
            "value": 42,
        }
    )

    assert (
        manager.exists(
            "manual_quick"
        )
        is True
    )


def test_invalid_quick_save_slot_is_rejected(
    manager: SaveManager,
) -> None:
    with pytest.raises(
        ValueError
    ):
        manager.quick_save_slot = (
            "../quicksave"
        )


def test_delete_quick_save(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 1,
        }
    )

    assert (
        manager.has_quick_save()
        is True
    )

    assert (
        manager.delete_quick_save()
        is True
    )

    assert (
        manager.has_quick_save()
        is False
    )


def test_delete_quick_save_when_missing(
    manager: SaveManager,
) -> None:
    assert (
        manager.delete_quick_save()
        is False
    )


def test_quick_save_can_be_deleted_while_disabled(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 1,
        }
    )

    quick_path = (
        manager.slot_path(
            manager.quick_save_slot
        )
    )

    assert (
        quick_path.is_file()
    )

    manager.quick_save_enabled = (
        False
    )

    # has_quick_save intentionally reports False while
    # the feature is disabled.
    assert (
        manager.has_quick_save()
        is False
    )

    # The physical quick-save file can still be removed.
    assert (
        manager.delete_quick_save()
        is True
    )

    assert (
        quick_path.exists()
        is False
    )


def test_quick_save_overwrites_previous_quick_save(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 1,
        }
    )

    manager.quick_save(
        {
            "value": 2,
        }
    )

    loaded = (
        manager.quick_load()
    )

    assert (
        loaded.data[
            "value"
        ]
        == 2
    )

# ==============================================================
# SAVE EVENTS
# ==============================================================


from nexora.save import (
    SaveEventState,
    SaveKind,
    SaveOperation,
)


def test_manual_save_emits_started_and_completed(
    manager: SaveManager,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    metadata = manager.save(
        "slot_1",
        {
            "value": 123,
        },
        name="Manual Save",
    )

    assert len(
        events
    ) == 2

    started = events[0]
    completed = events[1]

    assert (
        started.operation
        == SaveOperation.SAVE
    )

    assert (
        started.kind
        == SaveKind.MANUAL
    )

    assert (
        started.state
        == SaveEventState.STARTED
    )

    assert (
        started.slot
        == "slot_1"
    )

    assert (
        started.metadata
        is None
    )

    assert (
        started.error
        is None
    )

    assert (
        completed.operation
        == SaveOperation.SAVE
    )

    assert (
        completed.kind
        == SaveKind.MANUAL
    )

    assert (
        completed.state
        == SaveEventState.COMPLETED
    )

    assert (
        completed.slot
        == "slot_1"
    )

    assert (
        completed.metadata
        is metadata
    )

    assert (
        completed.error
        is None
    )


def test_manual_load_emits_started_and_completed(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {
            "value": 42,
        },
    )

    events = []

    manager.add_listener(
        events.append
    )

    loaded = manager.load(
        "slot_1"
    )

    assert len(
        events
    ) == 2

    assert (
        events[0].operation
        == SaveOperation.LOAD
    )

    assert (
        events[0].kind
        == SaveKind.MANUAL
    )

    assert (
        events[0].state
        == SaveEventState.STARTED
    )

    assert (
        events[1].operation
        == SaveOperation.LOAD
    )

    assert (
        events[1].kind
        == SaveKind.MANUAL
    )

    assert (
        events[1].state
        == SaveEventState.COMPLETED
    )

    assert (
        events[1].metadata
        == loaded.metadata
    )


def test_quick_save_emits_quick_kind(
    manager: SaveManager,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    manager.quick_save(
        {
            "value": 1,
        }
    )

    assert len(
        events
    ) == 2

    assert (
        events[0].kind
        == SaveKind.QUICK
    )

    assert (
        events[1].kind
        == SaveKind.QUICK
    )

    assert (
        events[0].operation
        == SaveOperation.SAVE
    )

    assert (
        events[1].operation
        == SaveOperation.SAVE
    )


def test_quick_load_emits_quick_kind(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 2,
        }
    )

    events = []

    manager.add_listener(
        events.append
    )

    manager.quick_load()

    assert len(
        events
    ) == 2

    assert (
        events[0].kind
        == SaveKind.QUICK
    )

    assert (
        events[1].kind
        == SaveKind.QUICK
    )

    assert (
        events[0].operation
        == SaveOperation.LOAD
    )

    assert (
        events[1].operation
        == SaveOperation.LOAD
    )


def test_autosave_emits_auto_kind(
    manager: SaveManager,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    manager.auto_save(
        {
            "value": 3,
        }
    )

    assert len(
        events
    ) == 2

    assert (
        events[0].kind
        == SaveKind.AUTO
    )

    assert (
        events[1].kind
        == SaveKind.AUTO
    )

    assert (
        events[0].slot
        == "autosave_1"
    )

    assert (
        events[1].slot
        == "autosave_1"
    )


def test_autosave_load_emits_auto_kind(
    manager: SaveManager,
) -> None:
    manager.auto_save(
        {
            "value": 4,
        }
    )

    events = []

    manager.add_listener(
        events.append
    )

    manager.load_latest_auto_save()

    assert len(
        events
    ) == 2

    assert (
        events[0].kind
        == SaveKind.AUTO
    )

    assert (
        events[1].kind
        == SaveKind.AUTO
    )

    assert (
        events[0].operation
        == SaveOperation.LOAD
    )

    assert (
        events[1].operation
        == SaveOperation.LOAD
    )


def test_failed_load_emits_started_and_failed(
    manager: SaveManager,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    with pytest.raises(
        SaveNotFoundError
    ):
        manager.load(
            "missing"
        )

    assert len(
        events
    ) == 2

    started = events[0]
    failed = events[1]

    assert (
        started.state
        == SaveEventState.STARTED
    )

    assert (
        failed.state
        == SaveEventState.FAILED
    )

    assert (
        failed.operation
        == SaveOperation.LOAD
    )

    assert (
        failed.kind
        == SaveKind.MANUAL
    )

    assert isinstance(
        failed.error,
        SaveNotFoundError,
    )

    assert (
        failed.metadata
        is None
    )


def test_failed_save_emits_started_and_failed(
    manager: SaveManager,
    monkeypatch,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    def fail_write(
        destination,
        data,
    ):
        raise OSError(
            "simulated write failure"
        )

    monkeypatch.setattr(
        manager,
        "_atomic_write",
        fail_write,
    )

    with pytest.raises(
        OSError,
        match="simulated write failure",
    ):
        manager.save(
            "slot_1",
            {
                "value": 5,
            },
        )

    assert len(
        events
    ) == 2

    assert (
        events[0].state
        == SaveEventState.STARTED
    )

    assert (
        events[1].state
        == SaveEventState.FAILED
    )

    assert (
        events[1].operation
        == SaveOperation.SAVE
    )

    assert isinstance(
        events[1].error,
        OSError,
    )


def test_delete_emits_started_and_completed(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {
            "value": 1,
        },
    )

    events = []

    manager.add_listener(
        events.append
    )

    assert (
        manager.delete(
            "slot_1"
        )
        is True
    )

    assert len(
        events
    ) == 2

    assert (
        events[0].operation
        == SaveOperation.DELETE
    )

    assert (
        events[0].state
        == SaveEventState.STARTED
    )

    assert (
        events[1].operation
        == SaveOperation.DELETE
    )

    assert (
        events[1].state
        == SaveEventState.COMPLETED
    )

    assert (
        events[0].kind
        == SaveKind.MANUAL
    )


def test_quick_delete_emits_quick_kind(
    manager: SaveManager,
) -> None:
    manager.quick_save(
        {
            "value": 1,
        }
    )

    events = []

    manager.add_listener(
        events.append
    )

    manager.delete_quick_save()

    assert len(
        events
    ) == 2

    assert (
        events[0].kind
        == SaveKind.QUICK
    )

    assert (
        events[1].kind
        == SaveKind.QUICK
    )

    assert (
        events[0].operation
        == SaveOperation.DELETE
    )


def test_delete_missing_slot_emits_no_event(
    manager: SaveManager,
) -> None:
    events = []

    manager.add_listener(
        events.append
    )

    result = manager.delete(
        "missing"
    )

    assert (
        result
        is False
    )

    assert (
        events
        == []
    )


def test_listener_can_be_removed(
    manager: SaveManager,
) -> None:
    events = []

    listener = events.append

    manager.add_listener(
        listener
    )

    assert (
        manager.remove_listener(
            listener
        )
        is True
    )

    manager.save(
        "slot_1",
        {}
    )

    assert (
        events
        == []
    )


def test_remove_unknown_listener_returns_false(
    manager: SaveManager,
) -> None:
    def listener(
        event,
    ):
        pass

    assert (
        manager.remove_listener(
            listener
        )
        is False
    )


def test_duplicate_listener_is_not_registered_twice(
    manager: SaveManager,
) -> None:
    events = []

    listener = events.append

    manager.add_listener(
        listener
    )

    manager.add_listener(
        listener
    )

    assert len(
        manager.listeners
    ) == 1

    manager.save(
        "slot_1",
        {}
    )

    assert len(
        events
    ) == 2


def test_clear_listeners(
    manager: SaveManager,
) -> None:
    events_a = []
    events_b = []

    manager.add_listener(
        events_a.append
    )

    manager.add_listener(
        events_b.append
    )

    assert len(
        manager.listeners
    ) == 2

    manager.clear_listeners()

    assert (
        manager.listeners
        == ()
    )

    manager.save(
        "slot_1",
        {}
    )

    assert (
        events_a
        == []
    )

    assert (
        events_b
        == []
    )


def test_invalid_listener_is_rejected(
    manager: SaveManager,
) -> None:
    with pytest.raises(
        TypeError,
        match="listener must be callable",
    ):
        manager.add_listener(
            123
        )


def test_broken_listener_does_not_break_save(
    manager: SaveManager,
) -> None:
    good_events = []

    def broken_listener(
        event,
    ):
        raise RuntimeError(
            "notification system exploded"
        )

    manager.add_listener(
        broken_listener
    )

    manager.add_listener(
        good_events.append
    )

    metadata = manager.save(
        "slot_1",
        {
            "value": 123,
        },
    )

    assert (
        metadata.slot
        == "slot_1"
    )

    assert (
        manager.exists(
            "slot_1"
        )
        is True
    )

    assert len(
        good_events
    ) == 2

    assert (
        good_events[0].state
        == SaveEventState.STARTED
    )

    assert (
        good_events[1].state
        == SaveEventState.COMPLETED
    )


def test_broken_listener_does_not_break_load(
    manager: SaveManager,
) -> None:
    manager.save(
        "slot_1",
        {
            "value": 55,
        },
    )

    def broken_listener(
        event,
    ):
        raise RuntimeError(
            "broken listener"
        )

    manager.add_listener(
        broken_listener
    )

    loaded = manager.load(
        "slot_1"
    )

    assert (
        loaded.data[
            "value"
        ]
        == 55
    )