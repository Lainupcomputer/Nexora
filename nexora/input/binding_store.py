from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Iterable, Mapping, Sequence

from nexora.input.bindings import (
    Binding,
    BindingType,
    keyboard_key_name,
    mouse_button_name,
    resolve_keyboard_key,
    resolve_mouse_button,
)


DEFAULT_KEYBINDS_PATH = (
    Path(__file__).resolve().parent.parent
    / "core"
    / "defaults"
    / "keybinds.toml"
)


class BindingStore:
    """
    Layered TOML storage for input bindings.

    Layers are applied in this order::

        engine defaults
        project defaults
        mods
        user settings

    A later layer replaces an entire action from an earlier layer.
    This keeps overrides predictable and prevents old bindings from
    accidentally surviving a user or mod override.
    """

    FILE_NAME = "keybinds.toml"

    def __init__(
        self,
        *,
        defaults_path: str | Path | None = None,
        project_path: str | Path | None = None,
        mod_paths: Iterable[str | Path] = (),
        settings_path: str | Path | None = "settings",
    ) -> None:
        self.defaults_path = (
            Path(defaults_path)
            if defaults_path is not None
            else DEFAULT_KEYBINDS_PATH
        )

        self.project_path = (
            Path(project_path)
            if project_path is not None
            else None
        )

        self.mod_paths = tuple(
            Path(path)
            for path in mod_paths
        )

        self.settings_path = (
            Path(settings_path)
            if settings_path is not None
            else None
        )

        self.user_path = (
            self.settings_path
            / self.FILE_NAME
            if self.settings_path is not None
            else None
        )

    def ensure_user_file(
        self,
    ) -> None:
        """
        Create the initial user keybind file when it does not exist.

        The initial file contains engine + project defaults only.
        Mod bindings remain owned by the mod and are therefore not
        copied into the user's permanent configuration automatically.
        """

        if self.user_path is None:
            return

        if self.user_path.exists():
            return

        initial = (
            self._load_base_bindings()
        )

        self.save(
            initial
        )

    def load(
        self,
    ) -> dict[str, list[Binding]]:
        self.ensure_user_file()

        result = (
            self._load_base_bindings()
        )

        for path in self.mod_paths:
            self._apply_layer(
                result,
                path,
                required=False,
            )

        if self.user_path is not None:
            self._apply_layer(
                result,
                self.user_path,
                required=False,
            )

        return result

    def save(
        self,
        bindings: Mapping[
            str,
            Sequence[Binding],
        ],
    ) -> None:
        if self.user_path is None:
            raise RuntimeError(
                "No user settings path is configured."
            )

        self.user_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = (
            self._encode_toml(
                bindings
            )
        )

        temporary = (
            self.user_path.with_suffix(
                ".toml.tmp"
            )
        )

        temporary.write_text(
            content,
            encoding="utf-8",
        )

        temporary.replace(
            self.user_path
        )

    def reset_user(
        self,
    ) -> None:
        if self.user_path is None:
            return

        if self.user_path.exists():
            self.user_path.unlink()

        self.ensure_user_file()

    def _load_base_bindings(
        self,
    ) -> dict[str, list[Binding]]:
        result: dict[
            str,
            list[Binding],
        ] = {}

        self._apply_layer(
            result,
            self.defaults_path,
            required=True,
        )

        if self.project_path is not None:
            self._apply_layer(
                result,
                self.project_path,
                required=False,
            )

        return result

    def _apply_layer(
        self,
        target: dict[str, list[Binding]],
        path: Path,
        *,
        required: bool,
    ) -> None:
        layer = (
            self._read_file(
                path,
                required=required,
            )
        )

        for action, bindings in layer.items():
            target[
                action
            ] = bindings

    def _read_file(
        self,
        path: Path,
        *,
        required: bool,
    ) -> dict[str, list[Binding]]:
        if not path.is_file():
            if required:
                raise FileNotFoundError(
                    "Key binding file not found: "
                    f"{path}"
                )

            return {}

        with path.open(
            "rb"
        ) as file:
            data = tomllib.load(
                file
            )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                f"Invalid key binding file: {path}"
            )

        result: dict[
            str,
            list[Binding],
        ] = {}

        for action, config in data.items():
            if (
                not isinstance(
                    action,
                    str,
                )
                or not action
            ):
                raise ValueError(
                    f"Invalid action name in {path}"
                )

            if not isinstance(
                config,
                dict,
            ):
                raise ValueError(
                    f"Action {action!r} in {path} "
                    "must be a TOML table."
                )

            unknown = (
                set(config)
                - {
                    "keyboard",
                    "mouse",
                }
            )

            if unknown:
                names = ", ".join(
                    sorted(
                        unknown
                    )
                )

                raise ValueError(
                    "Unknown binding field(s) for "
                    f"{action!r} in {path}: "
                    f"{names}"
                )

            bindings: list[
                Binding
            ] = []

            for key in self._string_list(
                config.get(
                    "keyboard",
                    [],
                ),
                action=action,
                field="keyboard",
                path=path,
            ):
                bindings.append(
                    Binding(
                        BindingType.KEYBOARD,
                        resolve_keyboard_key(
                            key
                        ),
                    )
                )

            for button in self._string_list(
                config.get(
                    "mouse",
                    [],
                ),
                action=action,
                field="mouse",
                path=path,
            ):
                bindings.append(
                    Binding(
                        BindingType.MOUSE,
                        resolve_mouse_button(
                            button
                        ),
                    )
                )

            result[
                action
            ] = bindings

        return result

    @staticmethod
    def _string_list(
        value: object,
        *,
        action: str,
        field: str,
        path: Path,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            raise ValueError(
                f"{field!r} for action "
                f"{action!r} in {path} "
                "must be an array."
            )

        if not all(
            isinstance(
                item,
                str,
            )
            for item in value
        ):
            raise ValueError(
                f"{field!r} for action "
                f"{action!r} in {path} "
                "must contain strings only."
            )

        return list(
            value
        )

    @staticmethod
    def _encode_toml(
        bindings: Mapping[
            str,
            Sequence[Binding],
        ],
    ) -> str:
        lines = [
            "# Nexora user key bindings",
            (
                "# Generated by Nexora. "
                "This file may be edited manually."
            ),
            "",
        ]

        for action in sorted(
            bindings
        ):
            keyboard: list[
                str
            ] = []

            mouse: list[
                str
            ] = []

            for binding in bindings[
                action
            ]:
                if (
                    binding.type
                    is BindingType.KEYBOARD
                ):
                    keyboard.append(
                        keyboard_key_name(
                            binding.code
                        )
                    )

                elif (
                    binding.type
                    is BindingType.MOUSE
                ):
                    mouse.append(
                        mouse_button_name(
                            binding.code
                        )
                    )

                else:
                    raise ValueError(
                        "Unsupported binding type: "
                        f"{binding.type}"
                    )

            lines.append(
                "["
                + BindingStore._toml_key(
                    action
                )
                + "]"
            )

            if keyboard:
                lines.append(
                    "keyboard = "
                    + BindingStore._toml_array(
                        keyboard
                    )
                )

            if mouse:
                lines.append(
                    "mouse = "
                    + BindingStore._toml_array(
                        mouse
                    )
                )

            if (
                not keyboard
                and not mouse
            ):
                lines.append(
                    "keyboard = []"
                )

            lines.append(
                ""
            )

        return "\n".join(
            lines
        )

    @staticmethod
    def _toml_array(
        values: Sequence[str],
    ) -> str:
        escaped = [
            '"'
            + value.replace(
                "\\",
                "\\\\",
            ).replace(
                '"',
                '\\"',
            )
            + '"'
            for value in values
        ]

        return (
            "["
            + ", ".join(
                escaped
            )
            + "]"
        )

    @staticmethod
    def _toml_key(
        value: str,
    ) -> str:
        if (
            value.replace(
                "_",
                "a",
            ).isalnum()
            and not value[
                0
            ].isdigit()
        ):
            return value

        escaped = (
            value.replace(
                "\\",
                "\\\\",
            ).replace(
                '"',
                '\\"',
            )
        )

        return f'"{escaped}"'