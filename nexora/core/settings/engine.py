from __future__ import annotations

from typing import Any

from nexora.core.settings.engine_store import (
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


from nexora.core.settings.facade import SettingsFacade

class EngineSettings(SettingsFacade):
    """
    Runtime facade for Nexora engine settings.

    Defaults:

        nexora/core/defaults/engine.toml

    User overrides:

        Documents/<project_name>/settings/engine.toml
    """

    KEY_LABEL = "Engine"

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        settings_path=...,
        autosave: bool = True,
    ) -> None:
        store = EngineSettingsStore(
            project_name=project_name,
            settings_path=settings_path,
        )
        self._initialize_settings(
            store,
            autosave=autosave,
        )

        self.timing = EngineSection(self, "timing")
        self.debug = EngineSection(self, "debug")
        self.audio = EngineSection(self, "audio")
        self.audio_buffer = EngineSection(self, "audio_buffer")

    @property
    def engine_path(self):
        return self.store.user_path
