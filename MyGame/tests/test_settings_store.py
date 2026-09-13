from __future__ import annotations

import json

import pytest

from nexora.settings import SettingsStore


def test_settings_defaults(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json",
        defaults={
            "video": {
                "vsync": True,
            },
        },
    )

    assert store.get(
        "video.vsync"
    ) is True


def test_get_missing_uses_default(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    assert store.get(
        "missing.value",
        123,
    ) == 123


def test_set_and_get(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    store.set(
        "audio.master_volume",
        0.8,
    )

    assert store.get(
        "audio.master_volume"
    ) == pytest.approx(
        0.8
    )


def test_set_creates_nested_structure(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    store.set(
        "video.display.vsync",
        True,
    )

    assert store.data == {
        "video": {
            "display": {
                "vsync": True,
            },
        },
    }


def test_contains(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    store.set(
        "video.vsync",
        True,
    )

    assert store.contains(
        "video.vsync"
    )

    assert (
        "video.vsync"
        in store
    )


def test_remove(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    store.set(
        "audio.master",
        1.0,
    )

    assert store.remove(
        "audio.master"
    )

    assert not store.contains(
        "audio.master"
    )


def test_remove_missing_returns_false(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    assert not store.remove(
        "missing.value"
    )


def test_save(tmp_path):
    path = (
        tmp_path
        / "settings.json"
    )

    store = SettingsStore(
        path
    )

    store.set(
        "video.vsync",
        True,
    )

    store.save()

    assert path.is_file()

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert data[
        "video"
    ][
        "vsync"
    ] is True


def test_reload(tmp_path):
    path = (
        tmp_path
        / "settings.json"
    )

    path.write_text(
        json.dumps(
            {
                "audio": {
                    "master_volume": 0.4,
                },
            }
        ),
        encoding="utf-8",
    )

    store = SettingsStore(
        path
    )

    assert store.get(
        "audio.master_volume"
    ) == pytest.approx(
        0.4
    )


def test_reload_merges_defaults(tmp_path):
    path = (
        tmp_path
        / "settings.json"
    )

    path.write_text(
        json.dumps(
            {
                "video": {
                    "vsync": False,
                },
            }
        ),
        encoding="utf-8",
    )

    store = SettingsStore(
        path,
        defaults={
            "video": {
                "vsync": True,
                "fullscreen": False,
            },
            "audio": {
                "master": 1.0,
            },
        },
    )

    assert store.get(
        "video.vsync"
    ) is False

    assert store.get(
        "video.fullscreen"
    ) is False

    assert store.get(
        "audio.master"
    ) == pytest.approx(
        1.0
    )


def test_reset(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json",
        defaults={
            "video": {
                "vsync": True,
            },
        },
    )

    store.set(
        "video.vsync",
        False,
    )

    store.reset(
        save=False
    )

    assert store.get(
        "video.vsync"
    ) is True


def test_reset_key(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json",
        defaults={
            "audio": {
                "master": 1.0,
            },
        },
    )

    store.set(
        "audio.master",
        0.2,
    )

    assert store.reset_key(
        "audio.master"
    )

    assert store.get(
        "audio.master"
    ) == pytest.approx(
        1.0
    )


def test_reset_missing_key_returns_false(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    assert not store.reset_key(
        "missing.value"
    )


def test_set_default(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    store.set_default(
        "video.vsync",
        True,
    )

    assert store.get_default(
        "video.vsync"
    ) is True


def test_autosave(tmp_path):
    path = (
        tmp_path
        / "settings.json"
    )

    store = SettingsStore(
        path,
        autosave=True,
    )

    store.set(
        "video.vsync",
        True,
    )

    assert path.is_file()

    reloaded = SettingsStore(
        path
    )

    assert reloaded.get(
        "video.vsync"
    ) is True


def test_invalid_empty_key(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    with pytest.raises(
        ValueError
    ):
        store.get(
            ""
        )


def test_invalid_dotted_key(tmp_path):
    store = SettingsStore(
        tmp_path / "settings.json"
    )

    with pytest.raises(
        ValueError
    ):
        store.set(
            "video..vsync",
            True,
        )


def test_invalid_json_root(tmp_path):
    path = (
        tmp_path
        / "settings.json"
    )

    path.write_text(
        "[1, 2, 3]",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError
    ):
        SettingsStore(
            path
        )