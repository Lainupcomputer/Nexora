from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nexora.data.save.errors import (
    InvalidSaveError,
    SaveNotFoundError,
)
from nexora.data.save.events import SaveKind
from nexora.data.save.save_data import SaveGame, SaveMetadata
from nexora.data.save.serialization import decode_save, encode_save
from nexora.data.save.storage import SaveSlotStore


class AutoSaveController:
    """Rotating autosave policy and relocation implementation."""

    def __init__(
        self,
        *,
        enabled: bool,
        slots: int,
        prefix: str,
        slot_store: SaveSlotStore,
        validate_slot: Callable[[str], str],
        save: Callable[..., SaveMetadata],
        load: Callable[..., SaveGame],
        exists: Callable[[str], bool],
        delete: Callable[..., bool],
        signing_key: Callable[[], bytes],
        max_file_size: Callable[[], int],
    ) -> None:
        self._slot_store = slot_store
        self._validate_slot = validate_slot
        self._save = save
        self._load = load
        self._exists = exists
        self._delete = delete
        self._signing_key = signing_key
        self._max_file_size = max_file_size
        self.enabled = bool(enabled)
        self.slots = int(slots)
        self.prefix = self._validate_slot(prefix)

    def slot_name(self, index: int) -> str:
        if index <= 0:
            raise ValueError("Autosave index must be greater than zero.")
        return f"{self.prefix}_{index}"

    def save(
        self,
        data: dict[str, Any],
        *,
        name: str = "Auto Save",
        playtime: float = 0.0,
    ) -> SaveMetadata:
        if not self.enabled:
            raise RuntimeError("Autosaving is disabled.")
        self.rotate()
        return self._save(
            self.slot_name(1),
            data,
            name=name,
            playtime=playtime,
            kind=SaveKind.AUTO,
        )

    def rotate(self) -> None:
        oldest_path = self._slot_store.slot_path(self.slot_name(self.slots))
        if oldest_path.exists():
            oldest_path.unlink()

        for index in range(self.slots - 1, 0, -1):
            source_slot = self.slot_name(index)
            if not self._slot_store.slot_path(source_slot).exists():
                continue
            self.relocate(source_slot, self.slot_name(index + 1))

    def relocate(self, source_slot: str, destination_slot: str) -> None:
        source_slot = self._validate_slot(source_slot)
        destination_slot = self._validate_slot(destination_slot)
        source_path = self._slot_store.slot_path(source_slot)
        destination_path = self._slot_store.slot_path(destination_slot)

        try:
            raw = source_path.read_bytes()
        except OSError as exc:
            raise InvalidSaveError(
                f"Could not read save slot '{source_slot}'."
            ) from exc

        envelope = decode_save(
            raw,
            signing_key=self._signing_key(),
            max_payload_size=self._max_file_size(),
        )
        if not isinstance(envelope, dict):
            raise InvalidSaveError("Save root must be a dictionary.")

        required = {"save_version", "metadata", "data"}
        if not required.issubset(envelope):
            raise InvalidSaveError("Save envelope is incomplete.")

        metadata_raw = envelope["metadata"]
        if not isinstance(metadata_raw, dict):
            raise InvalidSaveError("Save metadata is invalid.")

        metadata = SaveMetadata.from_dict(metadata_raw)
        if metadata.slot != source_slot:
            raise InvalidSaveError(
                "Save slot metadata does not match source filename."
            )

        new_metadata = dict(metadata_raw)
        new_metadata["slot"] = destination_slot
        new_envelope = dict(envelope)
        new_envelope["metadata"] = new_metadata

        encoded = encode_save(
            new_envelope,
            signing_key=self._signing_key(),
        )
        if len(encoded) > self._max_file_size():
            raise InvalidSaveError(
                "Rotated save exceeds configured maximum size."
            )

        self._slot_store.write_path(destination_path, encoded)
        try:
            source_path.unlink()
        except OSError as exc:
            raise InvalidSaveError(
                f"Could not remove rotated source slot '{source_slot}'."
            ) from exc

    def list_slots(self) -> tuple[str, ...]:
        return tuple(
            slot
            for index in range(1, self.slots + 1)
            if self._exists(slot := self.slot_name(index))
        )

    def latest_slot(self) -> str | None:
        slot = self.slot_name(1)
        return slot if self._exists(slot) else None

    def load_latest(self) -> SaveGame:
        if not self.enabled:
            raise RuntimeError("Autosaving is disabled.")
        slot = self.latest_slot()
        if slot is None:
            raise SaveNotFoundError("No autosave exists.")
        return self._load(slot, kind=SaveKind.AUTO)

    def exists(self) -> bool:
        if not self.enabled:
            return False
        return self.latest_slot() is not None

    def delete_all(self) -> int:
        deleted = 0
        for index in range(1, self.slots + 1):
            if self._delete(self.slot_name(index), kind=SaveKind.AUTO):
                deleted += 1
        return deleted
