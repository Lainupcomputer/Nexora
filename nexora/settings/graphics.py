from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from nexora.settings.graphics_store import (
    GraphicsSettingsStore,
)


class GraphicsSection:
    """
    Attribute proxy for one graphics settings section.

    Example:

        graphics.window.width
        graphics.rendering.vsync
    """

    __slots__ = (
        "_graphics",
        "_section",
    )

    def __init__(
        self,
        graphics: "GraphicsSettings",
        section: str,
    ) -> None:
        object.__setattr__(
            self,
            "_graphics",
            graphics,
        )

        object.__setattr__(
            self,
            "_section",
            section,
        )

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

        return self._graphics.get(
            f"{self._section}.{name}"
        )

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

        self._graphics.set(
            f"{self._section}.{name}",
            value,
        )


class GraphicsSettings:
    """
    Runtime graphics settings facade.

    Provides:

        graphics.window.width
        graphics.window.height
        graphics.window.mode
        graphics.window.resizable

        graphics.rendering.vsync
        graphics.rendering.frames_in_flight

        graphics.post_processing.enabled
        graphics.post_processing.brightness
        graphics.post_processing.contrast
        graphics.post_processing.saturation
        graphics.post_processing.film_grain
    """

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        settings_path=...,
        defaults_path: str | Path | None = None,
        project_path: str | Path | None = None,
        mod_paths: Iterable[str | Path] = (),
        autosave: bool = True,
    ) -> None:
        store_kwargs = {
            "project_name": (
                project_name
            ),
            "defaults_path": (
                defaults_path
            ),
            "project_path": (
                project_path
            ),
            "mod_paths": (
                mod_paths
            ),
        }

        if settings_path is not ...:
            store_kwargs[
                "settings_path"
            ] = settings_path

        self.store = (
            GraphicsSettingsStore(
                **store_kwargs
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

        self.window = (
            GraphicsSection(
                self,
                "window",
            )
        )

        self.rendering = (
            GraphicsSection(
                self,
                "rendering",
            )
        )

        self.post_processing = (
            GraphicsSection(
                self,
                "post_processing",
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

    @property
    def settings_path(
        self,
    ) -> Path | None:
        return (
            self.store.settings_path
        )

    @property
    def graphics_path(
        self,
    ) -> Path | None:
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
            value = current.get(
                part
            )

            if not isinstance(
                value,
                dict,
            ):
                return False

            current = value

        final = parts[-1]

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
    # GPU CREATION
    # ==========================================================

    def gpu_context_kwargs(
        self,
    ) -> dict[str, Any]:
        """
        Settings needed when GPUContext is created.

        frames_in_flight and resizable belong here because they
        are startup-oriented settings.
        """

        return {
            "width": int(
                self.window.width
            ),
            "height": int(
                self.window.height
            ),
            "window_mode": str(
                self.window.mode
            ),
            "resizable": bool(
                self.window.resizable
            ),
            "vsync": bool(
                self.rendering.vsync
            ),
            "frames_in_flight": int(
                self.rendering.frames_in_flight
            ),
        }

    # ==========================================================
    # POST PROCESSING
    # ==========================================================

    def apply_post_processing(
        self,
        renderer,
    ) -> None:
        post = (
            renderer.post_processing
        )

        post.enabled = bool(
            self.post_processing.enabled
        )

        post.brightness = max(
            0.0,
            float(
                self.post_processing.brightness
            ),
        )

        post.contrast = max(
            0.0,
            float(
                self.post_processing.contrast
            ),
        )

        post.saturation = max(
            0.0,
            float(
                self.post_processing.saturation
            ),
        )

        post.film_grain = max(
            0.0,
            min(
                1.0,
                float(
                    self.post_processing.film_grain
                ),
            ),
        )

    # ==========================================================
    # RUNTIME APPLY
    # ==========================================================

    def apply_runtime(
        self,
        context,
        renderer=None,
    ) -> None:
        """
        Apply settings that Nexora can safely change at runtime.

        frames_in_flight and resizable are not changed here.
        They are applied during GPUContext creation.
        """

        context.resize(
            int(
                self.window.width
            ),
            int(
                self.window.height
            ),
        )

        context.set_window_mode(
            str(
                self.window.mode
            )
        )

        context.set_vsync(
            bool(
                self.rendering.vsync
            )
        )

        if renderer is not None:
            self.apply_post_processing(
                renderer
            )

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
                "Graphics setting key must be a string."
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
                "Graphics setting key cannot be empty."
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