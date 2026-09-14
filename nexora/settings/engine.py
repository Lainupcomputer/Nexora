from __future__ import annotations

from copy import deepcopy
from typing import Any

from nexora.settings.engine_store import (
    EngineSettingsStore,
)


class EngineSection:
    """
    Attribute-based access to one engine settings section.

    Examples:

        settings.timing.target_fps
        settings.debug.overlay

        settings.audio.frequency
        settings.audio.channels

        settings.audio_buffer.target_queue_frames
        settings.audio_buffer.max_update_frames
    """

    __slots__ = (
        "_settings",
        "_path",
    )

    def __init__(
        self,
        settings: "EngineSettings",
        path: str,
    ) -> None:
        object.__setattr__(
            self,
            "_settings",
            settings,
        )

        object.__setattr__(
            self,
            "_path",
            path,
        )

    # ==========================================================
    # GET
    # ==========================================================

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        if name.startswith(
            "_"
        ):
            raise AttributeError(
                name
            )

        full_path = (
            f"{self._path}.{name}"
        )

        value = (
            self._settings.get(
                full_path
            )
        )

        if isinstance(
            value,
            dict,
        ):
            return EngineSection(
                self._settings,
                full_path,
            )

        return value

    # ==========================================================
    # SET
    # ==========================================================

    def __setattr__(
        self,
        name: str,
        value: Any,
    ) -> None:
        if name.startswith(
            "_"
        ):
            object.__setattr__(
                self,
                name,
                value,
            )

            return

        self._settings.set(
            f"{self._path}.{name}",
            value,
        )


class EngineSettings:
    """
    Runtime facade for Nexora engine settings.

    Defaults:

        nexora/core/defaults/engine.toml

    User overrides:

        Documents/<project_name>/settings/engine.toml
    """

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        autosave: bool = True,
    ) -> None:
        # ======================================================
        # Store
        # ======================================================

        self.store = (
            EngineSettingsStore(
                project_name=(
                    project_name
                )
            )
        )

        # ======================================================
        # Runtime
        # ======================================================

        self.autosave = bool(
            autosave
        )

        self._data: dict[
            str,
            Any,
        ] = {}

        self._user_data: dict[
            str,
            Any,
        ] = {}

        # ======================================================
        # Sections
        # ======================================================

        self.timing = (
            EngineSection(
                self,
                "timing",
            )
        )

        self.debug = (
            EngineSection(
                self,
                "debug",
            )
        )

        self.audio = (
            EngineSection(
                self,
                "audio",
            )
        )

        self.audio_buffer = (
            EngineSection(
                self,
                "audio_buffer",
            )
        )

        # ======================================================
        # Load
        # ======================================================

        self.reload()

    # ==========================================================
    # DATA
    # ==========================================================

    @property
    def data(
        self,
    ) -> dict[str, Any]:
        return deepcopy(
            self._data
        )

    @property
    def user_data(
        self,
    ) -> dict[str, Any]:
        return deepcopy(
            self._user_data
        )

    @property
    def settings_path(
        self,
    ):
        return (
            self.store.settings_path
        )

    @property
    def engine_path(
        self,
    ):
        return (
            self.store.user_path
        )

    # ==========================================================
    # RELOAD
    # ==========================================================

    def reload(
        self,
    ) -> None:
        self._data = (
            self.store.load()
        )

        self._user_data = (
            self.store.load_user()
        )

    # ==========================================================
    # GET
    # ==========================================================

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        parts = (
            self._split_key(
                key
            )
        )

        current: Any = (
            self._data
        )

        for part in parts:
            if not isinstance(
                current,
                dict,
            ):
                return default

            if part not in current:
                return default

            current = current[
                part
            ]

        return current

    # ==========================================================
    # SET
    # ==========================================================

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        parts = (
            self._split_key(
                key
            )
        )

        self._set_nested(
            self._user_data,
            parts,
            value,
        )

        if self.autosave:
            self.save()

        else:
            self._set_nested(
                self._data,
                parts,
                value,
            )

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(
        self,
    ) -> None:
        self.store.save_user(
            self._user_data
        )

        self.reload()

    # ==========================================================
    # RESET
    # ==========================================================

    def reset_user(
        self,
    ) -> None:
        self.store.reset_user()

        self.reload()

    def remove_override(
        self,
        key: str,
    ) -> bool:
        parts = (
            self._split_key(
                key
            )
        )

        current = (
            self._user_data
        )

        for part in parts[:-1]:
            child = current.get(
                part
            )

            if not isinstance(
                child,
                dict,
            ):
                return False

            current = child

        final = (
            parts[-1]
        )

        if final not in current:
            return False

        del current[
            final
        ]

        self._remove_empty_sections(
            self._user_data
        )

        if self.autosave:
            self.save()

        else:
            self.reload()

        return True

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _split_key(
        key: str,
    ) -> list[str]:
        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "Engine setting key must be a string."
            )

        parts = [
            part
            for part in key.split(
                "."
            )
            if part
        ]

        if not parts:
            raise ValueError(
                "Engine setting key cannot be empty."
            )

        return parts

    @staticmethod
    def _set_nested(
        target: dict[str, Any],
        parts: list[str],
        value: Any,
    ) -> None:
        current = target

        for part in parts[:-1]:
            child = current.get(
                part
            )

            if not isinstance(
                child,
                dict,
            ):
                child = {}

                current[
                    part
                ] = child

            current = child

        current[
            parts[-1]
        ] = value

    @classmethod
    def _remove_empty_sections(
        cls,
        data: dict[str, Any],
    ) -> None:
        for key in list(
            data
        ):
            value = data[
                key
            ]

            if isinstance(
                value,
                dict,
            ):
                cls._remove_empty_sections(
                    value
                )

                if not value:
                    del data[
                        key
                    ]