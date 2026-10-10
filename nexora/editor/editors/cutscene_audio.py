from __future__ import annotations

from pathlib import Path

from nexora.audio import AudioSource

from .cutscene_common import parse_float as _float


class CutsceneAudioMixin:

    def _resolve_audio_path(self, value: str | Path) -> Path:
        return self._asset_path(value)

    def _audio_reference(self, value: str) -> str:
        return str(self._resolve_audio_path(value).resolve())

    @staticmethod
    def _audio_path_from_value(value: object) -> str:
        if not isinstance(value, dict):
            return ""
        return str(
            value.get("path", value.get("asset", value.get("source", "")))
            or ""
        ).strip()

    def _preload_audio_tracks(self) -> None:
        self._audio_cache.clear()
        audio = self.game.audio
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                value = frame.value
                if not isinstance(value, dict):
                    continue
                path = self._audio_path_from_value(value)
                if not path:
                    continue
                if str(value.get("action", "play")).lower() in {"stop", "fade_out"}:
                    continue
                reference = self._audio_reference(path)
                if reference in self._audio_cache:
                    continue
                try:
                    loader = audio.load_stream if bool(value.get("stream", False)) else audio.load
                    self._audio_cache[reference] = loader(reference)
                except Exception as exc:
                    self.status = f"Audio unavailable: {Path(path).name} ({exc})"

    def _play_editor_audio(self, value: object, *, offset: float = 0.0) -> None:
        if not isinstance(value, dict):
            return
        path = self._audio_path_from_value(value)
        if not path:
            return

        audio = self.game.audio
        reference = self._audio_reference(path)
        action = str(value.get("action", "play")).lower()
        active = self._audio_sources.get(reference, [])
        if action in {"stop", "fade_out"}:
            for source in tuple(active):
                if action == "fade_out":
                    source.fade_out(max(0.0, _float(value.get("duration", 0.0))))
                else:
                    source.stop()
            return

        sound = self._audio_cache.get(reference)
        if sound is None:
            try:
                loader = audio.load_stream if bool(value.get("stream", False)) else audio.load
                sound = loader(reference)
                self._audio_cache[reference] = sound
            except Exception as exc:
                self.status = f"Could not play audio: {Path(path).name} ({exc})"
                return

        channel_name = str(value.get("channel", "sfx")).lower()
        bus = channel_name or "Master"
        bus_name = str(value.get("bus", channel_name.title()))
        try:
            bus = audio.get_bus(bus_name)
        except KeyError:
            bus = None
        source = AudioSource(
            sound,
            volume=max(0.0, min(1.0, _float(value.get("volume", 1.0), 1.0))),
            loop=bool(value.get("loop", False)),
            bus=bus,
        )
        audio.player.play(source)
        if offset > 0.0:
            duration = max(0.0, _float(getattr(sound, "duration", 0.0)))
            if bool(value.get("loop", False)) and duration > 0.0:
                offset %= duration
            if offset > 0.0:
                source.seek_seconds(offset)
        self._audio_sources.setdefault(reference, []).append(source)
        fade_in = _float(value.get("fade_in", 0.0), 0.0)
        if fade_in > 0.0:
            source.fade_in(fade_in)

    def _start_audio_at_playhead(self) -> None:
        """Start sounds that are already active at the current playhead."""

        states: dict[str, tuple[dict, float]] = {}
        frames: list[tuple[float, dict]] = []
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                if frame.time <= self.player.time and isinstance(frame.value, dict):
                    frames.append((frame.time, frame.value))

        for frame_time, value in sorted(frames, key=lambda item: item[0]):
            path = self._audio_path_from_value(value)
            if not path:
                continue
            reference = self._audio_reference(path)
            action = str(value.get("action", "play")).lower()
            if action in {"stop", "fade_out"}:
                states.pop(reference, None)
            else:
                states[reference] = (value, frame_time)

        for value, frame_time in states.values():
            path = self._audio_path_from_value(value)
            reference = self._audio_reference(path)
            sound = self._audio_cache.get(reference)
            if sound is None:
                continue
            offset = max(0.0, self.player.time - frame_time)
            duration = max(0.0, _float(getattr(sound, "duration", 0.0)))
            if not bool(value.get("loop", False)) and duration > 0.0 and offset >= duration:
                continue
            self._play_editor_audio(value, offset=offset)

    def _trigger_audio_between(self, start: float, end: float) -> None:
        if end < start:
            return
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                if start < frame.time <= end:
                    self._play_editor_audio(frame.value)

    def _prune_editor_audio(self) -> None:
        audio = self.game.audio
        for reference, sources in tuple(self._audio_sources.items()):
            alive = []
            for source in sources:
                if source.stopped:
                    audio.player.remove(source)
                else:
                    alive.append(source)
            if alive:
                self._audio_sources[reference] = alive
            else:
                self._audio_sources.pop(reference, None)

    def _pause_editor_audio(self) -> None:
        for sources in self._audio_sources.values():
            for source in sources:
                source.pause()

    def _resume_editor_audio(self) -> None:
        for sources in self._audio_sources.values():
            for source in sources:
                source.resume()

    def _stop_editor_audio(self) -> None:
        if self.game.engine is None:
            self._audio_cache.clear()
            self._audio_sources.clear()
            return
        audio = self.game.audio
        for sources in self._audio_sources.values():
            for source in sources:
                source.stop()
                audio.player.remove(source)
        self._audio_sources.clear()
        self._audio_cache.clear()
