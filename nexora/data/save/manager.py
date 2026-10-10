from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data.file import normalize_signing_key


from nexora.data.save.errors import (
    InvalidSaveError,
    SaveNotFoundError,
)

from nexora.data.save.dispatcher import (
    SaveEventDispatcher,
    SaveEventListener,
)
from nexora.data.save.events import (
    SaveEvent,
    SaveEventState,
    SaveKind,
    SaveOperation,
)

from nexora.data.save.storage import SaveSlotStore
from nexora.data.save.autosave import AutoSaveController
from nexora.data.save.quick import QuickSaveController
from nexora.data.save.serialization import (
    decode_save as _decode_save,
    encode_save as _encode_save,
)

from nexora.data.save.save_data import (
    SaveGame,
    SaveMetadata,
)





class SaveManager:
    """
    Secure binary save manager for Nexora.

    Features
    --------

        - shared Nexora data container
        - restricted payload decoding
        - safe type validation
        - HMAC-SHA256 authentication
        - NXDATA01 container header
        - payload size limits
        - sanitized slot names
        - atomic writes
        - configurable save path
        - save metadata
        - optional quick save
        - configurable quick-save slot
        - optional autosave
        - rotating autosave slots
        - save/load/delete events
        - isolated event listeners
    """

    FILE_EXTENSION = ".nxs"

    def __init__(
        self,
        save_path: str | Path = "saves",
        *,
        signing_key: bytes | str,
        save_version: int = 1,
        max_file_size: int = (
            64 * 1024 * 1024
        ),
        quick_save_enabled: bool = True,
        quick_save_slot: str = "quicksave",
        autosave_enabled: bool = True,
        autosave_slots: int = 3,
        autosave_prefix: str = "autosave",
        create_directory: bool = True,
    ) -> None:
        if max_file_size <= 0:
            raise ValueError(
                "max_file_size must be greater than zero."
            )
        if save_version <= 0:
            raise ValueError(
                "save_version must be greater than zero."
            )
        if autosave_slots <= 0:
            raise ValueError(
                "autosave_slots must be greater than zero."
            )

        # Validate policy slot names before touching the filesystem.
        quick_save_slot = self.validate_slot(quick_save_slot)
        autosave_prefix = self.validate_slot(autosave_prefix)

        self._signing_key = normalize_signing_key(signing_key)
        self.save_version = int(save_version)
        self.max_file_size = int(max_file_size)
        self._create_save_directory = bool(create_directory)

        self._slot_store = SaveSlotStore(
            save_path,
            extension=self.FILE_EXTENSION,
            create_directory=self._create_save_directory,
        )
        self._event_dispatcher = SaveEventDispatcher()

        self._quick_saves = QuickSaveController(
            enabled=quick_save_enabled,
            slot=quick_save_slot,
            validate_slot=self.validate_slot,
            save=self._save,
            load=self._load,
            exists=self.exists,
            delete=self._delete,
        )
        self._autosaves = AutoSaveController(
            enabled=autosave_enabled,
            slots=autosave_slots,
            prefix=autosave_prefix,
            slot_store=self._slot_store,
            validate_slot=self.validate_slot,
            save=self._save,
            load=self._load,
            exists=self.exists,
            delete=self._delete,
            signing_key=lambda: self._signing_key,
            max_file_size=lambda: self.max_file_size,
        )

    # ==========================================================
    # SAVE PATH
    # ==========================================================

    @property
    def save_path(
        self,
    ) -> Path:
        return self._slot_store.path

    @save_path.setter
    def save_path(
        self,
        value: str | Path,
    ) -> None:
        self.set_save_path(
            value
        )

    def set_save_path(
        self,
        value: str | Path,
        *,
        create_directory: bool | None = None,
    ) -> Path:
        """Change the directory used for save files."""
        return self._slot_store.set_path(
            value,
            create_directory=create_directory,
        )

    # ==========================================================
    # SIGNING KEY
    # ==========================================================

    def set_signing_key(
        self,
        signing_key: bytes | str,
    ) -> None:
        """
        Replace the save authentication key.

        Existing saves signed with the old key will no longer
        load using the new key.
        """

        self._signing_key = (
            normalize_signing_key(
                signing_key
            )
        )

    # ==========================================================
    # EVENTS
    # ==========================================================

    @property
    def listeners(
        self,
    ) -> tuple[
        SaveEventListener,
        ...
    ]:
        return self._event_dispatcher.listeners

    def add_listener(
        self,
        callback: SaveEventListener,
    ) -> None:
        self._event_dispatcher.add(callback)

    def remove_listener(
        self,
        callback: SaveEventListener,
    ) -> bool:
        return self._event_dispatcher.remove(callback)

    def clear_listeners(
        self,
    ) -> None:
        self._event_dispatcher.clear()

    def _emit(
        self,
        event: SaveEvent,
    ) -> None:
        self._event_dispatcher.emit(event)

    # ==========================================================
    # QUICK SAVE CONFIGURATION
    # ==========================================================

    @property
    def quick_save_enabled(
        self,
    ) -> bool:
        return self._quick_saves.enabled

    @quick_save_enabled.setter
    def quick_save_enabled(
        self,
        enabled: bool,
    ) -> None:
        self._quick_saves.enabled = bool(enabled)

    @property
    def quick_save_slot(
        self,
    ) -> str:
        return self._quick_saves.slot

    @quick_save_slot.setter
    def quick_save_slot(
        self,
        slot: str,
    ) -> None:
        self._quick_saves.slot = slot

    # ==========================================================
    # AUTOSAVE CONFIGURATION
    # ==========================================================

    @property
    def autosave_enabled(
        self,
    ) -> bool:
        return self._autosaves.enabled

    @autosave_enabled.setter
    def autosave_enabled(
        self,
        enabled: bool,
    ) -> None:
        self._autosaves.enabled = bool(enabled)

    @property
    def autosave_slots(
        self,
    ) -> int:
        return self._autosaves.slots

    @property
    def autosave_prefix(
        self,
    ) -> str:
        return self._autosaves.prefix

    # ==========================================================
    # SLOT VALIDATION
    # ==========================================================

    @staticmethod
    def validate_slot(
        slot: str,
    ) -> str:
        return SaveSlotStore.validate_slot(slot)

    # ==========================================================
    # PATH
    # ==========================================================

    def slot_path(
        self,
        slot: str,
    ) -> Path:
        return self._slot_store.slot_path(slot)

    # ==========================================================
    # MANUAL SAVE
    # ==========================================================

    def save(
        self,
        slot: str,
        data: dict[str, Any],
        *,
        name: str | None = None,
        playtime: float = 0.0,
    ) -> SaveMetadata:
        """
        Write a manual save.
        """

        return self._save(
            slot,
            data,
            name=name,
            playtime=playtime,
            kind=SaveKind.MANUAL,
        )

    # ==========================================================
    # INTERNAL SAVE
    # ==========================================================

    def _save(
        self,
        slot: str,
        data: dict[str, Any],
        *,
        name: str | None,
        playtime: float,
        kind: SaveKind,
    ) -> SaveMetadata:
        slot = self.validate_slot(
            slot
        )

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Save data must be a dictionary."
            )

        # ------------------------------------------------------
        # Started
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.SAVE
                ),
                kind=kind,
                state=(
                    SaveEventState.STARTED
                ),
                slot=slot,
            )
        )

        try:
            # --------------------------------------------------
            # Metadata
            # --------------------------------------------------

            metadata = (
                SaveMetadata.create(
                    slot=slot,
                    name=(
                        name
                        if name is not None
                        else slot
                    ),
                    playtime=playtime,
                    save_version=(
                        self.save_version
                    ),
                )
            )

            # --------------------------------------------------
            # Envelope
            # --------------------------------------------------

            envelope = {
                "save_version": (
                    self.save_version
                ),
                "metadata": (
                    metadata.to_dict()
                ),
                "data": data,
            }

            # --------------------------------------------------
            # Encode
            # --------------------------------------------------

            raw = _encode_save(
                envelope,
                signing_key=(
                    self._signing_key
                ),
            )

            if (
                len(raw)
                > self.max_file_size
            ):
                raise ValueError(
                    "Encoded save exceeds "
                    "maximum configured file size."
                )

            # --------------------------------------------------
            # Destination
            # --------------------------------------------------

            destination = (
                self.slot_path(
                    slot
                )
            )

            # --------------------------------------------------
            # Atomic write
            # --------------------------------------------------

            self._atomic_write(
                destination,
                raw,
            )

        except Exception as exc:
            # --------------------------------------------------
            # Failed
            # --------------------------------------------------

            self._emit(
                SaveEvent(
                    operation=(
                        SaveOperation.SAVE
                    ),
                    kind=kind,
                    state=(
                        SaveEventState.FAILED
                    ),
                    slot=slot,
                    error=exc,
                )
            )

            raise

        # ------------------------------------------------------
        # Completed
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.SAVE
                ),
                kind=kind,
                state=(
                    SaveEventState.COMPLETED
                ),
                slot=slot,
                metadata=metadata,
            )
        )

        return metadata

    # ==========================================================
    # MANUAL LOAD
    # ==========================================================

    def load(
        self,
        slot: str,
    ) -> SaveGame:
        """
        Load and verify a manual save.
        """

        return self._load(
            slot,
            kind=SaveKind.MANUAL,
        )

    # ==========================================================
    # INTERNAL LOAD
    # ==========================================================

    def _load(
        self,
        slot: str,
        *,
        kind: SaveKind,
    ) -> SaveGame:
        slot = self.validate_slot(
            slot
        )

        # ------------------------------------------------------
        # Started
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.LOAD
                ),
                kind=kind,
                state=(
                    SaveEventState.STARTED
                ),
                slot=slot,
            )
        )

        try:
            # --------------------------------------------------
            # Resolve path
            # --------------------------------------------------

            path = self.slot_path(
                slot
            )

            if not path.is_file():
                raise SaveNotFoundError(
                    f"Save slot '{slot}' does not exist."
                )

            # --------------------------------------------------
            # File size validation
            # --------------------------------------------------

            stat = path.stat()

            if (
                stat.st_size
                > self.max_file_size
            ):
                raise InvalidSaveError(
                    "Save file exceeds configured "
                    "maximum size."
                )

            # --------------------------------------------------
            # Read
            # --------------------------------------------------

            try:
                raw = path.read_bytes()

            except OSError as exc:
                raise InvalidSaveError(
                    f"Could not read save slot '{slot}'."
                ) from exc

            # --------------------------------------------------
            # Decode
            # --------------------------------------------------

            envelope = _decode_save(
                raw,
                signing_key=(
                    self._signing_key
                ),
                max_payload_size=(
                    self.max_file_size
                ),
            )

            # --------------------------------------------------
            # Root validation
            # --------------------------------------------------

            if not isinstance(
                envelope,
                dict,
            ):
                raise InvalidSaveError(
                    "Save root must be a dictionary."
                )

            required = {
                "save_version",
                "metadata",
                "data",
            }

            if not required.issubset(
                envelope
            ):
                raise InvalidSaveError(
                    "Save envelope is incomplete."
                )

            # --------------------------------------------------
            # Save version
            # --------------------------------------------------

            save_version = int(
                envelope[
                    "save_version"
                ]
            )

            if (
                save_version
                > self.save_version
            ):
                raise InvalidSaveError(
                    "Save was created by a newer "
                    "save format version."
                )

            # --------------------------------------------------
            # Metadata/data
            # --------------------------------------------------

            metadata_raw = (
                envelope[
                    "metadata"
                ]
            )

            data = (
                envelope[
                    "data"
                ]
            )

            if not isinstance(
                metadata_raw,
                dict,
            ):
                raise InvalidSaveError(
                    "Save metadata is invalid."
                )

            if not isinstance(
                data,
                dict,
            ):
                raise InvalidSaveError(
                    "Save data is invalid."
                )

            metadata = (
                SaveMetadata.from_dict(
                    metadata_raw
                )
            )

            # --------------------------------------------------
            # Slot identity
            # --------------------------------------------------

            if metadata.slot != slot:
                raise InvalidSaveError(
                    "Save slot metadata does not match filename."
                )

            save_game = SaveGame(
                metadata=metadata,
                data=data,
            )

        except Exception as exc:
            # --------------------------------------------------
            # Failed
            # --------------------------------------------------

            self._emit(
                SaveEvent(
                    operation=(
                        SaveOperation.LOAD
                    ),
                    kind=kind,
                    state=(
                        SaveEventState.FAILED
                    ),
                    slot=slot,
                    error=exc,
                )
            )

            raise

        # ------------------------------------------------------
        # Completed
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.LOAD
                ),
                kind=kind,
                state=(
                    SaveEventState.COMPLETED
                ),
                slot=slot,
                metadata=metadata,
            )
        )

        return save_game

    # ==========================================================
    # QUICK SAVE
    # ==========================================================

    def quick_save(
        self,
        data: dict[str, Any],
        *,
        name: str = "Quick Save",
        playtime: float = 0.0,
    ) -> SaveMetadata:
        return self._quick_saves.save(
            data,
            name=name,
            playtime=playtime,
        )

    # ==========================================================
    # QUICK LOAD
    # ==========================================================

    def quick_load(
        self,
    ) -> SaveGame:
        return self._quick_saves.load()

    # ==========================================================
    # QUICK SAVE EXISTS
    # ==========================================================

    def has_quick_save(
        self,
    ) -> bool:
        return self._quick_saves.exists()

    # ==========================================================
    # DELETE QUICK SAVE
    # ==========================================================

    def delete_quick_save(
        self,
    ) -> bool:
        return self._quick_saves.delete()

    # ==========================================================
    # AUTOSAVE
    # ==========================================================

    def auto_save(
        self,
        data: dict[str, Any],
        *,
        name: str = "Auto Save",
        playtime: float = 0.0,
    ) -> SaveMetadata:
        return self._autosaves.save(
            data,
            name=name,
            playtime=playtime,
        )

    def _autosave_slot_name(
        self,
        index: int,
    ) -> str:
        return self._autosaves.slot_name(index)

    def _rotate_auto_saves(
        self,
    ) -> None:
        self._autosaves.rotate()

    def _relocate_save(
        self,
        source_slot: str,
        destination_slot: str,
    ) -> None:
        self._autosaves.relocate(
            source_slot,
            destination_slot,
        )

    def list_auto_saves(
        self,
    ) -> tuple[str, ...]:
        return self._autosaves.list_slots()

    def latest_auto_save_slot(
        self,
    ) -> str | None:
        return self._autosaves.latest_slot()

    def load_latest_auto_save(
        self,
    ) -> SaveGame:
        return self._autosaves.load_latest()

    def has_auto_save(
        self,
    ) -> bool:
        return self._autosaves.exists()

    def delete_auto_saves(
        self,
    ) -> int:
        return self._autosaves.delete_all()

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        slot: str,
    ) -> bool:
        return self._slot_store.exists(slot)

    # ==========================================================
    # DELETE
    # ==========================================================

    def delete(
        self,
        slot: str,
    ) -> bool:
        """
        Delete a manual save slot.
        """

        return self._delete(
            slot,
            kind=SaveKind.MANUAL,
        )

    # ==========================================================
    # INTERNAL DELETE
    # ==========================================================

    def _delete(
        self,
        slot: str,
        *,
        kind: SaveKind,
    ) -> bool:
        slot = self.validate_slot(
            slot
        )

        path = self.slot_path(
            slot
        )

        # ------------------------------------------------------
        # Missing files are not treated as failed operations.
        # Existing SaveManager behavior remains:
        #
        #     delete(...) -> False
        # ------------------------------------------------------

        if not path.exists():
            return False

        # ------------------------------------------------------
        # Started
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.DELETE
                ),
                kind=kind,
                state=(
                    SaveEventState.STARTED
                ),
                slot=slot,
            )
        )

        try:
            path.unlink()

        except Exception as exc:
            # --------------------------------------------------
            # Failed
            # --------------------------------------------------

            self._emit(
                SaveEvent(
                    operation=(
                        SaveOperation.DELETE
                    ),
                    kind=kind,
                    state=(
                        SaveEventState.FAILED
                    ),
                    slot=slot,
                    error=exc,
                )
            )

            raise

        # ------------------------------------------------------
        # Completed
        # ------------------------------------------------------

        self._emit(
            SaveEvent(
                operation=(
                    SaveOperation.DELETE
                ),
                kind=kind,
                state=(
                    SaveEventState.COMPLETED
                ),
                slot=slot,
            )
        )

        return True

    # ==========================================================
    # LIST
    # ==========================================================

    def list_slots(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        """Return available save slot names without deserializing files."""
        return self._slot_store.list_slots()

    # ==========================================================
    # METADATA
    # ==========================================================

    def metadata(
        self,
        slot: str,
    ) -> SaveMetadata:
        """
        Return verified metadata.

        This currently performs a normal authenticated load.
        """

        return (
            self.load(
                slot
            ).metadata
        )

    # ==========================================================
    # ATOMIC WRITE
    # ==========================================================

    def _atomic_write(
        self,
        destination: Path,
        data: bytes,
    ) -> None:
        self._slot_store.write_path(destination, data)
