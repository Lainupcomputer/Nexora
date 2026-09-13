from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    slots=True,
)
class TileMetadata:
    """
    Gameplay metadata attached to one TileSet tile.

    TileMetadata is intentionally independent from rendering.
    """

    solid: bool = False

    tags: set[str] = field(
        default_factory=set
    )

    properties: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    # ==============================================================
    # Tags
    # ==============================================================

    def add_tag(
        self,
        tag: str,
    ) -> None:
        tag = str(
            tag
        ).strip()

        if not tag:
            raise ValueError(
                "tag cannot be empty."
            )

        self.tags.add(
            tag
        )

    def remove_tag(
        self,
        tag: str,
    ) -> bool:
        if tag not in self.tags:
            return False

        self.tags.remove(
            tag
        )

        return True

    def has_tag(
        self,
        tag: str,
    ) -> bool:
        return (
            tag
            in self.tags
        )

    # ==============================================================
    # Properties
    # ==============================================================

    def set_property(
        self,
        key: str,
        value: Any,
    ) -> None:
        key = str(
            key
        ).strip()

        if not key:
            raise ValueError(
                "property key cannot be empty."
            )

        self.properties[
            key
        ] = value

    def get_property(
        self,
        key: str,
        default=None,
    ):
        return self.properties.get(
            key,
            default,
        )

    def remove_property(
        self,
        key: str,
    ) -> bool:
        if key not in self.properties:
            return False

        del self.properties[
            key
        ]

        return True