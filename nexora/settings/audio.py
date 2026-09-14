from __future__ import annotations

from copy import deepcopy
from typing import Any

from nexora.settings.audio_store import (
    AudioSettingsStore,
)


class AudioSection:
    """
    Attribute-based access to one audio section.
    """

    __slots__ = (
        "_settings",
        "_path",
    )

    def __init__(
        self,
        settings: "AudioSettings",
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

    def __getattr__(
        self,
        name: str,
    ) -> Any:
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
            return AudioSection(
                self._settings,
                full_path,
            )

        return value

    def __setattr__(
        self,
        name: str,
        value: Any,
    ) -> None:
        self._settings.set(
            f"{self._path}.{name}",
            value,
        )


class AudioSettings:
    """
    Runtime audio settings facade.

    Example:

        audio.volume.master = 0.8

        audio.buses.music.volume = 0.5
        audio.buses.music.muted = False
    """

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        autosave: bool = True,
    ) -> None:
        self.store = (
            AudioSettingsStore(
                project_name=(
                    project_name
                )
            )
        )

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

        self.volume = (
            AudioSection(
                self,
                "volume",
            )
        )

        self.buses = (
            AudioSection(
                self,
                "buses",
            )
        )

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
        parts = self._split_key(
            key
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
        parts = self._split_key(
            key
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
        parts = self._split_key(
            key
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

        self._remove_empty(
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
        parts = [
            part
            for part in key.split(
                "."
            )
            if part
        ]

        if not parts:
            raise ValueError(
                "Audio setting key cannot be empty."
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
    def _remove_empty(
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
                cls._remove_empty(
                    value
                )

                if not value:
                    del data[
                        key
                    ]