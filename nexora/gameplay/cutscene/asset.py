from __future__ import annotations

"""Data-only, versioned Nexora cutscene resources.

Cutscenes deliberately store references and primitive values instead of live
Nodes, callbacks or audio objects.  This keeps ``.ncutscene`` files safe to
load, portable between editor and game runtime, and easy to migrate later.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CUTSCENE_ASSET_VERSION = 1
CUTSCENE_ASSET_SUFFIX = ".ncutscene"
CUTSCENE_ASSET_MAX_PAYLOAD = 64 * 1024 * 1024

TRACK_TYPES = (
    "image",
    "camera",
    "fade",
    "audio",
    "effect",
    "event",
)
INTERPOLATIONS = ("step", "linear", "ease_in", "ease_out", "ease_in_out")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clean_time(value: Any) -> float:
    return max(0.0, _number(value))


def _primitive(value: Any) -> Any:
    """Return a primitive copy suitable for the secure save codec."""

    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    raise TypeError(f"Cutscene values must be primitive, got {type(value)!r}.")


@dataclass(slots=True)
class CutsceneKeyframe:
    """One value change on a cutscene track."""

    time: float = 0.0
    value: Any = field(default_factory=dict)
    interpolation: str = "step"

    def __post_init__(self) -> None:
        self.time = _clean_time(self.time)
        self.interpolation = (
            str(self.interpolation).strip().lower()
            if self.interpolation
            else "step"
        )
        if self.interpolation not in INTERPOLATIONS:
            self.interpolation = "step"
        self.value = _primitive(self.value)

    def to_state(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "value": _primitive(self.value),
            "interpolation": self.interpolation,
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "CutsceneKeyframe":
        return cls(
            time=state.get("time", 0.0),
            value=state.get("value", {}),
            interpolation=state.get("interpolation", "step"),
        )


@dataclass(slots=True)
class CutsceneTrack:
    """A named, typed sequence of keyframes."""

    name: str
    track_type: str = "image"
    target: str = ""
    enabled: bool = True
    keyframes: list[CutsceneKeyframe] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip() or "Track"
        self.track_type = str(self.track_type).strip().lower()
        if self.track_type not in TRACK_TYPES:
            self.track_type = "image"
        self.target = str(self.target or "")
        self.enabled = bool(self.enabled)
        self.keyframes = [
            frame if isinstance(frame, CutsceneKeyframe) else CutsceneKeyframe.from_state(dict(frame))
            for frame in self.keyframes
        ]
        self.sort_keyframes()

    def add_keyframe(self, keyframe: CutsceneKeyframe) -> CutsceneKeyframe:
        self.keyframes.append(keyframe)
        self.sort_keyframes()
        return keyframe

    def sort_keyframes(self) -> None:
        self.keyframes.sort(key=lambda frame: frame.time)

    def to_state(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.track_type,
            "target": self.target,
            "enabled": self.enabled,
            "keyframes": [frame.to_state() for frame in self.keyframes],
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "CutsceneTrack":
        return cls(
            name=state.get("name", "Track"),
            track_type=state.get("type", state.get("track_type", "image")),
            target=state.get("target", ""),
            enabled=state.get("enabled", True),
            keyframes=[
                CutsceneKeyframe.from_state(dict(frame))
                for frame in state.get("keyframes", [])
                if isinstance(frame, dict)
            ],
        )


@dataclass(slots=True)
class CutsceneAsset:
    """A complete data-only cutscene timeline."""

    name: str = "Untitled Cutscene"
    duration: float = 10.0
    fps: float = 60.0
    tracks: list[CutsceneTrack] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip() or "Untitled Cutscene"
        self.duration = max(0.1, _number(self.duration, 10.0))
        self.fps = max(1.0, _number(self.fps, 60.0))
        self.tracks = [
            track if isinstance(track, CutsceneTrack) else CutsceneTrack.from_state(dict(track))
            for track in self.tracks
        ]
        self.metadata = dict(self.metadata or {})

    def add_track(self, track: CutsceneTrack) -> CutsceneTrack:
        self.tracks.append(track)
        return track

    def to_state(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration": self.duration,
            "fps": self.fps,
            "tracks": [track.to_state() for track in self.tracks],
            "metadata": _primitive(self.metadata),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "CutsceneAsset":
        if not isinstance(state, dict):
            raise ValueError("Payload is not Nexora Cutscene data.")
        return cls(
            name=state.get("name", "Untitled Cutscene"),
            duration=state.get("duration", 10.0),
            fps=state.get("fps", 60.0),
            tracks=[
                CutsceneTrack.from_state(dict(track))
                for track in state.get("tracks", [])
                if isinstance(track, dict)
            ],
            metadata=dict(state.get("metadata", {})),
        )

    def save(self, path: str | Path, *, signing_key: bytes | str) -> Path:
        from nexora.data.codecs import cutscene as cutscene_codec

        target = Path(path).expanduser()
        if target.suffix.lower() != CUTSCENE_ASSET_SUFFIX:
            target = Path(str(target) + CUTSCENE_ASSET_SUFFIX)
        return cutscene_codec.save(
            self,
            target,
            signing_key=signing_key,
            max_file_size=CUTSCENE_ASSET_MAX_PAYLOAD,
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        signing_key: bytes | str,
    ) -> "CutsceneAsset":
        from nexora.data.codecs import cutscene as cutscene_codec

        return cutscene_codec.load(
            path,
            signing_key=signing_key,
            max_file_size=CUTSCENE_ASSET_MAX_PAYLOAD,
        )


__all__ = [
    "CUTSCENE_ASSET_MAX_PAYLOAD",
    "CUTSCENE_ASSET_SUFFIX",
    "CUTSCENE_ASSET_VERSION",
    "INTERPOLATIONS",
    "TRACK_TYPES",
    "CutsceneAsset",
    "CutsceneKeyframe",
    "CutsceneTrack",
]
