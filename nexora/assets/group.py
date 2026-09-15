from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from nexora.assets.preload import FontAssetRequest, normalize_font_requests


@dataclass(slots=True, frozen=True)
class AssetGroupDefinition:
    """Declarative collection of assets that belong together.

    Dependencies are other registered group names. A group can share assets
    with any number of other groups; AssetManager reference-counts ownership
    and only releases a resource after the final active group stops using it.
    """

    name: str
    fonts: tuple[FontAssetRequest, ...] = ()
    sounds: tuple[str | Path, ...] = ()
    textures: tuple[str | Path, ...] = ()
    dependencies: tuple[str, ...] = ()
    persistent: bool = False

    @classmethod
    def create(
        cls,
        name: str,
        *,
        fonts: Iterable[FontAssetRequest | tuple[str | Path, float]] = (),
        sounds: Iterable[str | Path] = (),
        textures: Iterable[str | Path] = (),
        dependencies: Iterable[str] = (),
        persistent: bool = False,
    ) -> "AssetGroupDefinition":
        normalized_name = normalize_group_name(name)
        normalized_dependencies = tuple(
            normalize_group_name(dependency)
            for dependency in dependencies
        )

        if normalized_name in normalized_dependencies:
            raise ValueError(
                f"Asset group {normalized_name!r} cannot depend on itself."
            )

        if persistent and normalized_dependencies:
            raise ValueError(
                "Persistent asset groups cannot currently declare dependencies. "
                "Keep permanent shared assets in the persistent group itself."
            )

        return cls(
            name=normalized_name,
            fonts=tuple(normalize_font_requests(fonts)),
            sounds=tuple(sounds),
            textures=tuple(textures),
            dependencies=normalized_dependencies,
            persistent=bool(persistent),
        )


def normalize_group_name(name: str) -> str:
    normalized = str(name).strip().lower()
    if not normalized:
        raise ValueError("Asset group name cannot be empty.")
    return normalized
