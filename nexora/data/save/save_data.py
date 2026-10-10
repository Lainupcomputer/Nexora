from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True, frozen=True)
class SaveMetadata:
    """
    Metadata associated with a save game.
    """

    slot: str
    name: str
    timestamp: str
    playtime: float
    save_version: int

    @classmethod
    def create(
        cls,
        *,
        slot: str,
        name: str,
        playtime: float = 0.0,
        save_version: int = 1,
    ) -> SaveMetadata:
        return cls(
            slot=str(slot),
            name=str(name),
            timestamp=(
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            playtime=max(
                0.0,
                float(playtime),
            ),
            save_version=int(
                save_version
            ),
        )

    def to_dict(
        self,
    ) -> dict:
        return {
            "slot": self.slot,
            "name": self.name,
            "timestamp": self.timestamp,
            "playtime": self.playtime,
            "save_version": self.save_version,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> SaveMetadata:
        return cls(
            slot=str(
                data["slot"]
            ),
            name=str(
                data["name"]
            ),
            timestamp=str(
                data["timestamp"]
            ),
            playtime=float(
                data["playtime"]
            ),
            save_version=int(
                data["save_version"]
            ),
        )


@dataclass(slots=True)
class SaveGame:
    """
    Loaded save game.

    data intentionally contains only safe serializable values.
    """

    metadata: SaveMetadata
    data: dict[str, Any]