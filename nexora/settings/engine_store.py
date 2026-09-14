from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping

from nexora.settings.layered_store import (
    LayeredSettingsStore,
)


class EngineSettingsStore(
    LayeredSettingsStore[
        dict[str, Any]
    ]
):
    FILE_NAME = "engine.toml"

    USER_HEADER = (
        "# Nexora user engine settings\n"
        "# Only changed engine settings are stored here.\n"
    )

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
                    "Engine settings file not found: "
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
                f"Invalid engine settings file: {path}"
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
        required = {
            "timing": {
                "target_fps",
                "fixed_delta_time",
            },
            "debug": {
                "overlay",
            },
            "audio": {
                "frequency",
                "channels",
            },
            "audio_buffer": {
                "target_queue_frames",
                "max_update_frames",
            },
        }

        for section_name, keys in required.items():
            section = data.get(
                section_name
            )

            if not isinstance(
                section,
                dict,
            ):
                raise ValueError(
                    "Missing engine section: "
                    f"{section_name}"
                )

            missing = (
                keys
                - set(
                    section
                )
            )

            if missing:
                raise ValueError(
                    "Missing engine setting(s) in "
                    f"[{section_name}]: "
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
            "timing",
            "debug",
            "audio",
            "audio_buffer",
        }

        unknown = (
            set(
                data
            )
            - allowed
        )

        if unknown:
            raise ValueError(
                "Unknown engine section(s) in "
                f"{path}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

        timing = data.get(
            "timing"
        )

        if timing is not None:
            cls._validate_timing(
                timing,
                path,
            )

        debug = data.get(
            "debug"
        )

        if debug is not None:
            cls._validate_debug(
                debug,
                path,
            )

        audio = data.get(
            "audio"
        )

        if audio is not None:
            cls._validate_audio(
                audio,
                path,
            )

        audio_buffer = data.get(
            "audio_buffer"
        )

        if audio_buffer is not None:
            cls._validate_audio_buffer(
                audio_buffer,
                path,
            )

    @classmethod
    def _validate_timing(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "timing",
            path,
        )

        assert isinstance(
            section,
            dict,
        )

        cls._unknown(
            section,
            {
                "target_fps",
                "fixed_delta_time",
            },
            "timing",
            path,
        )

        if "target_fps" in section:
            cls._positive_int(
                section[
                    "target_fps"
                ],
                "timing.target_fps",
                path,
            )

        if "fixed_delta_time" in section:
            cls._positive_number(
                section[
                    "fixed_delta_time"
                ],
                "timing.fixed_delta_time",
                path,
            )

    @classmethod
    def _validate_debug(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "debug",
            path,
        )

        assert isinstance(
            section,
            dict,
        )

        cls._unknown(
            section,
            {
                "overlay",
            },
            "debug",
            path,
        )

        if (
            "overlay" in section
            and not isinstance(
                section[
                    "overlay"
                ],
                bool,
            )
        ):
            raise ValueError(
                "debug.overlay in "
                f"{path} must be a boolean."
            )

    @classmethod
    def _validate_audio(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "audio",
            path,
        )

        assert isinstance(
            section,
            dict,
        )

        cls._unknown(
            section,
            {
                "frequency",
                "channels",
            },
            "audio",
            path,
        )

        if "frequency" in section:
            cls._positive_int(
                section[
                    "frequency"
                ],
                "audio.frequency",
                path,
            )

        if "channels" in section:
            cls._positive_int(
                section[
                    "channels"
                ],
                "audio.channels",
                path,
            )

    @classmethod
    def _validate_audio_buffer(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "audio_buffer",
            path,
        )

        assert isinstance(
            section,
            dict,
        )

        cls._unknown(
            section,
            {
                "target_queue_frames",
                "max_update_frames",
            },
            "audio_buffer",
            path,
        )

        for key in (
            "target_queue_frames",
            "max_update_frames",
        ):
            if key in section:
                cls._positive_int(
                    section[
                        key
                    ],
                    f"audio_buffer.{key}",
                    path,
                )

    # ==========================================================
    # VALIDATION HELPERS
    # ==========================================================

    @staticmethod
    def _require_table(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                f"[{name}] in {path} "
                "must be a TOML table."
            )

    @staticmethod
    def _unknown(
        section: Mapping[str, Any],
        allowed: set[str],
        name: str,
        path: Path,
    ) -> None:
        unknown = (
            set(
                section
            )
            - allowed
        )

        if unknown:
            raise ValueError(
                "Unknown setting(s) in "
                f"[{name}] in {path}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

    @staticmethod
    def _positive_int(
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
                int,
            )
            or value <= 0
        ):
            raise ValueError(
                f"{name} in {path} "
                "must be a positive integer."
            )

    @staticmethod
    def _positive_number(
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
            or float(
                value
            ) <= 0.0
        ):
            raise ValueError(
                f"{name} in {path} "
                "must be greater than zero."
            )

    # ==========================================================
    # TOML
    # ==========================================================

    @classmethod
    def _encode_toml(
        cls,
        data: Mapping[str, Any],
    ) -> str:
        lines = [
            "# Nexora user engine settings",
            "# Only changed engine settings are stored here.",
            "",
        ]

        for section_name in (
            "timing",
            "debug",
            "audio",
            "audio_buffer",
        ):
            section = data.get(
                section_name
            )

            if (
                not isinstance(
                    section,
                    Mapping,
                )
                or not section
            ):
                continue

            lines.append(
                f"[{section_name}]"
            )

            for key, value in section.items():
                lines.append(
                    f"{key} = "
                    f"{cls._encode_value(value)}"
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