from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from nexora.core.settings.toml_store import TomlSettingsStore


class GraphicsSettingsStore(
    TomlSettingsStore
):
    """
    Layered TOML storage for graphics settings.

    Layer order:

        engine defaults
        project settings
        mods
        user settings

    Later layers override earlier layers.

    Graphics settings use a deep merge, so a layer may override
    only one value without replacing the rest of its section.
    """

    FILE_NAME = "graphics.toml"

    USER_HEADER = (
        "# Nexora user graphics settings\n"
        "# Only changed graphics settings are stored here.\n"
    )


    SETTINGS_NAME = "graphics"
    REQUIRED_SECTIONS = {
        "window": {"width", "height", "mode", "resizable"},
        "rendering": {"vsync", "frames_in_flight"},
        "post_processing": {
            "enabled", "brightness", "contrast", "saturation", "film_grain"
        },
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
            {"window", "rendering", "post_processing"},
            path,
        )

        window = data.get(
            "window"
        )

        if window is not None:
            cls._validate_window(
                window,
                path,
            )

        rendering = data.get(
            "rendering"
        )

        if rendering is not None:
            cls._validate_rendering(
                rendering,
                path,
            )

        post = data.get(
            "post_processing"
        )

        if post is not None:
            cls._validate_post_processing(
                post,
                path,
            )

    @classmethod
    def _validate_window(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "window",
            path,
        )
        assert isinstance(section, dict)

        allowed = {
            "width",
            "height",
            "mode",
            "resizable",
        }

        cls._check_unknown(
            section,
            allowed,
            "window",
            path,
        )

        if "width" in section:
            cls._positive_int(
                section["width"],
                "window.width",
                path,
            )

        if "height" in section:
            cls._positive_int(
                section["height"],
                "window.height",
                path,
            )

        if "mode" in section:
            mode = section[
                "mode"
            ]

            if mode not in {
                "windowed",
                "borderless",
                "fullscreen",
            }:
                raise ValueError(
                    "window.mode in "
                    f"{path} must be one of: "
                    "windowed, borderless, fullscreen"
                )

        if "resizable" in section:
            cls._boolean(
                section["resizable"],
                "window.resizable",
                path,
            )

    @classmethod
    def _validate_rendering(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "rendering",
            path,
        )
        assert isinstance(section, dict)

        allowed = {
            "vsync",
            "frames_in_flight",
        }

        cls._check_unknown(
            section,
            allowed,
            "rendering",
            path,
        )

        if "vsync" in section:
            cls._boolean(
                section["vsync"],
                "rendering.vsync",
                path,
            )

        if "frames_in_flight" in section:
            value = section[
                "frames_in_flight"
            ]

            cls._positive_int(
                value,
                "rendering.frames_in_flight",
                path,
            )

            if not 1 <= value <= 3:
                raise ValueError(
                    "rendering.frames_in_flight "
                    f"in {path} must be between 1 and 3."
                )

    @classmethod
    def _validate_post_processing(
        cls,
        section: object,
        path: Path,
    ) -> None:
        cls._require_table(
            section,
            "post_processing",
            path,
        )
        assert isinstance(section, dict)

        allowed = {
            "enabled",
            "brightness",
            "contrast",
            "saturation",
            "film_grain",
        }

        cls._check_unknown(
            section,
            allowed,
            "post_processing",
            path,
        )

        if "enabled" in section:
            cls._boolean(
                section["enabled"],
                "post_processing.enabled",
                path,
            )

        for key in (
            "brightness",
            "contrast",
            "saturation",
        ):
            if key not in section:
                continue

            value = cls._number(
                section[key],
                f"post_processing.{key}",
                path,
            )

            if value < 0.0:
                raise ValueError(
                    f"post_processing.{key} "
                    f"in {path} must be >= 0.0."
                )

        if "film_grain" in section:
            value = cls._number(
                section["film_grain"],
                "post_processing.film_grain",
                path,
            )

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    "post_processing.film_grain "
                    f"in {path} must be between "
                    "0.0 and 1.0."
                )

    # ==========================================================
    # TOML ENCODING
    # ==========================================================

    @classmethod
    def _encode_toml(
        cls,
        data: Mapping[str, Any],
    ) -> str:
        return cls._encode_flat_sections(
            data,
            ("window", "rendering", "post_processing"),
            {
                "window": ("width", "height", "mode", "resizable"),
                "rendering": ("vsync", "frames_in_flight"),
                "post_processing": (
                    "enabled",
                    "brightness",
                    "contrast",
                    "saturation",
                    "film_grain",
                ),
            },
        )
