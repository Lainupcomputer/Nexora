from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InspectorProperty:
    """Declarative description of one editor-visible property."""

    key: str
    label: str
    path: str
    kind: str = "text"
    group: str = "General"
    editable: bool = True
    decimals: int = 3

    def __post_init__(self) -> None:
        if self.kind not in {
            "text",
            "bool",
            "float",
            "int",
        }:
            raise ValueError(
                f"Unsupported inspector property kind: {self.kind!r}"
            )
