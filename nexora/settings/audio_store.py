from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping

from nexora.settings.layered_store import LayeredSettingsStore


class AudioSettingsStore(LayeredSettingsStore[dict[str, Any]]):
    """Layered storage for the dynamic audio bus graph."""

    FILE_NAME = "audio.toml"
    USER_HEADER = (
        "# Nexora user audio settings\n"
        "# Only changed audio settings are stored here.\n"
    )

    def _empty(self) -> dict[str, Any]:
        return {}

    def _read_layer(self, path: Path, *, required: bool) -> dict[str, Any]:
        if not path.is_file():
            if required:
                raise FileNotFoundError(f"Audio settings file not found: {path}")
            return {}

        with path.open("rb") as file:
            data = tomllib.load(file)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid audio settings file: {path}")

        self._validate_layer(data, path)
        return deepcopy(data)

    def _merge_layer(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        self._deep_merge(target, source)

    def _validate_user(self, data: dict[str, Any]) -> None:
        self._validate_layer(data, self.user_path or Path(self.FILE_NAME))

    def _validate_complete(self, data: dict[str, Any]) -> None:
        buses = data.get("buses")
        if not isinstance(buses, dict):
            raise ValueError("Missing audio section: buses")
        if "master" not in {str(name).casefold() for name in buses}:
            raise ValueError("Missing audio bus: master")
        for bus_name, bus in buses.items():
            self._validate_bus(str(bus_name), bus, Path(self.FILE_NAME))

    def _encode_user(self, data: dict[str, Any]) -> str:
        return self._encode_toml(data)

    @classmethod
    def _deep_merge(cls, target: dict[str, Any], source: Mapping[str, Any]) -> None:
        for key, value in source.items():
            current = target.get(key)
            if isinstance(current, dict) and isinstance(value, Mapping):
                cls._deep_merge(current, value)
            else:
                target[key] = deepcopy(value)

    @classmethod
    def _validate_layer(cls, data: Mapping[str, Any], path: Path) -> None:
        unknown = set(data) - {"buses"}
        if unknown:
            raise ValueError(
                f"Unknown audio section(s) in {path}: "
                + ", ".join(sorted(unknown))
            )

        buses = data.get("buses")
        if buses is None:
            return
        if not isinstance(buses, dict):
            raise ValueError(f"[buses] in {path} must be a TOML table.")
        for bus_name, bus in buses.items():
            cls._validate_bus(str(bus_name), bus, path)

    @classmethod
    def _validate_bus(cls, bus_name: str, bus: object, path: Path) -> None:
        if not isinstance(bus, dict):
            raise ValueError(f"[buses.{bus_name}] in {path} must be a TOML table.")

        unknown = set(bus) - {"volume", "muted", "parent"}
        if unknown:
            raise ValueError(
                f"Unknown setting(s) in [buses.{bus_name}] in {path}: "
                + ", ".join(sorted(unknown))
            )

        if "volume" in bus:
            cls._volume(bus["volume"], f"buses.{bus_name}.volume", path)
        if "muted" in bus and not isinstance(bus["muted"], bool):
            raise ValueError(f"buses.{bus_name}.muted in {path} must be a boolean.")
        if "parent" in bus and not isinstance(bus["parent"], str):
            raise ValueError(f"buses.{bus_name}.parent in {path} must be a string.")

    @staticmethod
    def _volume(value: object, name: str, path: Path) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} in {path} must be a number.")
        value = float(value)
        if value < 0.0:
            raise ValueError(f"{name} in {path} must not be negative.")

    @classmethod
    def _encode_toml(cls, data: Mapping[str, Any]) -> str:
        lines = [
            "# Nexora user audio settings",
            "# Only changed audio settings are stored here.",
            "",
        ]
        buses = data.get("buses")
        if isinstance(buses, Mapping):
            for bus_name, bus in buses.items():
                if not isinstance(bus, Mapping) or not bus:
                    continue
                lines.append(f"[buses.{bus_name}]")
                for key in ("parent", "volume", "muted"):
                    if key in bus:
                        lines.append(f"{key} = {cls._encode_value(bus[key])}")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _encode_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return repr(value)
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        raise TypeError(f"Unsupported TOML value: {type(value).__name__}")
