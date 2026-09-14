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

from nexora.settings.layered_store import (
    LayeredSettingsStore,
)


class BindingStore(
    LayeredSettingsStore[
        dict[str, list[Binding]]
    ]
):
    """
    Layered TOML storage for input bindings.

    Layer order:

        engine defaults
        project settings
        mods
        user settings

    A later layer replaces an entire action from an earlier
    layer.

    The user file contains only bindings that differ from the
    effective defaults/project/mod configuration.
    """

    FILE_NAME = "keybinds.toml"

    USER_HEADER = (
        "# Nexora user key bindings\n"
        "# Only changed bindings are stored here.\n"
    )

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        defaults_path: str | Path | None = None,
        project_path: str | Path | None = None,
        mod_paths: Iterable[str | Path] = (),
        settings_path=...,
    ) -> None:
        kwargs = {
            "project_name": (
                project_name
            ),
            "defaults_path": (
                defaults_path
            ),
            "project_path": (
                project_path
            ),
            "mod_paths": (
                mod_paths
            ),
        }

        if settings_path is not ...:
            kwargs[
                "settings_path"
            ] = settings_path

        super().__init__(
            **kwargs
        )

    # ==========================================================
    # LAYERED STORE
    # ==========================================================

    def _empty(
        self,
    ) -> dict[
        str,
        list[Binding],
    ]:
        return {}

    def _read_layer(
        self,
        path: Path,
        *,
        required: bool,
    ) -> dict[
        str,
        list[Binding],
    ]:
        return self._read_file(
            path,
            required=required,
        )

    def _merge_layer(
        self,
        target: dict[
            str,
            list[Binding],
        ],
        source: dict[
            str,
            list[Binding],
        ],
    ) -> None:
        """
        A keybind layer replaces complete actions.
        """

        for action, bindings in source.items():
            target[
                action
            ] = list(
                bindings
            )

    def _encode_user(
        self,
        data: dict[
            str,
            list[Binding],
        ],
    ) -> str:
        return self._encode_toml(
            data
        )

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(
        self,
        bindings: Mapping[
            str,
            Sequence[Binding],
        ],
    ) -> None:
        """
        Persist only bindings that differ from the effective
        defaults/project/mod configuration.

        Removing a default action is represented by an empty
        action in the user layer.
        """

        baseline = (
            self.load_without_user()
        )

        current = {
            action: list(
                action_bindings
            )
            for action, action_bindings
            in bindings.items()
        }

        overrides: dict[
            str,
            list[Binding],
        ] = {}

        actions = (
            set(
                baseline
            )
            | set(
                current
            )
        )

        for action in sorted(
            actions
        ):
            baseline_bindings = (
                baseline.get(
                    action
                )
            )

            current_bindings = (
                current.get(
                    action
                )
            )

            # --------------------------------------------------
            # Default action removed by user
            # --------------------------------------------------

            if current_bindings is None:
                if baseline_bindings is not None:
                    overrides[
                        action
                    ] = []

                continue

            # --------------------------------------------------
            # Completely new user action
            # --------------------------------------------------

            if baseline_bindings is None:
                overrides[
                    action
                ] = current_bindings

                continue

            # --------------------------------------------------
            # Changed action
            # --------------------------------------------------

            if (
                current_bindings
                != baseline_bindings
            ):
                overrides[
                    action
                ] = current_bindings

        self.save_user(
            overrides
        )

    # ==========================================================
    # FILE READER
    # ==========================================================

    def _read_file(
        self,
        path: Path,
        *,
        required: bool,
    ) -> dict[
        str,
        list[Binding],
    ]:
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

    # ==========================================================
    # VALIDATION
    # ==========================================================

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

    # ==========================================================
    # TOML ENCODING
    # ==========================================================

    @staticmethod
    def _encode_toml(
        bindings: Mapping[
            str,
            Sequence[Binding],
        ],
    ) -> str:
        lines = [
            "# Nexora user key bindings",
            "# Only changed bindings are stored here.",
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
                # Explicit empty override disables the action.
                lines.append(
                    "keyboard = []"
                )

            lines.append(
                ""
            )

        return (
            "\n".join(
                lines
            ).rstrip()
            + "\n"
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