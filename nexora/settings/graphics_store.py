from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Iterable, Mapping

from nexora.settings.layered_store import (
    LayeredSettingsStore,
)


class GraphicsSettingsStore(
    LayeredSettingsStore[dict[str, Any]]
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
            "project_name": project_name,
            "defaults_path": defaults_path,
            "project_path": project_path,
            "mod_paths": mod_paths,
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
                    "Graphics settings file not found: "
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
                f"Invalid graphics settings file: {path}"
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
        path = (
            self.user_path
            or Path(
                self.FILE_NAME
            )
        )

        self._validate_layer(
            data,
            path,
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
                isinstance(current, dict)
                and isinstance(value, Mapping)
            ):
                cls._deep_merge(
                    current,
                    value,
                )

            else:
                target[key] = deepcopy(
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
        allowed_sections = {
            "window",
            "rendering",
            "post_processing",
        }

        unknown_sections = (
            set(data)
            - allowed_sections
        )

        if unknown_sections:
            raise ValueError(
                "Unknown graphics section(s) in "
                f"{path}: "
                + ", ".join(
                    sorted(
                        unknown_sections
                    )
                )
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
        if not isinstance(
            section,
            dict,
        ):
            raise ValueError(
                f"[window] in {path} must be a TOML table."
            )

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
        if not isinstance(
            section,
            dict,
        ):
            raise ValueError(
                f"[rendering] in {path} must be a TOML table."
            )

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
        if not isinstance(
            section,
            dict,
        ):
            raise ValueError(
                "[post_processing] in "
                f"{path} must be a TOML table."
            )

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

    @classmethod
    def _validate_complete(
        cls,
        data: Mapping[str, Any],
    ) -> None:
        required = {
            "window": {
                "width",
                "height",
                "mode",
                "resizable",
            },
            "rendering": {
                "vsync",
                "frames_in_flight",
            },
            "post_processing": {
                "enabled",
                "brightness",
                "contrast",
                "saturation",
                "film_grain",
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
                    "Missing graphics section: "
                    f"{section_name}"
                )

            missing = (
                keys
                - set(section)
            )

            if missing:
                raise ValueError(
                    "Missing graphics setting(s) in "
                    f"[{section_name}]: "
                    + ", ".join(
                        sorted(
                            missing
                        )
                    )
                )

    # ==========================================================
    # VALIDATION HELPERS
    # ==========================================================

    @staticmethod
    def _check_unknown(
        section: Mapping[str, Any],
        allowed: set[str],
        section_name: str,
        path: Path,
    ) -> None:
        unknown = (
            set(section)
            - allowed
        )

        if unknown:
            raise ValueError(
                "Unknown setting(s) in "
                f"[{section_name}] in {path}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

    @staticmethod
    def _boolean(
        value: object,
        name: str,
        path: Path,
    ) -> None:
        if not isinstance(
            value,
            bool,
        ):
            raise ValueError(
                f"{name} in {path} must be a boolean."
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
                f"{name} in {path} must be a positive integer."
            )

    @staticmethod
    def _number(
        value: object,
        name: str,
        path: Path,
    ) -> float:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise ValueError(
                f"{name} in {path} must be a number."
            )

        return float(
            value
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
            "# Nexora user graphics settings",
            "# Only user overrides are stored here.",
            "",
        ]

        section_order = (
            "window",
            "rendering",
            "post_processing",
        )

        key_order = {
            "window": (
                "width",
                "height",
                "mode",
                "resizable",
            ),
            "rendering": (
                "vsync",
                "frames_in_flight",
            ),
            "post_processing": (
                "enabled",
                "brightness",
                "contrast",
                "saturation",
                "film_grain",
            ),
        }

        for section_name in section_order:
            section = data.get(
                section_name
            )

            if not isinstance(
                section,
                Mapping,
            ):
                continue

            if not section:
                continue

            lines.append(
                f"[{section_name}]"
            )

            for key in key_order[
                section_name
            ]:
                if key not in section:
                    continue

                lines.append(
                    f"{key} = "
                    f"{cls._encode_value(section[key])}"
                )

            lines.append(
                ""
            )

        return (
            "\n".join(lines).rstrip()
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
            str,
        ):
            escaped = (
                value
                .replace(
                    "\\",
                    "\\\\",
                )
                .replace(
                    '"',
                    '\\"',
                )
            )

            return (
                f'"{escaped}"'
            )

        if isinstance(
            value,
            (int, float),
        ):
            return repr(
                value
            )

        raise TypeError(
            "Unsupported TOML value: "
            f"{type(value).__name__}"
        )