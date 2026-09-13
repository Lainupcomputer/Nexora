from __future__ import annotations

from enum import Enum


class AudioChannel(Enum):
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    AMBIENT = "ambient"
    VOICE = "voice"