from __future__ import annotations

from abc import abstractmethod
from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping

from nexora.core.settings.layered_store import LayeredSettingsStore


class TomlSettingsStore(
    LayeredSettingsStore[dict[str, Any]]
):
    """
    Shared layered store for dictionary-based TOML settings.

    Concrete stores only define their domain schema, validation rules and
    table layout for serialization. File loading, deep merging, user-layer
    validation and primitive TOML value encoding live here.
    """

    SETTINGS_NAME = "settings"
    REQUIRED_SECTIONS: Mapping[str, set[str]] = {}

    def _empty(self) -> dict[str, Any]:
        return {}

    def _read_layer(
        self,
        path: Path,
        *,
        required: bool,
    ) -> dict[str, Any]:
        if not path.is_file():
            if required:
                raise FileNotFoundError(
                    f"{self.SETTINGS_NAME.capitalize()} settings file "
                    f"not found: {path}"
                )
            return {}

        with path.open("rb") as file:
            data = tomllib.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                f"Invalid {self.SETTINGS_NAME} settings file: {path}"
            )

        self._validate_layer(data, path)
        return deepcopy(data)

    def _merge_layer(
        self,
        target: dict[str, Any],
        source: dict[str, Any],
    ) -> None:
        self._deep_merge(target, source)

    def _validate_user(
        self,
        data: dict[str, Any],
    ) -> None:
        self._validate_layer(
            data,
            self.user_path or Path(self.FILE_NAME),
        )

    def _validate_complete(
        self,
        data: dict[str, Any],
    ) -> None:
        for section_name, keys in self.REQUIRED_SECTIONS.items():
            section = data.get(section_name)

            if not isinstance(section, dict):
                raise ValueError(
                    f"Missing {self.SETTINGS_NAME} section: {section_name}"
                )

            missing = keys - set(section)
            if missing:
                raise ValueError(
                    f"Missing {self.SETTINGS_NAME} setting(s) in "
                    f"[{section_name}]: "
                    + ", ".join(sorted(missing))
                )

    def _encode_user(
        self,
        data: dict[str, Any],
    ) -> str:
        return self._encode_toml(data)

    @classmethod
    def _deep_merge(
        cls,
        target: dict[str, Any],
        source: Mapping[str, Any],
    ) -> None:
        for key, value in source.items():
            current = target.get(key)

            if isinstance(current, dict) and isinstance(value, Mapping):
                cls._deep_merge(current, value)
            else:
                target[key] = deepcopy(value)


    @classmethod
    def _check_unknown_sections(
        cls,
        data: Mapping[str, Any],
        allowed: set[str],
        path: Path,
    ) -> None:
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                f"Unknown {cls.SETTINGS_NAME} section(s) in {path}: "
                + ", ".join(sorted(unknown))
            )

    @staticmethod
    def _require_table(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if not isinstance(value, dict):
            raise ValueError(
                f"[{name}] in {path} must be a TOML table."
            )

    @staticmethod
    def _check_unknown(
        section: Mapping[str, Any],
        allowed: set[str],
        name: str,
        path: Path,
    ) -> None:
        unknown = set(section) - allowed
        if unknown:
            raise ValueError(
                f"Unknown setting(s) in [{name}] in {path}: "
                + ", ".join(sorted(unknown))
            )

    @staticmethod
    def _boolean(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"{name} in {path} must be a boolean.")

    @staticmethod
    def _string(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if not isinstance(value, str):
            raise ValueError(f"{name} in {path} must be a string.")

    @staticmethod
    def _positive_int(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{name} in {path} must be a positive integer."
            )

    @staticmethod
    def _number(
        value: object,
        name: str,
        path: Path,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError(f"{name} in {path} must be a number.")
        return float(value)

    @classmethod
    def _positive_number(
        cls,
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if cls._number(value, name, path) <= 0.0:
            raise ValueError(
                f"{name} in {path} must be greater than zero."
            )

    @classmethod
    def _non_negative_number(
        cls,
        value: object,
        name: str,
        path: Path,
    ) -> float:
        number = cls._number(value, name, path)
        if number < 0.0:
            raise ValueError(f"{name} in {path} must not be negative.")
        return number

    @classmethod
    def _encode_flat_sections(
        cls,
        data: Mapping[str, Any],
        section_order: tuple[str, ...],
        key_order: Mapping[str, tuple[str, ...]] | None = None,
    ) -> str:
        lines = cls.USER_HEADER.rstrip("\n").splitlines() + [""]

        for section_name in section_order:
            section = data.get(section_name)
            if not isinstance(section, Mapping) or not section:
                continue

            lines.append(f"[{section_name}]")
            keys = (
                key_order.get(section_name, tuple(section))
                if key_order is not None
                else tuple(section)
            )
            for key in keys:
                if key in section:
                    lines.append(
                        f"{key} = {cls._encode_value(section[key])}"
                    )
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _encode_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        if isinstance(value, (int, float)):
            return repr(value)

        raise TypeError(
            "Unsupported TOML value: "
            f"{type(value).__name__}"
        )

    @classmethod
    @abstractmethod
    def _validate_layer(
        cls,
        data: Mapping[str, Any],
        path: Path,
    ) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _encode_toml(
        cls,
        data: Mapping[str, Any],
    ) -> str:
        raise NotImplementedError
