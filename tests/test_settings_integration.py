from __future__ import annotations

from pathlib import Path

import pytest

from nexora.input.binding_store import (
    BindingStore,
)

from nexora.input.bindings import (
    Binding,
    BindingType,
    resolve_keyboard_key,
)

from nexora.settings.audio import (
    AudioSettings,
)

from nexora.settings.engine import (
    EngineSettings,
)

from nexora.settings.graphics import (
    GraphicsSettings,
)


# ==============================================================
# HELPERS
# ==============================================================


def write_text(
    path: Path,
    content: str,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content.strip() + "\n",
        encoding="utf-8",
    )

    return path


def make_engine_defaults(
    root: Path,
) -> Path:
    return write_text(
        root / "engine.toml",
        """
[timing]
target_fps = 144
fixed_delta_time = 0.016666666666666666

[debug]
overlay = false

[audio]
frequency = 48000
channels = 2

[audio_buffer]
target_queue_frames = 2048
max_update_frames = 2048
""",
    )


def make_graphics_defaults(
    root: Path,
) -> Path:
    return write_text(
        root / "graphics.toml",
        """
[window]
width = 1280
height = 720
mode = "windowed"
resizable = true

[rendering]
vsync = false
frames_in_flight = 2

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 0.0
""",
    )


def make_audio_defaults(
    root: Path,
) -> Path:
    return write_text(
        root / "audio.toml",
        """
[volume]
master = 1.0
music = 1.0
sfx = 1.0
ambient = 1.0
voice = 1.0

[buses.master]
volume = 1.0
muted = false

[buses.music]
volume = 1.0
muted = false

[buses.sfx]
volume = 1.0
muted = false

[buses.ambient]
volume = 1.0
muted = false

[buses.voice]
volume = 1.0
muted = false
""",
    )


def make_keybind_defaults(
    root: Path,
) -> Path:
    return write_text(
        root / "keybinds.toml",
        """
[move_up]
keyboard = ["w", "up"]

[move_down]
keyboard = ["s", "down"]

[jump]
keyboard = ["space"]

[attack]
mouse = ["left"]
""",
    )


# ==============================================================
# ENGINE SETTINGS
# ==============================================================


def test_engine_settings_load_defaults_and_user_override(
    tmp_path: Path,
) -> None:
    defaults = make_engine_defaults(
        tmp_path / "defaults"
    )

    user_dir = (
        tmp_path
        / "user"
    )

    settings = EngineSettings.__new__(
        EngineSettings
    )

    from nexora.settings.engine_store import (
        EngineSettingsStore,
    )

    settings.store = (
        EngineSettingsStore(
            project_name="TestGame",
            defaults_path=defaults,
            settings_path=user_dir,
        )
    )

    settings.autosave = True
    settings._data = {}
    settings._user_data = {}

    from nexora.settings.engine import (
        EngineSection,
    )

    settings.timing = (
        EngineSection(
            settings,
            "timing",
        )
    )

    settings.debug = (
        EngineSection(
            settings,
            "debug",
        )
    )

    settings.audio = (
        EngineSection(
            settings,
            "audio",
        )
    )

    settings.audio_buffer = (
        EngineSection(
            settings,
            "audio_buffer",
        )
    )

    settings.reload()

    assert (
        settings.timing.target_fps
        == 144
    )

    assert (
        settings.audio.frequency
        == 48000
    )

    settings.timing.target_fps = 120

    assert (
        settings.timing.target_fps
        == 120
    )

    text = (
        settings.store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "[timing]"
        in text
    )

    assert (
        "target_fps = 120"
        in text
    )

    assert (
        "fixed_delta_time"
        not in text
    )


def test_engine_settings_reset_restores_defaults(
    tmp_path: Path,
) -> None:
    defaults = make_engine_defaults(
        tmp_path / "defaults"
    )

    from nexora.settings.engine_store import (
        EngineSettingsStore,
    )

    from nexora.settings.engine import (
        EngineSection,
    )

    settings = EngineSettings.__new__(
        EngineSettings
    )

    settings.store = (
        EngineSettingsStore(
            project_name="TestGame",
            defaults_path=defaults,
            settings_path=(
                tmp_path
                / "user"
            ),
        )
    )

    settings.autosave = True
    settings._data = {}
    settings._user_data = {}

    settings.timing = (
        EngineSection(
            settings,
            "timing",
        )
    )

    settings.debug = (
        EngineSection(
            settings,
            "debug",
        )
    )

    settings.audio = (
        EngineSection(
            settings,
            "audio",
        )
    )

    settings.audio_buffer = (
        EngineSection(
            settings,
            "audio_buffer",
        )
    )

    settings.reload()

    settings.timing.target_fps = 100

    assert (
        settings.timing.target_fps
        == 100
    )

    settings.reset_user()

    assert (
        settings.timing.target_fps
        == 144
    )


# ==============================================================
# GRAPHICS SETTINGS
# ==============================================================


def test_graphics_settings_single_override_only(
    tmp_path: Path,
) -> None:
    defaults = make_graphics_defaults(
        tmp_path / "defaults"
    )

    settings = GraphicsSettings(
        defaults_path=defaults,
        settings_path=(
            tmp_path
            / "user"
        ),
        autosave=True,
    )

    assert (
        settings.window.width
        == 1280
    )

    settings.window.width = 1920

    assert (
        settings.window.width
        == 1920
    )

    text = (
        settings.store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "[window]"
        in text
    )

    assert (
        "width = 1920"
        in text
    )

    assert (
        "height"
        not in text
    )

    assert (
        "mode"
        not in text
    )


def test_graphics_remove_override_falls_back_to_default(
    tmp_path: Path,
) -> None:
    defaults = make_graphics_defaults(
        tmp_path / "defaults"
    )

    settings = GraphicsSettings(
        defaults_path=defaults,
        settings_path=(
            tmp_path
            / "user"
        ),
        autosave=True,
    )

    settings.window.width = 1600

    assert (
        settings.window.width
        == 1600
    )

    removed = (
        settings.remove_override(
            "window.width"
        )
    )

    assert (
        removed
        is True
    )

    assert (
        settings.window.width
        == 1280
    )


# ==============================================================
# AUDIO SETTINGS
# ==============================================================


def test_audio_settings_load_and_write_only_override(
    tmp_path: Path,
) -> None:
    defaults = make_audio_defaults(
        tmp_path / "defaults"
    )

    from nexora.settings.audio_store import (
        AudioSettingsStore,
    )

    from nexora.settings.audio import (
        AudioSection,
    )

    settings = AudioSettings.__new__(
        AudioSettings
    )

    settings.store = (
        AudioSettingsStore(
            project_name="TestGame",
            defaults_path=defaults,
            settings_path=(
                tmp_path
                / "user"
            ),
        )
    )

    settings.autosave = True
    settings._data = {}
    settings._user_data = {}

    settings.volume = (
        AudioSection(
            settings,
            "volume",
        )
    )

    settings.buses = (
        AudioSection(
            settings,
            "buses",
        )
    )

    settings.reload()

    assert (
        settings.volume.master
        == 1.0
    )

    assert (
        settings.buses.music.volume
        == 1.0
    )

    assert (
        settings.buses.music.muted
        is False
    )

    settings.volume.music = 0.5

    assert (
        settings.volume.music
        == 0.5
    )

    text = (
        settings.store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "[volume]"
        in text
    )

    assert (
        "music = 0.5"
        in text
    )

    assert (
        "master ="
        not in text
    )


def test_audio_bus_override_and_reset(
    tmp_path: Path,
) -> None:
    defaults = make_audio_defaults(
        tmp_path / "defaults"
    )

    from nexora.settings.audio_store import (
        AudioSettingsStore,
    )

    from nexora.settings.audio import (
        AudioSection,
    )

    settings = AudioSettings.__new__(
        AudioSettings
    )

    settings.store = (
        AudioSettingsStore(
            project_name="TestGame",
            defaults_path=defaults,
            settings_path=(
                tmp_path
                / "user"
            ),
        )
    )

    settings.autosave = True
    settings._data = {}
    settings._user_data = {}

    settings.volume = (
        AudioSection(
            settings,
            "volume",
        )
    )

    settings.buses = (
        AudioSection(
            settings,
            "buses",
        )
    )

    settings.reload()

    settings.buses.music.volume = 0.25
    settings.buses.music.muted = True

    assert (
        settings.buses.music.volume
        == 0.25
    )

    assert (
        settings.buses.music.muted
        is True
    )

    settings.reset_user()

    assert (
        settings.buses.music.volume
        == 1.0
    )

    assert (
        settings.buses.music.muted
        is False
    )


# ==============================================================
# KEYBINDS
# ==============================================================


def test_keybinds_do_not_write_defaults(
    tmp_path: Path,
) -> None:
    defaults = make_keybind_defaults(
        tmp_path / "defaults"
    )

    store = BindingStore(
        project_name="TestGame",
        defaults_path=defaults,
        settings_path=(
            tmp_path
            / "user"
        ),
    )

    bindings = store.load()

    store.save(
        bindings
    )

    text = (
        store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "[move_up]"
        not in text
    )

    assert (
        "[jump]"
        not in text
    )


def test_keybinds_write_only_changed_action(
    tmp_path: Path,
) -> None:
    defaults = make_keybind_defaults(
        tmp_path / "defaults"
    )

    store = BindingStore(
        project_name="TestGame",
        defaults_path=defaults,
        settings_path=(
            tmp_path
            / "user"
        ),
    )

    bindings = store.load()

    bindings[
        "jump"
    ] = [
        Binding(
            BindingType.KEYBOARD,
            resolve_keyboard_key(
                "j"
            ),
        )
    ]

    store.save(
        bindings
    )

    text = (
        store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "[jump]"
        in text
    )

    assert (
        'keyboard = ["J"]'
        in text
        or
        'keyboard = ["j"]'
        in text
    )

    assert (
        "[move_up]"
        not in text
    )

    assert (
        "[move_down]"
        not in text
    )


# ==============================================================
# CROSS-SYSTEM ISOLATION
# ==============================================================


def test_settings_systems_do_not_overwrite_each_other(
    tmp_path: Path,
) -> None:
    graphics_defaults = (
        make_graphics_defaults(
            tmp_path
            / "defaults"
        )
    )

    audio_defaults = (
        make_audio_defaults(
            tmp_path
            / "defaults"
        )
    )

    user_dir = (
        tmp_path
        / "user"
    )

    graphics = GraphicsSettings(
        defaults_path=(
            graphics_defaults
        ),
        settings_path=user_dir,
        autosave=True,
    )

    from nexora.settings.audio_store import (
        AudioSettingsStore,
    )

    from nexora.settings.audio import (
        AudioSection,
    )

    audio = AudioSettings.__new__(
        AudioSettings
    )

    audio.store = (
        AudioSettingsStore(
            project_name="TestGame",
            defaults_path=(
                audio_defaults
            ),
            settings_path=(
                user_dir
            ),
        )
    )

    audio.autosave = True
    audio._data = {}
    audio._user_data = {}

    audio.volume = (
        AudioSection(
            audio,
            "volume",
        )
    )

    audio.buses = (
        AudioSection(
            audio,
            "buses",
        )
    )

    audio.reload()

    graphics.window.width = 1600
    audio.volume.music = 0.4

    graphics_text = (
        graphics.store.user_path.read_text(
            encoding="utf-8",
        )
    )

    audio_text = (
        audio.store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        "width = 1600"
        in graphics_text
    )

    assert (
        "music = 0.4"
        not in graphics_text
    )

    assert (
        "music = 0.4"
        in audio_text
    )

    assert (
        "width = 1600"
        not in audio_text
    )