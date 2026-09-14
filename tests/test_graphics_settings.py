from __future__ import annotations

from pathlib import Path

import pytest

from nexora.settings.graphics import (
    GraphicsSettings,
)
from nexora.settings.graphics_store import (
    GraphicsSettingsStore,
)


@pytest.fixture
def defaults_file(
    tmp_path: Path,
) -> Path:
    path = (
        tmp_path
        / "defaults"
        / "graphics.toml"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
[window]
width = 1280
height = 720
mode = "windowed"
resizable = true

[rendering]
vsync = true
frames_in_flight = 2

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 0.0
""".strip(),
        encoding="utf-8",
    )

    return path


# ============================================================
# DEFAULTS
# ============================================================


def test_graphics_store_loads_defaults(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = GraphicsSettingsStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    settings = store.load()

    assert (
        settings["window"]["width"]
        == 1280
    )

    assert (
        settings["window"]["height"]
        == 720
    )

    assert (
        settings["window"]["mode"]
        == "windowed"
    )

    assert (
        settings["window"]["resizable"]
        is True
    )

    assert (
        settings["rendering"]["vsync"]
        is True
    )

    assert (
        settings["rendering"][
            "frames_in_flight"
        ]
        == 2
    )

    assert (
        settings["post_processing"][
            "enabled"
        ]
        is True
    )

    assert (
        settings["post_processing"][
            "brightness"
        ]
        == 1.0
    )


def test_graphics_store_creates_user_file(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = GraphicsSettingsStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    assert (
        store.user_path
        is not None
    )

    assert not (
        store.user_path.exists()
    )

    store.load()

    assert (
        store.user_path.exists()
    )


def test_user_file_starts_empty(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = GraphicsSettingsStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    store.load()

    assert (
        store.user_path
        is not None
    )

    user_settings = (
        store.load_user()
    )

    assert (
        user_settings
        == {}
    )


# ============================================================
# PROJECT LAYER
# ============================================================


def test_project_layer_overrides_default_value(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    project_file = (
        tmp_path
        / "project"
        / "graphics.toml"
    )

    project_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    project_file.write_text(
        """
[window]
width = 1920

[rendering]
vsync = false
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults_file,
        project_path=project_file,
    )

    settings = store.load()

    assert (
        settings["window"]["width"]
        == 1920
    )

    assert (
        settings["window"]["height"]
        == 720
    )

    assert (
        settings["rendering"]["vsync"]
        is False
    )

    assert (
        settings["rendering"][
            "frames_in_flight"
        ]
        == 2
    )


# ============================================================
# MOD LAYER
# ============================================================


def test_mod_layer_overrides_project_layer(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    project_file = (
        tmp_path
        / "project.toml"
    )

    project_file.write_text(
        """
[post_processing]
brightness = 1.1
""".strip(),
        encoding="utf-8",
    )

    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[post_processing]
brightness = 1.4
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults_file,
        project_path=project_file,
        mod_paths=(
            mod_file,
        ),
    )

    settings = store.load()

    assert (
        settings["post_processing"][
            "brightness"
        ]
        == 1.4
    )


def test_mod_can_override_single_setting_only(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[post_processing]
film_grain = 0.25
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults_file,
        mod_paths=(
            mod_file,
        ),
    )

    settings = store.load()

    assert (
        settings["post_processing"][
            "film_grain"
        ]
        == 0.25
    )

    assert (
        settings["post_processing"][
            "brightness"
        ]
        == 1.0
    )

    assert (
        settings["post_processing"][
            "contrast"
        ]
        == 1.0
    )


# ============================================================
# USER PRIORITY
# ============================================================


def test_user_layer_has_highest_priority(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    project_file = (
        tmp_path
        / "project.toml"
    )

    project_file.write_text(
        """
[rendering]
vsync = false
""".strip(),
        encoding="utf-8",
    )

    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[rendering]
vsync = true
""".strip(),
        encoding="utf-8",
    )

    user_path = (
        tmp_path
        / "user"
    )

    user_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        user_path
        / "graphics.toml"
    ).write_text(
        """
[rendering]
vsync = false
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=user_path,
        defaults_path=defaults_file,
        project_path=project_file,
        mod_paths=(
            mod_file,
        ),
    )

    settings = store.load()

    assert (
        settings["rendering"]["vsync"]
        is False
    )


# ============================================================
# GRAPHICS SETTINGS API
# ============================================================


def test_graphics_attribute_api(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    assert (
        graphics.window.width
        == 1280
    )

    assert (
        graphics.window.height
        == 720
    )

    assert (
        graphics.window.mode
        == "windowed"
    )

    assert (
        graphics.rendering.vsync
        is True
    )

    assert (
        graphics.rendering.frames_in_flight
        == 2
    )

    assert (
        graphics.post_processing.enabled
        is True
    )

    assert (
        graphics.post_processing.brightness
        == 1.0
    )


def test_graphics_attribute_assignment_creates_override(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    graphics.window.width = 1920

    assert (
        graphics.window.width
        == 1920
    )

    assert (
        graphics.user_data["window"][
            "width"
        ]
        == 1920
    )


def test_graphics_post_processing_override(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    graphics.post_processing.brightness = 1.25
    graphics.post_processing.film_grain = 0.15

    assert (
        graphics.post_processing.brightness
        == 1.25
    )

    assert (
        graphics.post_processing.film_grain
        == 0.15
    )


# ============================================================
# SAVE / RELOAD
# ============================================================


def test_graphics_user_override_is_persisted(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    user_path = (
        tmp_path
        / "user"
    )

    graphics = GraphicsSettings(
        settings_path=user_path,
        defaults_path=defaults_file,
    )

    graphics.window.width = 1600
    graphics.rendering.vsync = False

    reloaded = GraphicsSettings(
        settings_path=user_path,
        defaults_path=defaults_file,
    )

    assert (
        reloaded.window.width
        == 1600
    )

    assert (
        reloaded.rendering.vsync
        is False
    )


def test_remove_override_restores_lower_layer(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    graphics.window.width = 1920

    assert (
        graphics.window.width
        == 1920
    )

    removed = (
        graphics.remove_override(
            "window.width"
        )
    )

    assert (
        removed
        is True
    )

    assert (
        graphics.window.width
        == 1280
    )


def test_remove_unknown_override_returns_false(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    assert (
        graphics.remove_override(
            "window.width"
        )
        is False
    )


# ============================================================
# RESET
# ============================================================


def test_reset_user_restores_defaults(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    graphics.window.width = 1920
    graphics.rendering.vsync = False
    graphics.post_processing.film_grain = 0.5

    graphics.reset_user()

    assert (
        graphics.window.width
        == 1280
    )

    assert (
        graphics.rendering.vsync
        is True
    )

    assert (
        graphics.post_processing.film_grain
        == 0.0
    )

    assert (
        graphics.user_data
        == {}
    )


# ============================================================
# GPU CONTEXT SETTINGS
# ============================================================


def test_gpu_context_kwargs(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    graphics = GraphicsSettings(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    kwargs = (
        graphics.gpu_context_kwargs()
    )

    assert kwargs == {
        "width": 1280,
        "height": 720,
        "window_mode": "windowed",
        "resizable": True,
        "vsync": True,
        "frames_in_flight": 2,
    }


# ============================================================
# VALIDATION
# ============================================================


def test_invalid_window_width_raises(
    tmp_path: Path,
) -> None:
    defaults = (
        tmp_path
        / "graphics.toml"
    )

    defaults.write_text(
        """
[window]
width = 0
height = 720
mode = "windowed"
resizable = true

[rendering]
vsync = true
frames_in_flight = 2

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 0.0
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults,
    )

    with pytest.raises(
        ValueError
    ):
        store.load()


def test_invalid_window_mode_raises(
    tmp_path: Path,
) -> None:
    defaults = (
        tmp_path
        / "graphics.toml"
    )

    defaults.write_text(
        """
[window]
width = 1280
height = 720
mode = "banana"
resizable = true

[rendering]
vsync = true
frames_in_flight = 2

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 0.0
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults,
    )

    with pytest.raises(
        ValueError
    ):
        store.load()


def test_invalid_frames_in_flight_raises(
    tmp_path: Path,
) -> None:
    defaults = (
        tmp_path
        / "graphics.toml"
    )

    defaults.write_text(
        """
[window]
width = 1280
height = 720
mode = "windowed"
resizable = true

[rendering]
vsync = true
frames_in_flight = 5

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 0.0
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults,
    )

    with pytest.raises(
        ValueError
    ):
        store.load()


def test_invalid_film_grain_raises(
    tmp_path: Path,
) -> None:
    defaults = (
        tmp_path
        / "graphics.toml"
    )

    defaults.write_text(
        """
[window]
width = 1280
height = 720
mode = "windowed"
resizable = true

[rendering]
vsync = true
frames_in_flight = 2

[post_processing]
enabled = true
brightness = 1.0
contrast = 1.0
saturation = 1.0
film_grain = 2.0
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=defaults,
    )

    with pytest.raises(
        ValueError
    ):
        store.load()


def test_unknown_setting_raises(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    user_path = (
        tmp_path
        / "user"
    )

    user_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        user_path
        / "graphics.toml"
    ).write_text(
        """
[rendering]
potato_mode = true
""".strip(),
        encoding="utf-8",
    )

    store = GraphicsSettingsStore(
        settings_path=user_path,
        defaults_path=defaults_file,
    )

    with pytest.raises(
        ValueError
    ):
        store.load()


def test_missing_defaults_file_raises(
    tmp_path: Path,
) -> None:
    store = GraphicsSettingsStore(
        settings_path=None,
        defaults_path=(
            tmp_path
            / "missing.toml"
        ),
    )

    with pytest.raises(
        FileNotFoundError
    ):
        store.load()