from __future__ import annotations

"""Scene node that plays a serialized ``.ncutscene`` asset at runtime."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from nexora.audio import AudioSource
from nexora.nodes.camera import CinematicCamera2D
from nexora.nodes.effects import Light2D
from nexora.nodes.node import Node
from nexora.nodes.texture import AnimatedSprite

from .asset import CutsceneAsset, CutsceneTrack
from .player import CutscenePlayer


DEFAULT_CUTSCENE_SIGNING_KEY = (
    b"nexora-default-save-signing-key-"
    b"change-this-for-your-game"
)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp01(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _float(value, default)))


class CutscenePlayerNode(Node):
    """Play a ``.ncutscene`` timeline inside a normal Nexora scene.

    The node owns a runtime sprite and a :class:`CinematicCamera2D`.  Those
    children are deliberately marked as runtime-only so they are not written
    back into the scene file; the node itself only stores the cutscene path
    and playback settings.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.asset_path: str | None = None
        self.autoplay = False
        self.play_on_enter = False
        self.loop = False

        self.started = self.create_signal(f"{name}.cutscene_started")
        self.paused = self.create_signal(f"{name}.cutscene_paused")
        self.finished = self.create_signal(f"{name}.cutscene_finished")
        self.event = self.create_signal(f"{name}.cutscene_event")
        self.error = self.create_signal(f"{name}.cutscene_error")

        self._asset: CutsceneAsset | None = None
        self._player: CutscenePlayer | None = None
        self._sprite: AnimatedSprite | None = None
        self._camera: CinematicCamera2D | None = None
        self._light: Light2D | None = None
        self._renderer = None
        self._assets = None
        self._audio = None
        self._scene = None
        self._scene_path: str | None = None
        self._signing_key: bytes | str = DEFAULT_CUTSCENE_SIGNING_KEY
        self._audio_cache: dict[str, Any] = {}
        self._audio_sources: list[AudioSource] = []
        self._active_audio_sources: dict[str, list[AudioSource]] = {}
        self._event_handlers: dict[str, list[Callable[..., Any]]] = {}
        self._active_image_source: str | None = None
        self._last_time = 0.0
        self._finished_emitted = False

    @property
    def asset(self) -> CutsceneAsset | None:
        return self._asset

    @property
    def player(self) -> CutscenePlayer | None:
        return self._player

    @property
    def sprite(self) -> AnimatedSprite | None:
        return self._sprite

    @property
    def camera(self) -> CinematicCamera2D | None:
        return self._camera

    @property
    def playing(self) -> bool:
        return bool(self._player and self._player.playing)

    @property
    def time(self) -> float:
        return 0.0 if self._player is None else self._player.time

    def build(
        self,
        *,
        renderer,
        assets,
        audio=None,
        scene=None,
        signing_key: bytes | str | None = None,
        asset_path: str | Path | None = None,
        scene_path: str | Path | None = None,
    ) -> None:
        """Bind runtime services, load the cutscene and create its children."""

        self._renderer = renderer
        self._assets = assets
        self._audio = audio
        self._scene = scene
        if scene_path is not None:
            self._scene_path = str(scene_path)
        if signing_key is not None:
            self._signing_key = signing_key
        if asset_path is not None:
            self.asset_path = str(asset_path)

        if not self.asset_path:
            raise ValueError("CutscenePlayerNode requires an asset_path.")

        path = self._resolve_asset_path(self.asset_path)
        asset = CutsceneAsset.load(path, signing_key=self._signing_key)
        self._asset = asset
        self._player = CutscenePlayer(asset, on_event=self._on_event)
        self._player.loop = bool(self.loop)
        self._audio_cache.clear()
        self._active_image_source = None
        self._stop_audio_sources()
        self._remove_runtime_children()

        sprite = AnimatedSprite(f"{self.name}_Image", self.world)
        sprite.origin = (0.5, 0.5)
        sprite.width = 640.0
        sprite.height = 360.0
        viewport_width = _float(getattr(self._renderer, "width", 640.0), 640.0)
        viewport_height = _float(getattr(self._renderer, "height", 360.0), 360.0)
        artwork_scale = max(viewport_width / 640.0, viewport_height / 360.0) * 1.16
        sprite.width = 640.0 * artwork_scale
        sprite.height = 360.0 * artwork_scale
        sprite._nexora_runtime_only = True
        self.add_child(sprite)
        self._sprite = sprite

        light_state = self._asset.metadata.get("light") if asset.metadata else None
        if isinstance(light_state, dict):
            light = Light2D(f"{self.name}_Light", self.world)
            light._nexora_runtime_only = True
            light.color = tuple(light_state.get("color", (1.0, 0.48, 0.12))[:3])
            light.radius = _float(light_state.get("radius", 68.0), 68.0) * artwork_scale
            light.intensity = _float(light_state.get("intensity", 0.95), 0.95)
            light.falloff = _float(light_state.get("falloff", 1.7), 1.7)
            light.flicker_enabled = bool(light_state.get("flicker", True))
            light.flicker_strength = _float(light_state.get("flicker_strength", 0.16), 0.16)
            light.flicker_speed = _float(light_state.get("flicker_speed", 11.5), 11.5)
            anchor = light_state.get("anchor", (96.0, 178.0))
            if isinstance(anchor, (list, tuple)) and len(anchor) >= 2:
                light.transform.x = (_float(anchor[0]) - 320.0) * artwork_scale
                light.transform.y = (_float(anchor[1]) - 180.0) * artwork_scale
            self.add_child(light)
            self._light = light

        camera = CinematicCamera2D(
            f"{self.name}_Camera",
            self.world,
            self._renderer,
        )
        camera._nexora_runtime_only = True
        self.add_child(camera)
        self._camera = camera

        if self._scene is not None:
            self._scene.set_camera(camera)

        self._preload_audio_tracks()
        self._apply_tracks()
        if self.autoplay or self.play_on_enter:
            self.play(restart=True)

    def load_asset(self, path: str | Path) -> None:
        """Update the asset path and rebuild when services are already bound."""

        self.asset_path = str(path)
        if self._renderer is not None and self._assets is not None:
            self.build(
                renderer=self._renderer,
                assets=self._assets,
                audio=self._audio,
                scene=self._scene,
                signing_key=self._signing_key,
                scene_path=self._scene_path,
            )

    def play(self, *, restart: bool = False) -> None:
        if self._player is None:
            raise RuntimeError("CutscenePlayerNode is not built.")
        was_playing = self._player.playing
        self._player.play(restart=restart)
        self._finished_emitted = False
        if restart:
            self._last_time = 0.0
            self._apply_tracks()
            self._trigger_audio_between(-1e-9, 0.0)
            self._trigger_effects_between(-1e-9, 0.0)
        if not was_playing:
            self.started.emit(self)

    def pause(self) -> None:
        if self._player is None:
            return
        if self._player.playing:
            self._player.pause()
            self.paused.emit(self)

    def stop(self) -> None:
        if self._player is None:
            return
        self._player.stop()
        self._last_time = 0.0
        self._finished_emitted = False
        self._stop_audio_sources()
        self._reset_camera_effects()
        self._apply_tracks()

    def seek(self, time: float) -> None:
        if self._player is None:
            return
        self._player.seek(time)
        self._last_time = self._player.time
        self._reset_camera_effects()
        self._apply_tracks()
        self._trigger_effects_between(-1e-9, self._player.time)
        self._apply_tracks()

    def restart(self) -> None:
        self.play(restart=True)

    def register_event(self, event_id: str, callback: Callable[..., Any]) -> None:
        """Register a runtime callback; callbacks are never serialized."""

        key = str(event_id).strip()
        if not key:
            raise ValueError("event_id cannot be empty")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._event_handlers.setdefault(key, []).append(callback)

    def unregister_event(self, event_id: str, callback: Callable[..., Any]) -> bool:
        callbacks = self._event_handlers.get(str(event_id).strip())
        if not callbacks or callback not in callbacks:
            return False
        callbacks.remove(callback)
        return True

    def update(self, delta_time: float) -> None:
        if self._player is None:
            return

        previous = self._player.time
        self._player.update(delta_time)
        current = self._player.time

        self._apply_tracks()
        self._trigger_audio_between(previous, current)
        self._trigger_effects_between(previous, current)
        self._last_time = current

        if self._player.finished and not self._finished_emitted:
            self._finished_emitted = True
            self.finished.emit(self)

    def destroy(self) -> None:
        self._stop_audio_sources()
        if self._scene is not None and self._scene.camera is self._camera:
            self._scene.clear_camera()
        super().destroy()

    def _resolve_asset_path(self, asset_path: str | Path) -> Path:
        path = Path(asset_path).expanduser()
        if path.is_absolute():
            return path

        candidates: list[Path] = [Path.cwd() / path]
        scene_path = self._scene_path
        if scene_path is None and self._scene is not None:
            scene_path = getattr(self._scene, "scene_path", None)
        if scene_path is not None:
            scene_file = Path(scene_path).expanduser()
            candidates.extend((scene_file.parent / path, scene_file.parent.parent / path))
        assets_root = getattr(self._assets, "root", None)
        if assets_root is not None:
            assets_path = Path(assets_root)
            project_path = assets_path.parent
            candidates.extend(
                (
                    assets_path / path,
                    project_path / path,
                    project_path / "cutscenes" / path,
                )
            )

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]

    def _remove_runtime_children(self) -> None:
        for child in tuple(self.children):
            if getattr(child, "_nexora_runtime_only", False):
                child.destroy()

    def _track(self, track_type: str) -> CutsceneTrack | None:
        if self._asset is None:
            return None
        return next(
            (
                track
                for track in self._asset.tracks
                if track.enabled and track.track_type == track_type
            ),
            None,
        )

    def _apply_tracks(self) -> None:
        if self._player is None:
            return

        image_track = self._track("image")
        if image_track is not None and self._sprite is not None:
            value = self._player.evaluate_track(image_track)
            self._apply_image(value)

        camera_track = self._track("camera")
        if camera_track is not None and self._camera is not None:
            value = self._player.evaluate_track(camera_track)
            self._apply_camera(value)

        fade_track = self._track("fade")
        if fade_track is not None and self._camera is not None:
            self._apply_fade(self._player.evaluate_track(fade_track))


    def _apply_image(self, value: Any) -> None:
        if self._sprite is None or value is None:
            return
        if isinstance(value, str):
            source = value
            options: dict[str, Any] = {}
        elif isinstance(value, dict):
            source = value.get("path", value.get("asset", value.get("source", "")))
            options = value
        else:
            return
        source = str(source or "").strip()
        if source:
            if source != self._active_image_source:
                try:
                    self._sprite.texture = self._assets.texture(self._asset_reference(source))
                    self._sprite._nexora_texture_source = source
                    self._active_image_source = source
                except Exception as exc:
                    self.error.emit(str(exc))
        if "width" in options:
            self._sprite.width = max(0.0, _float(options["width"], self._sprite.width))
        if "height" in options:
            self._sprite.height = max(0.0, _float(options["height"], self._sprite.height))
        if "alpha" in options:
            self._sprite.alpha = _clamp01(options["alpha"], self._sprite.alpha)

    def _apply_camera(self, value: Any) -> None:
        if self._camera is None or not isinstance(value, dict):
            return
        if "x" in value or "y" in value:
            self._camera.set_position(
                _float(value.get("x", self._camera._x)),
                _float(value.get("y", self._camera._y)),
            )
        if "zoom" in value:
            self._camera.set_zoom(max(0.001, _float(value["zoom"], 1.0)))

    def _apply_fade(self, value: Any) -> None:
        if self._camera is None or value is None:
            return
        if isinstance(value, dict):
            alpha = value.get("alpha", value.get("amount", 0.0))
            color = value.get("color")
        else:
            alpha = value
            color = None
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            self._camera.fade_color = tuple(_clamp01(item, 0.0) for item in color[:3])
        self._camera.fade_alpha = _clamp01(alpha, 0.0)

    def _apply_effect(self, value: Any) -> None:
        if self._camera is None or not isinstance(value, dict):
            return
        effect = str(value.get("effect", value.get("name", value.get("type", "")))).lower()
        amount = value.get("amount", value.get("intensity", value.get("value", 0.0)))
        duration = max(0.0, _float(value.get("duration", 0.15), 0.15))
        if effect == "shake":
            self._camera.shake(_float(amount, 0.0), duration)
        elif effect == "trauma":
            self._camera.add_trauma(_clamp01(amount, 0.0))
        elif effect == "flash":
            color = value.get("color")
            if not isinstance(color, (list, tuple)) or len(color) < 3:
                color = (1.0, 1.0, 1.0)
            self._camera.flash(
                color=tuple(_clamp01(item, 1.0) for item in color[:3]),
                alpha=_clamp01(amount, 0.0),
                duration=duration,
            )
        elif effect == "punch":
            self._camera.punch(
                _float(value.get("x", 0.0)),
                _float(value.get("y", 0.0)),
                duration=duration,
            )
        elif effect == "letterbox":
            color = value.get("color", (0.0, 0.0, 0.0))
            if not isinstance(color, (list, tuple)) or len(color) < 3:
                color = (0.0, 0.0, 0.0)
            self._camera.letterbox(
                max(0.0, _float(value.get("size", amount), 0.0)),
                duration=duration,
                color=tuple(_clamp01(item, 0.0) for item in color[:3]),
            )
        elif effect in {"clear", "reset"}:
            self._reset_camera_effects()

    def _trigger_effects_between(self, start: float, end: float) -> None:
        if self._player is None or self._asset is None:
            return
        segments = (
            ((start, end),)
            if end >= start
            else ((start, self._asset.duration), (0.0, end))
        )
        for track in self._asset.tracks:
            if not track.enabled or track.track_type != "effect":
                continue
            for frame in track.keyframes:
                if any(left < frame.time <= right for left, right in segments):
                    self._apply_effect(frame.value)

    def _trigger_audio_between(self, start: float, end: float) -> None:
        if self._player is None or self._asset is None:
            return
        if end >= start:
            segments = ((start, end),)
        else:
            segments = ((start, self._asset.duration), (0.0, end))
        for track in self._asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                if any(left < frame.time <= right for left, right in segments):
                    self._play_audio(frame.value)

    def _preload_audio_tracks(self) -> None:
        if self._audio is None or self._asset is None:
            return
        for track in self._asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                value = frame.value
                if not isinstance(value, dict):
                    continue
                path = str(value.get("path", value.get("asset", value.get("source", ""))) or "").strip()
                if not path or str(value.get("action", "play")).lower() in {"fade_out", "stop"}:
                    continue
                reference = self._audio_reference(path)
                if reference in self._audio_cache:
                    continue
                try:
                    loader = self._audio.load_stream if bool(value.get("stream", False)) else self._audio.load
                    self._audio_cache[reference] = loader(reference)
                except Exception as exc:
                    if not bool(value.get("optional", False)):
                        self.error.emit(str(exc))

    def _play_audio(self, value: Any) -> None:
        if self._audio is None or not isinstance(value, dict):
            return
        path = str(value.get("path", value.get("asset", value.get("source", ""))) or "").strip()
        if not path:
            return
        reference = self._audio_reference(path)
        action = str(value.get("action", "play")).lower()
        if action in {"fade_out", "stop"}:
            for source in tuple(self._active_audio_sources.get(reference, ())):
                if action == "fade_out":
                    source.fade_out(max(0.0, _float(value.get("duration", 0.0))))
                else:
                    source.stop()
            return
        try:
            sound = self._audio_cache.get(reference)
            if sound is None:
                loader = self._audio.load_stream if bool(value.get("stream", False)) else self._audio.load
                sound = loader(reference)
                self._audio_cache[reference] = sound
            channel_name = str(value.get("channel", "sfx")).lower()
            bus = channel_name or "Master"
            bus_name = str(value.get("bus", channel_name.title()))
            try:
                bus = self._audio.get_bus(bus_name)
            except KeyError:
                bus = None
            source = AudioSource(
                sound,
                bus=bus,
                volume=_clamp01(value.get("volume", 1.0), 1.0),
                loop=bool(value.get("loop", False)),
            )
            self._audio.player.play(source)
            self._audio_sources.append(source)
            self._active_audio_sources.setdefault(reference, []).append(source)
            fade_in = _float(value.get("fade_in", 0.0), 0.0)
            if fade_in > 0.0:
                source.fade_in(fade_in)
            self._audio_sources[:] = [item for item in self._audio_sources if not item.stopped]
            for key, sources in tuple(self._active_audio_sources.items()):
                alive = [item for item in sources if not item.stopped]
                if alive:
                    self._active_audio_sources[key] = alive
                else:
                    self._active_audio_sources.pop(key, None)
        except Exception as exc:
            if not bool(value.get("optional", False)):
                self.error.emit(str(exc))

    def _asset_reference(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        if normalized.lower().startswith("assets/"):
            return normalized[7:]
        return path

    def _audio_reference(self, path: str) -> str:
        """Resolve a cutscene audio reference against the project assets."""

        normalized = str(path).replace("\\", "/").strip()
        candidate = Path(normalized).expanduser()
        if candidate.is_absolute():
            return str(candidate.resolve())

        if normalized.lower().startswith("assets/"):
            normalized = normalized[7:]

        assets_root = getattr(self._assets, "root", None)
        if assets_root is not None:
            return str((Path(assets_root) / normalized).resolve())

        return normalized

    def _on_event(self, event_id: str, parameters: dict[str, Any]) -> None:
        self.event.emit(event_id, parameters)
        for callback in tuple(self._event_handlers.get(event_id, ())):
            callback(parameters)

    def _stop_audio_sources(self) -> None:
        for source in tuple(self._audio_sources):
            try:
                source.stop()
                if self._audio is not None:
                    self._audio.player.remove(source)
            except Exception:
                pass
        self._audio_sources.clear()
        self._active_audio_sources.clear()

    def _reset_camera_effects(self) -> None:
        if self._camera is not None:
            self._camera.reset_effects()


__all__ = ["DEFAULT_CUTSCENE_SIGNING_KEY", "CutscenePlayerNode"]
