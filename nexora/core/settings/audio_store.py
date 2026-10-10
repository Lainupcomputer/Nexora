from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from nexora.core.settings.toml_store import TomlSettingsStore


class AudioSettingsStore(TomlSettingsStore):
    """Layered storage for the dynamic audio bus graph."""

    FILE_NAME = "audio.toml"
    SETTINGS_NAME = "audio"
    REQUIRED_SECTIONS = {
        "buses": set(),
    }

    USER_HEADER = (
        "# Nexora user audio settings\n"
        "# Only changed audio settings are stored here.\n"
    )

    def _validate_complete(
        self,
        data: dict[str, Any],
    ) -> None:
        super()._validate_complete(data)

        buses = data["buses"]
        if "master" not in {str(name).casefold() for name in buses}:
            raise ValueError("Missing audio bus: master")

        for bus_name, bus in buses.items():
            self._validate_bus(
                str(bus_name),
                bus,
                Path(self.FILE_NAME),
            )

    @classmethod
    def _validate_layer(
        cls,
        data: Mapping[str, Any],
        path: Path,
    ) -> None:
        cls._check_unknown_sections(data, {"buses"}, path)

        buses = data.get("buses")
        if buses is None:
            return

        cls._require_table(buses, "buses", path)
        assert isinstance(buses, dict)

        for bus_name, bus in buses.items():
            cls._validate_bus(str(bus_name), bus, path)

    @classmethod
    def _validate_bus(
        cls,
        bus_name: str,
        bus: object,
        path: Path,
    ) -> None:
        table_name = f"buses.{bus_name}"
        cls._require_table(bus, table_name, path)
        assert isinstance(bus, dict)
        cls._check_unknown(
            bus,
            {"volume", "muted", "parent"},
            table_name,
            path,
        )

        if "volume" in bus:
            cls._non_negative_number(
                bus["volume"],
                f"buses.{bus_name}.volume",
                path,
            )

        if "muted" in bus:
            cls._boolean(
                bus["muted"],
                f"buses.{bus_name}.muted",
                path,
            )

        if "parent" in bus:
            cls._string(
                bus["parent"],
                f"buses.{bus_name}.parent",
                path,
            )

    @classmethod
    def _encode_toml(
        cls,
        data: Mapping[str, Any],
    ) -> str:
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
                        lines.append(
                            f"{key} = {cls._encode_value(bus[key])}"
                        )
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"
