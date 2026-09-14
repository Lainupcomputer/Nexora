from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping

from nexora.settings.layered_store import (
    LayeredSettingsStore,
)


class AudioSettingsStore(
    LayeredSettingsStore[
        dict[str, Any]
    ]
):
    """
    Layered storage for user-facing audio settings.

    Audio settings intentionally contain only:

        channel volumes
        bus volumes
        bus mute states

    Technical audio configuration such as frequency,
    channels and buffer sizes belongs to engine.toml.
    """

    FILE_NAME = "audio.toml"

    USER_HEADER = (
        "# Nexora user audio settings\n"
        "# Only changed audio settings are stored here.\n"
    )

    CHANNELS = (
        "master",
        "music",
        "sfx",
        "ambient",
        "voice",
    )

    # ==========================================================
    # LAYERED STORE
    # ==========================================================

    def _empty(
        self,
    ) -> dict[str, Any]:
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
                    "Audio settings file not found: "
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
                f"Invalid audio settings file: {path}"
            )

        self._validate_layer(
            data,
            path,
        )

        return deepcopy(
            data
        )

    def _merge_layer(
        self,
        target: dict[str, Any],
        source: dict[str, Any],
    ) -> None:
        self._deep_merge(
            target,
            source,
        )

    def _validate_user(
        self,
        data: dict[str, Any],
    ) -> None:
        self._validate_layer(
            data,
            self.user_path
            or Path(
                self.FILE_NAME
            ),
        )

    def _validate_complete(
        self,
        data: dict[str, Any],
    ) -> None:
        volume = data.get(
            "volume"
        )

        if not isinstance(
            volume,
            dict,
        ):
            raise ValueError(
                "Missing audio section: volume"
            )

        missing_channels = (
            set(
                self.CHANNELS
            )
            - set(
                volume
            )
        )

        if missing_channels:
            raise ValueError(
                "Missing audio volume setting(s): "
                + ", ".join(
                    sorted(
                        missing_channels
                    )
                )
            )

        buses = data.get(
            "buses"
        )

        if not isinstance(
            buses,
            dict,
        ):
            raise ValueError(
                "Missing audio section: buses"
            )

        missing_buses = (
            set(
                self.CHANNELS
            )
            - set(
                buses
            )
        )

        if missing_buses:
            raise ValueError(
                "Missing audio bus setting(s): "
                + ", ".join(
                    sorted(
                        missing_buses
                    )
                )
            )

        for bus_name in self.CHANNELS:
            bus = buses.get(
                bus_name
            )

            if not isinstance(
                bus,
                dict,
            ):
                raise ValueError(
                    f"Missing audio bus: {bus_name}"
                )

            missing = (
                {
                    "volume",
                    "muted",
                }
                - set(
                    bus
                )
            )

            if missing:
                raise ValueError(
                    f"Missing setting(s) in "
                    f"[buses.{bus_name}]: "
                    + ", ".join(
                        sorted(
                            missing
                        )
                    )
                )

    def _encode_user(
        self,
        data: dict[str, Any],
    ) -> str:
        return self._encode_toml(
            data
        )

    # ==========================================================
    # MERGE
    # ==========================================================

    @classmethod
    def _deep_merge(
        cls,
        target: dict[str, Any],
        source: Mapping[str, Any],
    ) -> None:
        for key, value in source.items():
            current = target.get(
                key
            )

            if (
                isinstance(
                    current,
                    dict,
                )
                and isinstance(
                    value,
                    Mapping,
                )
            ):
                cls._deep_merge(
                    current,
                    value,
                )

            else:
                target[
                    key
                ] = deepcopy(
                    value
                )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @classmethod
    def _validate_layer(
        cls,
        data: Mapping[str, Any],
        path: Path,
    ) -> None:
        allowed = {
            "volume",
            "buses",
        }

        unknown = (
            set(
                data
            )
            - allowed
        )

        if unknown:
            raise ValueError(
                "Unknown audio section(s) in "
                f"{path}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        # ------------------------------------------------------
        # Channel volumes
        # ------------------------------------------------------

        volume = data.get(
            "volume"
        )

        if volume is not None:
            if not isinstance(
                volume,
                dict,
            ):
                raise ValueError(
                    f"[volume] in {path} "
                    "must be a TOML table."
                )

            unknown_channels = (
                set(
                    volume
                )
                - set(
                    cls.CHANNELS
                )
            )

            if unknown_channels:
                raise ValueError(
                    "Unknown audio channel(s) in "
                    f"{path}: "
                    + ", ".join(
                        sorted(
                            unknown_channels
                        )
                    )
                )

            for name, value in volume.items():
                cls._volume(
                    value,
                    f"volume.{name}",
                    path,
                )

        # ------------------------------------------------------
        # Buses
        # ------------------------------------------------------

        buses = data.get(
            "buses"
        )

        if buses is not None:
            if not isinstance(
                buses,
                dict,
            ):
                raise ValueError(
                    f"[buses] in {path} "
                    "must be a TOML table."
                )

            unknown_buses = (
                set(
                    buses
                )
                - set(
                    cls.CHANNELS
                )
            )

            if unknown_buses:
                raise ValueError(
                    "Unknown audio bus(es) in "
                    f"{path}: "
                    + ", ".join(
                        sorted(
                            unknown_buses
                        )
                    )
                )

            for bus_name, bus in buses.items():
                cls._validate_bus(
                    bus_name,
                    bus,
                    path,
                )

    @classmethod
    def _validate_bus(
        cls,
        bus_name: str,
        bus: object,
        path: Path,
    ) -> None:
        if not isinstance(
            bus,
            dict,
        ):
            raise ValueError(
                f"[buses.{bus_name}] in {path} "
                "must be a TOML table."
            )

        allowed = {
            "volume",
            "muted",
        }

        unknown = (
            set(
                bus
            )
            - allowed
        )

        if unknown:
            raise ValueError(
                "Unknown setting(s) in "
                f"[buses.{bus_name}] in {path}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        if "volume" in bus:
            cls._volume(
                bus[
                    "volume"
                ],
                f"buses.{bus_name}.volume",
                path,
            )

        if "muted" in bus:
            if not isinstance(
                bus[
                    "muted"
                ],
                bool,
            ):
                raise ValueError(
                    f"buses.{bus_name}.muted "
                    f"in {path} must be a boolean."
                )

    @staticmethod
    def _volume(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                (
                    int,
                    float,
                ),
            )
        ):
            raise ValueError(
                f"{name} in {path} must be a number."
            )

        value = float(
            value
        )

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} in {path} "
                "must be between 0.0 and 1.0."
            )

    # ==========================================================
    # TOML ENCODING
    # ==========================================================

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

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        volume = data.get(
            "volume"
        )

        if (
            isinstance(
                volume,
                Mapping,
            )
            and volume
        ):
            lines.append(
                "[volume]"
            )

            for channel in cls.CHANNELS:
                if channel not in volume:
                    continue

                lines.append(
                    f"{channel} = "
                    f"{cls._encode_value(volume[channel])}"
                )

            lines.append(
                ""
            )

        # ------------------------------------------------------
        # Buses
        # ------------------------------------------------------

        buses = data.get(
            "buses"
        )

        if isinstance(
            buses,
            Mapping,
        ):
            for bus_name in cls.CHANNELS:
                bus = buses.get(
                    bus_name
                )

                if (
                    not isinstance(
                        bus,
                        Mapping,
                    )
                    or not bus
                ):
                    continue

                lines.append(
                    f"[buses.{bus_name}]"
                )

                if "volume" in bus:
                    lines.append(
                        "volume = "
                        f"{cls._encode_value(bus['volume'])}"
                    )

                if "muted" in bus:
                    lines.append(
                        "muted = "
                        f"{cls._encode_value(bus['muted'])}"
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
    def _encode_value(
        value: Any,
    ) -> str:
        if isinstance(
            value,
            bool,
        ):
            return (
                "true"
                if value
                else "false"
            )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            return repr(
                value
            )

        raise TypeError(
            "Unsupported TOML value: "
            f"{type(value).__name__}"
        )