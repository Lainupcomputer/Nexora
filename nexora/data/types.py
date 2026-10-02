from __future__ import annotations

from enum import StrEnum


class DataType(StrEnum):
    """Nexora-owned binary document types."""

    Item = "item"
    Scene = "scene"
    Prefab = "prefab"
    Cutscene = "cutscene"
    TileMap = "tilemap"
    SaveGame = "savegame"
    AudioPreset = "audio_preset"
    AudioMixer = "audio_mixer"


__all__ = ["DataType"]
