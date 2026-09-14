from __future__ import annotations

from pathlib import Path

import pytest

from nexora import Game
from nexora.save import SaveManager


TEST_KEY = (
    b"nexora-engine-integration-test-key-"
    b"0123456789abcdef"
)


class SaveIntegrationGame(Game):
    """
    Minimal Game used to test SaveManager integration.
    """

    def __init__(
        self,
        save_path: Path,
    ) -> None:
        super().__init__(
            title="Save Integration Test",
            width=640,
            height=360,
            target_fps=60,
            resizable=False,
            vsync=False,
            save_path=save_path,
            save_signing_key=TEST_KEY,
            save_version=7,
            save_max_file_size=(
                8
                * 1024
                * 1024
            ),
        )

    def initialize(
        self,
    ) -> None:
        pass


@pytest.mark.gpu
def test_game_exposes_engine_save_manager(
    tmp_path,
) -> None:
    game = SaveIntegrationGame(
        tmp_path
    )

    # ----------------------------------------------------------
    # Before Engine creation there is intentionally no
    # SaveManager exposed through game.saves.
    # ----------------------------------------------------------

    with pytest.raises(
        RuntimeError
    ):
        _ = game.saves

    # ----------------------------------------------------------
    # Create Engine exactly like Game.run() would.
    #
    # We don't call engine.run() because this test only checks
    # service integration.
    # ----------------------------------------------------------

    game.engine = (
        game._create_engine()
        if hasattr(
            game,
            "_create_engine",
        )
        else None
    )

    # ----------------------------------------------------------
    # Current Game implementation creates Engine directly in
    # run(), so use the same configuration manually if there is
    # no _create_engine helper.
    # ----------------------------------------------------------

    if game.engine is None:
        from nexora.core.engine import Engine

        game.engine = Engine(
            game,
            width=game._width,
            height=game._height,
            title=game._title,
            target_fps=game._target_fps,
            fixed_delta_time=(
                game._fixed_delta_time
            ),
            resizable=game._resizable,
            fullscreen=game._fullscreen,
            window_mode=game._window_mode,
            vsync=game._vsync,
            save_path=game._save_path,
            save_signing_key=(
                game._save_signing_key
            ),
            save_version=(
                game._save_version
            ),
            save_max_file_size=(
                game._save_max_file_size
            ),
        )

    try:
        assert isinstance(
            game.engine.saves,
            SaveManager,
        )

        assert (
            game.saves
            is game.engine.saves
        )

    finally:
        game.engine.shutdown()


@pytest.mark.gpu
def test_game_save_configuration_reaches_manager(
    tmp_path,
) -> None:
    from nexora.core.engine import Engine

    game = SaveIntegrationGame(
        tmp_path
    )

    game.engine = Engine(
        game,
        width=game._width,
        height=game._height,
        title=game._title,
        target_fps=game._target_fps,
        fixed_delta_time=(
            game._fixed_delta_time
        ),
        resizable=game._resizable,
        fullscreen=game._fullscreen,
        window_mode=game._window_mode,
        vsync=game._vsync,
        save_path=game._save_path,
        save_signing_key=(
            game._save_signing_key
        ),
        save_version=(
            game._save_version
        ),
        save_max_file_size=(
            game._save_max_file_size
        ),
    )

    try:
        saves = game.saves

        assert (
            saves.save_path
            == tmp_path.resolve()
        )

        assert (
            saves.save_version
            == 7
        )

        assert (
            saves.max_file_size
            == (
                8
                * 1024
                * 1024
            )
        )

    finally:
        game.engine.shutdown()


@pytest.mark.gpu
def test_game_can_save_and_load_through_core_service(
    tmp_path,
) -> None:
    from nexora.core.engine import Engine

    game = SaveIntegrationGame(
        tmp_path
    )

    game.engine = Engine(
        game,
        width=game._width,
        height=game._height,
        title=game._title,
        target_fps=game._target_fps,
        fixed_delta_time=(
            game._fixed_delta_time
        ),
        resizable=game._resizable,
        fullscreen=game._fullscreen,
        window_mode=game._window_mode,
        vsync=game._vsync,
        save_path=game._save_path,
        save_signing_key=(
            game._save_signing_key
        ),
        save_version=(
            game._save_version
        ),
        save_max_file_size=(
            game._save_max_file_size
        ),
    )

    try:
        data = {
            "player": {
                "health": 85,
                "position": (
                    100.0,
                    250.0,
                ),
            },
            "world": {
                "scene": "HQ",
                "day": 3,
            },
        }

        metadata = game.saves.save(
            "slot_1",
            data,
            name="Integration Test",
            playtime=42.5,
        )

        assert (
            metadata.slot
            == "slot_1"
        )

        assert (
            game.saves.exists(
                "slot_1"
            )
            is True
        )

        loaded = game.saves.load(
            "slot_1"
        )

        assert (
            loaded.data
            == data
        )

        assert (
            loaded.metadata.name
            == "Integration Test"
        )

        assert (
            loaded.metadata.playtime
            == pytest.approx(
                42.5
            )
        )

    finally:
        game.engine.shutdown()


@pytest.mark.gpu
def test_game_can_change_save_path_at_runtime(
    tmp_path,
) -> None:
    from nexora.core.engine import Engine

    first_path = (
        tmp_path
        / "first"
    )

    second_path = (
        tmp_path
        / "second"
    )

    game = SaveIntegrationGame(
        first_path
    )

    game.engine = Engine(
        game,
        width=game._width,
        height=game._height,
        title=game._title,
        target_fps=game._target_fps,
        fixed_delta_time=(
            game._fixed_delta_time
        ),
        resizable=game._resizable,
        fullscreen=game._fullscreen,
        window_mode=game._window_mode,
        vsync=game._vsync,
        save_path=game._save_path,
        save_signing_key=(
            game._save_signing_key
        ),
        save_version=(
            game._save_version
        ),
        save_max_file_size=(
            game._save_max_file_size
        ),
    )

    try:
        game.saves.save(
            "first_slot",
            {
                "value": 1,
            },
        )

        assert (
            first_path
            / "first_slot.nxs"
        ).is_file()

        game.saves.save_path = (
            second_path
        )

        game.saves.save(
            "second_slot",
            {
                "value": 2,
            },
        )

        assert (
            second_path
            / "second_slot.nxs"
        ).is_file()

        assert (
            game.saves.save_path
            == second_path.resolve()
        )

    finally:
        game.engine.shutdown()


# ==============================================================
# AUTOSAVE
# ==============================================================


def test_auto_save_and_load_latest(
    manager: SaveManager,
) -> None:
    data = {
        "player": {
            "health": 75,
        },
    }

    metadata = manager.auto_save(
        data,
        playtime=15.0,
    )

    assert (
        metadata.slot
        == "autosave_1"
    )

    assert (
        manager.has_auto_save()
        is True
    )

    assert (
        manager.latest_auto_save_slot()
        == "autosave_1"
    )

    loaded = (
        manager.load_latest_auto_save()
    )

    assert (
        loaded.data
        == data
    )

    assert (
        loaded.metadata.name
        == "Auto Save"
    )

    assert (
        loaded.metadata.playtime
        == pytest.approx(
            15.0
        )
    )


def test_autosave_rotation(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_slots=3,
    )

    manager.auto_save(
        {
            "value": 1,
        },
        name="Save 1",
    )

    manager.auto_save(
        {
            "value": 2,
        },
        name="Save 2",
    )

    manager.auto_save(
        {
            "value": 3,
        },
        name="Save 3",
    )

    assert (
        manager.list_auto_saves()
        == (
            "autosave_1",
            "autosave_2",
            "autosave_3",
        )
    )

    newest = manager.load(
        "autosave_1"
    )

    middle = manager.load(
        "autosave_2"
    )

    oldest = manager.load(
        "autosave_3"
    )

    assert (
        newest.data[
            "value"
        ]
        == 3
    )

    assert (
        middle.data[
            "value"
        ]
        == 2
    )

    assert (
        oldest.data[
            "value"
        ]
        == 1
    )


def test_autosave_rotation_discards_oldest(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_slots=3,
    )

    manager.auto_save(
        {
            "value": 1,
        }
    )

    manager.auto_save(
        {
            "value": 2,
        }
    )

    manager.auto_save(
        {
            "value": 3,
        }
    )

    manager.auto_save(
        {
            "value": 4,
        }
    )

    assert (
        manager.load(
            "autosave_1"
        ).data["value"]
        == 4
    )

    assert (
        manager.load(
            "autosave_2"
        ).data["value"]
        == 3
    )

    assert (
        manager.load(
            "autosave_3"
        ).data["value"]
        == 2
    )


def test_autosave_can_be_disabled(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_enabled=False,
    )

    assert (
        manager.autosave_enabled
        is False
    )

    assert (
        manager.has_auto_save()
        is False
    )

    with pytest.raises(
        RuntimeError,
        match="Autosaving is disabled",
    ):
        manager.auto_save(
            {
                "value": 1,
            }
        )


def test_load_latest_autosave_disabled(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
    )

    manager.auto_save(
        {
            "value": 123,
        }
    )

    manager.autosave_enabled = (
        False
    )

    with pytest.raises(
        RuntimeError,
        match="Autosaving is disabled",
    ):
        manager.load_latest_auto_save()


def test_autosave_can_be_enabled_again(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_enabled=False,
    )

    manager.autosave_enabled = (
        True
    )

    manager.auto_save(
        {
            "value": 99,
        }
    )

    loaded = (
        manager.load_latest_auto_save()
    )

    assert (
        loaded.data[
            "value"
        ]
        == 99
    )


def test_custom_autosave_prefix(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_prefix="checkpoint",
        autosave_slots=2,
    )

    manager.auto_save(
        {
            "value": 1,
        }
    )

    assert (
        manager.latest_auto_save_slot()
        == "checkpoint_1"
    )

    assert (
        manager.exists(
            "checkpoint_1"
        )
        is True
    )


def test_autosave_slot_count(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_slots=2,
    )

    manager.auto_save(
        {
            "value": 1,
        }
    )

    manager.auto_save(
        {
            "value": 2,
        }
    )

    manager.auto_save(
        {
            "value": 3,
        }
    )

    assert (
        manager.list_auto_saves()
        == (
            "autosave_1",
            "autosave_2",
        )
    )

    assert (
        manager.exists(
            "autosave_3"
        )
        is False
    )


def test_invalid_autosave_slots_rejected(
    tmp_path,
) -> None:
    with pytest.raises(
        ValueError,
        match="autosave_slots must be greater than zero",
    ):
        SaveManager(
            tmp_path,
            signing_key=TEST_KEY,
            autosave_slots=0,
        )


def test_invalid_autosave_prefix_rejected(
    tmp_path,
) -> None:
    with pytest.raises(
        ValueError
    ):
        SaveManager(
            tmp_path,
            signing_key=TEST_KEY,
            autosave_prefix="../save",
        )


def test_load_latest_autosave_when_missing(
    manager: SaveManager,
) -> None:
    assert (
        manager.latest_auto_save_slot()
        is None
    )

    assert (
        manager.has_auto_save()
        is False
    )

    with pytest.raises(
        SaveNotFoundError,
        match="No autosave exists",
    ):
        manager.load_latest_auto_save()


def test_delete_all_autosaves(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_slots=3,
    )

    manager.auto_save(
        {
            "value": 1,
        }
    )

    manager.auto_save(
        {
            "value": 2,
        }
    )

    manager.auto_save(
        {
            "value": 3,
        }
    )

    deleted = (
        manager.delete_auto_saves()
    )

    assert (
        deleted
        == 3
    )

    assert (
        manager.list_auto_saves()
        == ()
    )

    assert (
        manager.has_auto_save()
        is False
    )


def test_delete_autosaves_when_none_exist(
    manager: SaveManager,
) -> None:
    assert (
        manager.delete_auto_saves()
        == 0
    )


def test_delete_autosaves_while_disabled(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
    )

    manager.auto_save(
        {
            "value": 1,
        }
    )

    manager.autosave_enabled = (
        False
    )

    assert (
        manager.has_auto_save()
        is False
    )

    assert (
        manager.delete_auto_saves()
        == 1
    )

    assert (
        manager.list_auto_saves()
        == ()
    )


def test_autosave_metadata_rotates_with_file(
    tmp_path,
) -> None:
    manager = SaveManager(
        tmp_path,
        signing_key=TEST_KEY,
        autosave_slots=3,
    )

    manager.auto_save(
        {
            "value": 1,
        },
        name="First",
    )

    manager.auto_save(
        {
            "value": 2,
        },
        name="Second",
    )

    newest = manager.load(
        "autosave_1"
    )

    older = manager.load(
        "autosave_2"
    )

    assert (
        newest.metadata.name
        == "Second"
    )

    assert (
        older.metadata.name
        == "First"
    )