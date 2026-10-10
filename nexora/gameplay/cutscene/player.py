from __future__ import annotations

"""Runtime timeline evaluation for Nexora cutscenes."""

from collections.abc import Callable
from typing import Any

from .asset import CutsceneAsset, CutsceneKeyframe, CutsceneTrack


def _ease(value: float, name: str) -> float:
    value = max(0.0, min(1.0, float(value)))
    if name == "ease_in":
        return value * value
    if name == "ease_out":
        inverse = 1.0 - value
        return 1.0 - inverse * inverse
    if name == "ease_in_out":
        return 2.0 * value * value if value < 0.5 else 1.0 - ((-2.0 * value + 2.0) ** 2) / 2.0
    return value


def _interpolate(start: Any, end: Any, amount: float) -> Any:
    if isinstance(start, dict) and isinstance(end, dict):
        # Cutscene camera and fade values are structured dictionaries.  The
        # old implementation returned ``start`` for dictionaries, which made
        # every camera movement snap at the next keyframe instead of moving
        # smoothly between x/y/zoom values.
        result = dict(start)
        for key, end_value in end.items():
            if key in start:
                result[key] = _interpolate(start[key], end_value, amount)
            elif amount >= 1.0:
                result[key] = end_value
        return result
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return float(start) + (float(end) - float(start)) * amount
    if isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)) and len(start) == len(end):
        return [_interpolate(left, right, amount) for left, right in zip(start, end)]
    return start


class CutscenePlayer:
    """Small deterministic player that evaluates data-only tracks.

    Rendering and asset-specific behavior remain outside this class.  A game
    can consume :meth:`snapshot` and resolve image/audio references through
    its normal AssetManager and AudioSystem.
    """

    def __init__(
        self,
        asset: CutsceneAsset | None = None,
        *,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.asset = asset or CutsceneAsset()
        self.on_event = on_event
        self.time = 0.0
        self.playing = False
        self.loop = False
        self._event_cursor = 0.0

    @property
    def finished(self) -> bool:
        return not self.loop and self.time >= self.asset.duration

    def play(self, *, restart: bool = False) -> None:
        if restart:
            self.seek(0.0)
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def stop(self) -> None:
        self.playing = False
        self.seek(0.0)

    def seek(self, time: float) -> None:
        self.time = max(0.0, min(float(time), self.asset.duration))
        self._event_cursor = self.time

    def update(self, delta_time: float) -> None:
        if not self.playing:
            return
        previous = self.time
        self.time += max(0.0, float(delta_time))
        if self.loop and self.asset.duration > 0.0:
            while self.time >= self.asset.duration:
                self._emit_events(previous, self.asset.duration)
                self.time -= self.asset.duration
                previous = 0.0
                self._event_cursor = 0.0
        else:
            self.time = min(self.time, self.asset.duration)
            self._emit_events(previous, self.time)
            if self.time >= self.asset.duration:
                self.playing = False
        self._event_cursor = self.time

    def evaluate_track(self, track: CutsceneTrack, time: float | None = None) -> Any:
        if not track.enabled or not track.keyframes:
            return None
        current_time = self.time if time is None else max(0.0, float(time))
        frames = track.keyframes
        if current_time < frames[0].time:
            return None
        previous = frames[0]
        for following in frames[1:]:
            if current_time < following.time:
                if previous.interpolation == "step" or following.time <= previous.time:
                    return previous.value
                amount = (current_time - previous.time) / (following.time - previous.time)
                return _interpolate(previous.value, following.value, _ease(amount, previous.interpolation))
            previous = following
        return previous.value

    def snapshot(self, time: float | None = None) -> dict[str, Any]:
        return {
            track.name: self.evaluate_track(track, time)
            for track in self.asset.tracks
            if track.enabled
        }

    def _emit_events(self, start: float, end: float) -> None:
        if self.on_event is None or end < start:
            return
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "event":
                continue
            for frame in track.keyframes:
                if start < frame.time <= end and isinstance(frame.value, dict):
                    event_id = str(frame.value.get("id", "")).strip()
                    if event_id:
                        params = frame.value.get("parameters", {})
                        self.on_event(event_id, dict(params) if isinstance(params, dict) else {})


__all__ = ["CutscenePlayer"]
