from __future__ import annotations

from typing import Any

from nexora.core.settings.audio_store import (
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


from nexora.core.settings.facade import SettingsFacade

class AudioSettings(SettingsFacade):
    """Runtime audio settings facade."""

    KEY_LABEL = "Audio"
    VALIDATE_KEY_TYPE = False

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        settings_path=...,
        autosave: bool = True,
    ) -> None:
        self._initialize_settings(
            AudioSettingsStore(
                project_name=project_name,
                settings_path=settings_path,
            ),
            autosave=autosave,
        )
        self.buses = AudioSection(self, "buses")

    @classmethod
    def _remove_empty(cls, data: dict[str, Any]) -> None:
        """Compatibility alias for the previous private helper."""
        cls._remove_empty_sections(data)
