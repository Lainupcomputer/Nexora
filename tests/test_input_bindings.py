from __future__ import annotations

from pathlib import Path

import pytest

from nexora.input.binding_store import (
    BindingStore,
)
from nexora.input.bindings import (
    BindingType,
    resolve_keyboard_key,
    resolve_mouse_button,
)
from nexora.input.input import (
    InputManager,
)


@pytest.fixture
def defaults_file(
    tmp_path: Path,
) -> Path:
    path = (
        tmp_path
        / "defaults"
        / "keybinds.toml"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
[move_up]
keyboard = ["w", "up"]

[move_down]
keyboard = ["s", "down"]

[move_left]
keyboard = ["a", "left"]

[move_right]
keyboard = ["d", "right"]

[jump]
keyboard = ["space"]

[interact]
keyboard = ["e"]

[attack]
mouse = ["left"]

[pause]
keyboard = ["escape"]
""".strip(),
        encoding="utf-8",
    )

    return path


# ============================================================
# DEFAULTS
# ============================================================


def test_binding_store_loads_defaults(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = BindingStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    bindings = store.load()

    assert "move_up" in bindings
    assert "jump" in bindings
    assert "attack" in bindings

    move_up = bindings[
        "move_up"
    ]

    assert len(
        move_up
    ) == 2

    assert (
        move_up[0].type
        is BindingType.KEYBOARD
    )

    assert (
        move_up[0].code
        == resolve_keyboard_key(
            "w"
        )
    )


def test_binding_store_creates_user_file(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    user_settings = (
        tmp_path
        / "user"
    )

    store = BindingStore(
        settings_path=user_settings,
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


def test_user_file_is_initialized_from_defaults(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = BindingStore(
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

    text = (
        store.user_path.read_text(
            encoding="utf-8",
        )
    )

    assert "[move_up]" in text
    assert 'keyboard = ["w", "up"]' in text

    assert "[jump]" in text
    assert 'keyboard = ["space"]' in text


# ============================================================
# USER OVERRIDES
# ============================================================


def test_user_layer_overrides_default_action(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    user_settings = (
        tmp_path
        / "user"
    )

    user_settings.mkdir(
        parents=True,
        exist_ok=True,
    )

    user_file = (
        user_settings
        / "keybinds.toml"
    )

    user_file.write_text(
        """
[move_up]
keyboard = ["i"]
""".strip(),
        encoding="utf-8",
    )

    store = BindingStore(
        settings_path=user_settings,
        defaults_path=defaults_file,
    )

    bindings = store.load()

    move_up = bindings[
        "move_up"
    ]

    assert len(
        move_up
    ) == 1

    assert (
        move_up[0].code
        == resolve_keyboard_key(
            "i"
        )
    )


# ============================================================
# PROJECT LAYER
# ============================================================


def test_project_layer_overrides_defaults(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    project_file = (
        tmp_path
        / "project"
        / "keybinds.toml"
    )

    project_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    project_file.write_text(
        """
[jump]
keyboard = ["j"]
""".strip(),
        encoding="utf-8",
    )

    store = BindingStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
        project_path=project_file,
    )

    bindings = store.load()

    jump = bindings[
        "jump"
    ]

    assert len(
        jump
    ) == 1

    assert (
        jump[0].code
        == resolve_keyboard_key(
            "j"
        )
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
[interact]
keyboard = ["e"]
""".strip(),
        encoding="utf-8",
    )

    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[interact]
keyboard = ["f"]
""".strip(),
        encoding="utf-8",
    )

    # No user settings here, otherwise the automatically created
    # user file would contain the project binding and therefore
    # override the mod layer again.
    store = BindingStore(
        settings_path=None,
        defaults_path=defaults_file,
        project_path=project_file,
        mod_paths=(
            mod_file,
        ),
    )

    bindings = store.load()

    interact = bindings[
        "interact"
    ]

    assert len(
        interact
    ) == 1

    assert (
        interact[0].code
        == resolve_keyboard_key(
            "f"
        )
    )


def test_layer_can_add_new_action(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[fishing_cast]
keyboard = ["f"]
""".strip(),
        encoding="utf-8",
    )

    store = BindingStore(
        settings_path=None,
        defaults_path=defaults_file,
        mod_paths=(
            mod_file,
        ),
    )

    bindings = store.load()

    assert (
        "fishing_cast"
        in bindings
    )

    assert (
        bindings[
            "fishing_cast"
        ][0].code
        == resolve_keyboard_key(
            "f"
        )
    )


# ============================================================
# LAYER PRIORITY
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
[jump]
keyboard = ["j"]
""".strip(),
        encoding="utf-8",
    )

    mod_file = (
        tmp_path
        / "mod.toml"
    )

    mod_file.write_text(
        """
[jump]
keyboard = ["k"]
""".strip(),
        encoding="utf-8",
    )

    user_settings = (
        tmp_path
        / "user"
    )

    user_settings.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        user_settings
        / "keybinds.toml"
    ).write_text(
        """
[jump]
keyboard = ["l"]
""".strip(),
        encoding="utf-8",
    )

    store = BindingStore(
        settings_path=user_settings,
        defaults_path=defaults_file,
        project_path=project_file,
        mod_paths=(
            mod_file,
        ),
    )

    bindings = store.load()

    jump = bindings[
        "jump"
    ]

    assert len(
        jump
    ) == 1

    assert (
        jump[0].code
        == resolve_keyboard_key(
            "l"
        )
    )


# ============================================================
# MOUSE
# ============================================================


def test_mouse_binding_is_loaded(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    store = BindingStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    bindings = store.load()

    attack = bindings[
        "attack"
    ]

    assert len(
        attack
    ) == 1

    assert (
        attack[0].type
        is BindingType.MOUSE
    )

    assert (
        attack[0].code
        == resolve_mouse_button(
            "left"
        )
    )


def test_multiple_devices_can_bind_same_action(
    tmp_path: Path,
) -> None:
    defaults = (
        tmp_path
        / "defaults.toml"
    )

    defaults.write_text(
        """
[attack]
keyboard = ["f"]
mouse = ["left"]
""".strip(),
        encoding="utf-8",
    )

    store = BindingStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults,
    )

    bindings = store.load()

    attack = bindings[
        "attack"
    ]

    assert len(
        attack
    ) == 2

    assert any(
        binding.type
        is BindingType.KEYBOARD
        for binding in attack
    )

    assert any(
        binding.type
        is BindingType.MOUSE
        for binding in attack
    )


# ============================================================
# INPUT MANAGER ATTRIBUTE API
# ============================================================


def test_input_manager_attribute_action_api(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    input_manager = InputManager(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    move_up_code = (
        resolve_keyboard_key(
            "w"
        )
    )

    input_manager._keys_down.add(
        move_up_code
    )

    input_manager._update_action_states()

    assert (
        input_manager.action_down.move_up
        is True
    )

    assert (
        input_manager.action_down.move_down
        is False
    )


def test_input_manager_callable_action_api_still_works(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    input_manager = InputManager(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    jump_code = (
        resolve_keyboard_key(
            "space"
        )
    )

    input_manager._keys_down.add(
        jump_code
    )

    input_manager._keys_pressed.add(
        jump_code
    )

    input_manager._update_action_states()

    assert (
        input_manager.action_down(
            "jump"
        )
        is True
    )

    assert (
        input_manager.action_pressed(
            "jump"
        )
        is True
    )


def test_input_manager_attribute_pressed_api(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    input_manager = InputManager(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    jump_code = (
        resolve_keyboard_key(
            "space"
        )
    )

    input_manager._keys_down.add(
        jump_code
    )

    input_manager._keys_pressed.add(
        jump_code
    )

    input_manager._update_action_states()

    assert (
        input_manager.action_pressed.jump
        is True
    )


def test_input_manager_attribute_released_api(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    input_manager = InputManager(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=defaults_file,
    )

    interact_code = (
        resolve_keyboard_key(
            "e"
        )
    )

    input_manager._keys_released.add(
        interact_code
    )

    input_manager._update_action_states()

    assert (
        input_manager.action_released.interact
        is True
    )


# ============================================================
# RESET
# ============================================================


def test_reset_bindings_restores_base_configuration(
    tmp_path: Path,
    defaults_file: Path,
) -> None:
    user_settings = (
        tmp_path
        / "user"
    )

    store = BindingStore(
        settings_path=user_settings,
        defaults_path=defaults_file,
    )

    store.load()

    assert (
        store.user_path
        is not None
    )

    store.user_path.write_text(
        """
[move_up]
keyboard = ["i"]
""".strip(),
        encoding="utf-8",
    )

    bindings = store.load()

    assert (
        bindings[
            "move_up"
        ][0].code
        == resolve_keyboard_key(
            "i"
        )
    )

    store.reset_user()

    bindings = store.load()

    assert (
        bindings[
            "move_up"
        ][0].code
        == resolve_keyboard_key(
            "w"
        )
    )


# ============================================================
# MISSING DEFAULTS
# ============================================================


def test_missing_required_defaults_raises(
    tmp_path: Path,
) -> None:
    store = BindingStore(
        settings_path=(
            tmp_path
            / "user"
        ),
        defaults_path=(
            tmp_path
            / "does_not_exist.toml"
        ),
    )

    with pytest.raises(
        FileNotFoundError
    ):
        store.load()