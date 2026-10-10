from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from nexora.core.settings.toml_store import TomlSettingsStore


class EngineSettingsStore(
    TomlSettingsStore
):
    FILE_NAME = "engine.toml"

    USER_HEADER = (
        "# Nexora user engine settings\n"
        "# Only changed engine settings are stored here.\n"
    )

    SETTINGS_NAME = "engine"
    REQUIRED_SECTIONS = {
        "timing": {"target_fps", "fixed_delta_time"},
        "debug": {"overlay"},
        "audio": {"frequency", "channels"},
        "audio_buffer": {"target_queue_frames", "max_update_frames"},
    }

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @classmethod
    def _validate_layer(
        cls,
        data: Mapping[str, Any],
        path: Path,
    ) -> None:
        cls._check_unknown_sections(
            data,
            {"timing", "debug", "audio", "audio_buffer"},
            path,
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

        cls._check_unknown(
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

        cls._check_unknown(
            section,
            {
                "overlay",
            },
            "debug",
            path,
        )

        if "overlay" in section:
            cls._boolean(
                section["overlay"],
                "debug.overlay",
                path,
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

        cls._check_unknown(
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

        cls._check_unknown(
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
    # TOML
    # ==========================================================

    @classmethod
    def _encode_toml(
        cls,
        data: Mapping[str, Any],
    ) -> str:
        return cls._encode_flat_sections(
            data,
            ("timing", "debug", "audio", "audio_buffer"),
        )
