from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from nexora.core.settings.graphics_store import (
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


from nexora.core.settings.facade import SettingsFacade

class GraphicsSettings(SettingsFacade):
    """Runtime graphics settings facade."""

    KEY_LABEL = "Graphics"

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
            "project_name": project_name,
            "defaults_path": defaults_path,
            "project_path": project_path,
            "mod_paths": mod_paths,
        }
        if settings_path is not ...:
            store_kwargs["settings_path"] = settings_path

        self._initialize_settings(
            GraphicsSettingsStore(**store_kwargs),
            autosave=autosave,
        )

        self.window = GraphicsSection(self, "window")
        self.rendering = GraphicsSection(self, "rendering")
        self.post_processing = GraphicsSection(self, "post_processing")

    @property
    def graphics_path(self) -> Path | None:
        return self.store.user_path

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
