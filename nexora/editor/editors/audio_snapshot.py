from __future__ import annotations

"""Mixer snapshot persistence for the audio editor."""

from pathlib import Path

from nexora.data.codecs import audio_mixer as audio_mixer_codec


class AudioSnapshotMixin:
    @property
    def snapshot_path(self) -> Path:
        return self.project_path / self.SNAPSHOT_NAME

    def _save_snapshot(self) -> None:
        try:
            audio_mixer_codec.save(
                self.game.audio.create_mixer_snapshot(),
                self.snapshot_path,
            )
            self.status = f"Saved {self.snapshot_path.name}."
        except Exception as exc:
            self.status = f"Save failed: {exc}"

    def _load_snapshot(self) -> None:
        try:
            data = audio_mixer_codec.load(self.snapshot_path)
            self.game.audio.restore_mixer_snapshot(data)
            self._selected_bus_id = None
            self._selected_effect = -1
            self._selected_send = -1
            self._refresh_bus_list(select_name="Master")
            self.status = f"Loaded {self.snapshot_path.name}."
        except FileNotFoundError:
            self.status = f"{self.snapshot_path.name} does not exist yet."
        except Exception as exc:
            self.status = f"Load failed: {exc}"

    def _reset_mixer(self) -> None:
        self.game.audio.reset()
        self.status = "Mixer reset."
        self._sync_controls()
