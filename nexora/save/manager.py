from __future__ import annotations

import os
import re
import tempfile

from collections.abc import Callable
from pathlib import Path
from typing import Any

from nexora.save.codec import (
    decode_save,
    encode_save,
    normalize_signing_key,
)

from nexora.save.errors import (
    InvalidSaveError,
    SaveNotFoundError,
)

from nexora.save.events import (
    SaveEvent,
    SaveEventState,
    SaveKind,
    SaveOperation,
)

from nexora.save.save_data import (
    SaveGame,
    SaveMetadata,
)


_SLOT_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]{1,64}$"
)


SaveEventListener = Callable[
    [SaveEvent],
    None,
]


class SaveManager:
    """
    Secure binary save manager for Nexora.

    Features
    --------

        - Pickle HIGHEST_PROTOCOL
        - restricted unpickling
        - opcode validation
        - safe type validation
        - HMAC-SHA256 authentication
        - Nexora magic header
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
    ) -> None:
        # ======================================================
        # Validation
        # ======================================================

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

        # ======================================================
        # Signing
        # ======================================================

        self._signing_key = (
            normalize_signing_key(
                signing_key
            )
        )

        # ======================================================
        # Save configuration
        # ======================================================

        self.save_version = int(
            save_version
        )

        self.max_file_size = int(
            max_file_size
        )

        # ======================================================
        # Quick save
        # ======================================================

        self._quick_save_enabled = bool(
            quick_save_enabled
        )

        self._quick_save_slot = (
            self.validate_slot(
                quick_save_slot
            )
        )

        # ======================================================
        # Autosave
        # ======================================================

        self._autosave_enabled = bool(
            autosave_enabled
        )

        self._autosave_slots = int(
            autosave_slots
        )

        self._autosave_prefix = (
            self.validate_slot(
                autosave_prefix
            )
        )

        # ======================================================
        # Save path
        # ======================================================

        self._save_path = Path()

        self.set_save_path(
            save_path
        )

        # ======================================================
        # Events
        # ======================================================

        self._listeners: list[
            SaveEventListener
        ] = []

    # ==========================================================
    # SAVE PATH
    # ==========================================================

    @property
    def save_path(
        self,
    ) -> Path:
        return self._save_path

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
    ) -> Path:
        """
        Change the directory used for save files.

        The directory is created automatically.
        """

        path = Path(
            value
        ).expanduser()

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not path.is_dir():
            raise NotADirectoryError(
                str(path)
            )

        self._save_path = (
            path.resolve()
        )

        return self._save_path

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
        """
        Return currently registered event listeners.
        """

        return tuple(
            self._listeners
        )

    def add_listener(
        self,
        callback: SaveEventListener,
    ) -> None:
        """
        Subscribe to SaveManager events.

        Adding the same callback more than once has no effect.
        """

        if not callable(
            callback
        ):
            raise TypeError(
                "Save event listener must be callable."
            )

        if callback in self._listeners:
            return

        self._listeners.append(
            callback
        )

    def remove_listener(
        self,
        callback: SaveEventListener,
    ) -> bool:
        """
        Remove an event listener.

        Returns True when the listener was registered.
        """

        try:
            self._listeners.remove(
                callback
            )

        except ValueError:
            return False

        return True

    def clear_listeners(
        self,
    ) -> None:
        """
        Remove all SaveManager listeners.
        """

        self._listeners.clear()

    def _emit(
        self,
        event: SaveEvent,
    ) -> None:
        """
        Dispatch an event.

        Listener errors are isolated from save operations.

        A broken notification listener must never cause a
        save or load operation itself to fail.
        """

        for callback in tuple(
            self._listeners
        ):
            try:
                callback(
                    event
                )

            except Exception:
                continue

    # ==========================================================
    # QUICK SAVE CONFIGURATION
    # ==========================================================

    @property
    def quick_save_enabled(
        self,
    ) -> bool:
        return self._quick_save_enabled

    @quick_save_enabled.setter
    def quick_save_enabled(
        self,
        enabled: bool,
    ) -> None:
        self._quick_save_enabled = bool(
            enabled
        )

    @property
    def quick_save_slot(
        self,
    ) -> str:
        return self._quick_save_slot

    @quick_save_slot.setter
    def quick_save_slot(
        self,
        slot: str,
    ) -> None:
        self._quick_save_slot = (
            self.validate_slot(
                slot
            )
        )

    # ==========================================================
    # AUTOSAVE CONFIGURATION
    # ==========================================================

    @property
    def autosave_enabled(
        self,
    ) -> bool:
        return self._autosave_enabled

    @autosave_enabled.setter
    def autosave_enabled(
        self,
        enabled: bool,
    ) -> None:
        self._autosave_enabled = bool(
            enabled
        )

    @property
    def autosave_slots(
        self,
    ) -> int:
        return self._autosave_slots

    @property
    def autosave_prefix(
        self,
    ) -> str:
        return self._autosave_prefix

    # ==========================================================
    # SLOT VALIDATION
    # ==========================================================

    @staticmethod
    def validate_slot(
        slot: str,
    ) -> str:
        slot = str(
            slot
        )

        if not _SLOT_PATTERN.fullmatch(
            slot
        ):
            raise ValueError(
                "Invalid save slot name. "
                "Allowed: A-Z, a-z, 0-9, '_' and '-'. "
                "Maximum length: 64."
            )

        return slot

    # ==========================================================
    # PATH
    # ==========================================================

    def slot_path(
        self,
        slot: str,
    ) -> Path:
        slot = self.validate_slot(
            slot
        )

        return (
            self._save_path
            / (
                slot
                + self.FILE_EXTENSION
            )
        )

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

            raw = encode_save(
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

            envelope = decode_save(
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
        """
        Create a quick save.
        """

        if not self._quick_save_enabled:
            raise RuntimeError(
                "Quick saving is disabled."
            )

        return self._save(
            self._quick_save_slot,
            data,
            name=name,
            playtime=playtime,
            kind=SaveKind.QUICK,
        )

    # ==========================================================
    # QUICK LOAD
    # ==========================================================

    def quick_load(
        self,
    ) -> SaveGame:
        """
        Load the current quick-save slot.
        """

        if not self._quick_save_enabled:
            raise RuntimeError(
                "Quick saving is disabled."
            )

        return self._load(
            self._quick_save_slot,
            kind=SaveKind.QUICK,
        )

    # ==========================================================
    # QUICK SAVE EXISTS
    # ==========================================================

    def has_quick_save(
        self,
    ) -> bool:
        if not self._quick_save_enabled:
            return False

        return self.exists(
            self._quick_save_slot
        )

    # ==========================================================
    # DELETE QUICK SAVE
    # ==========================================================

    def delete_quick_save(
        self,
    ) -> bool:
        return self._delete(
            self._quick_save_slot,
            kind=SaveKind.QUICK,
        )

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
        """
        Create a rotating autosave.

        autosave_1 is always the newest save.

        Existing saves are shifted:

            autosave_1 -> autosave_2
            autosave_2 -> autosave_3
            ...

        The oldest slot is discarded.
        """

        if not self._autosave_enabled:
            raise RuntimeError(
                "Autosaving is disabled."
            )

        self._rotate_auto_saves()

        slot = (
            self._autosave_slot_name(
                1
            )
        )

        return self._save(
            slot,
            data,
            name=name,
            playtime=playtime,
            kind=SaveKind.AUTO,
        )

    # ==========================================================
    # AUTOSAVE SLOT
    # ==========================================================

    def _autosave_slot_name(
        self,
        index: int,
    ) -> str:
        if index <= 0:
            raise ValueError(
                "Autosave index must be greater than zero."
            )

        return (
            f"{self._autosave_prefix}_{index}"
        )

    # ==========================================================
    # AUTOSAVE ROTATION
    # ==========================================================

    def _rotate_auto_saves(
        self,
    ) -> None:
        """
        Shift existing autosaves from newest to oldest.

        The save file cannot simply be renamed because metadata.slot
        must always match the filename / target slot.
        """

        # ------------------------------------------------------
        # Remove oldest
        # ------------------------------------------------------

        oldest_slot = (
            self._autosave_slot_name(
                self._autosave_slots
            )
        )

        oldest_path = (
            self.slot_path(
                oldest_slot
            )
        )

        if oldest_path.exists():
            oldest_path.unlink()

        # ------------------------------------------------------
        # Shift backwards
        # ------------------------------------------------------

        for index in range(
            self._autosave_slots - 1,
            0,
            -1,
        ):
            source_slot = (
                self._autosave_slot_name(
                    index
                )
            )

            destination_slot = (
                self._autosave_slot_name(
                    index + 1
                )
            )

            source_path = (
                self.slot_path(
                    source_slot
                )
            )

            if not source_path.exists():
                continue

            self._relocate_save(
                source_slot,
                destination_slot,
            )


    def _relocate_save(
        self,
        source_slot: str,
        destination_slot: str,
    ) -> None:
        """
        Move a save to another slot while updating its embedded
        metadata.slot value.

        This is required for autosave rotation because the slot identity
        is part of the signed save payload.
        """

        source_slot = self.validate_slot(
            source_slot
        )

        destination_slot = self.validate_slot(
            destination_slot
        )

        source_path = (
            self.slot_path(
                source_slot
            )
        )

        destination_path = (
            self.slot_path(
                destination_slot
            )
        )

        # ------------------------------------------------------
        # Read source
        # ------------------------------------------------------

        try:
            raw = source_path.read_bytes()

        except OSError as exc:
            raise InvalidSaveError(
                f"Could not read save slot '{source_slot}'."
            ) from exc

        # ------------------------------------------------------
        # Decode and verify
        # ------------------------------------------------------

        envelope = decode_save(
            raw,
            signing_key=(
                self._signing_key
            ),
            max_payload_size=(
                self.max_file_size
            ),
        )

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

        metadata_raw = (
            envelope[
                "metadata"
            ]
        )

        if not isinstance(
            metadata_raw,
            dict,
        ):
            raise InvalidSaveError(
                "Save metadata is invalid."
            )

        # ------------------------------------------------------
        # Verify original slot identity
        # ------------------------------------------------------

        metadata = (
            SaveMetadata.from_dict(
                metadata_raw
            )
        )

        if (
            metadata.slot
            != source_slot
        ):
            raise InvalidSaveError(
                "Save slot metadata does not match source filename."
            )

        # ------------------------------------------------------
        # Update slot identity
        # ------------------------------------------------------

        new_metadata = dict(
            metadata_raw
        )

        new_metadata[
            "slot"
        ] = destination_slot

        new_envelope = dict(
            envelope
        )

        new_envelope[
            "metadata"
        ] = new_metadata

        # ------------------------------------------------------
        # Encode again
        # ------------------------------------------------------

        encoded = encode_save(
            new_envelope,
            signing_key=(
                self._signing_key
            ),
        )

        if (
            len(
                encoded
            )
            > self.max_file_size
        ):
            raise InvalidSaveError(
                "Rotated save exceeds configured maximum size."
            )

        # ------------------------------------------------------
        # Write destination atomically
        # ------------------------------------------------------

        self._atomic_write(
            destination_path,
            encoded,
        )

        # ------------------------------------------------------
        # Remove source
        # ------------------------------------------------------

        try:
            source_path.unlink()

        except OSError as exc:
            raise InvalidSaveError(
                f"Could not remove rotated source slot "
                f"'{source_slot}'."
            ) from exc

    # ==========================================================
    # LIST AUTOSAVES
    # ==========================================================

    def list_auto_saves(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        """
        Return existing autosaves from newest to oldest.
        """

        slots: list[str] = []

        for index in range(
            1,
            self._autosave_slots + 1,
        ):
            slot = (
                self._autosave_slot_name(
                    index
                )
            )

            if self.exists(
                slot
            ):
                slots.append(
                    slot
                )

        return tuple(
            slots
        )

    # ==========================================================
    # LATEST AUTOSAVE
    # ==========================================================

    def latest_auto_save_slot(
        self,
    ) -> str | None:
        """
        Return the newest autosave slot.
        """

        slot = (
            self._autosave_slot_name(
                1
            )
        )

        if not self.exists(
            slot
        ):
            return None

        return slot

    # ==========================================================
    # LOAD AUTOSAVE
    # ==========================================================

    def load_latest_auto_save(
        self,
    ) -> SaveGame:
        """
        Load the newest autosave.
        """

        if not self._autosave_enabled:
            raise RuntimeError(
                "Autosaving is disabled."
            )

        slot = (
            self.latest_auto_save_slot()
        )

        if slot is None:
            raise SaveNotFoundError(
                "No autosave exists."
            )

        return self._load(
            slot,
            kind=SaveKind.AUTO,
        )

    # ==========================================================
    # AUTOSAVE EXISTS
    # ==========================================================

    def has_auto_save(
        self,
    ) -> bool:
        if not self._autosave_enabled:
            return False

        return (
            self.latest_auto_save_slot()
            is not None
        )

    # ==========================================================
    # DELETE AUTOSAVES
    # ==========================================================

    def delete_auto_saves(
        self,
    ) -> int:
        """
        Delete every autosave.

        Deletion is allowed even when autosaving is disabled.

        Returns
        -------
        int
            Number of deleted autosave files.
        """

        deleted = 0

        for index in range(
            1,
            self._autosave_slots + 1,
        ):
            slot = (
                self._autosave_slot_name(
                    index
                )
            )

            if self._delete(
                slot,
                kind=SaveKind.AUTO,
            ):
                deleted += 1

        return deleted

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        slot: str,
    ) -> bool:
        return (
            self.slot_path(
                slot
            ).is_file()
        )

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
        """
        Return available save slot names.

        Files are not deserialized by this operation.
        """

        slots = []

        for path in self._save_path.glob(
            "*" + self.FILE_EXTENSION
        ):
            if not path.is_file():
                continue

            slot = path.stem

            try:
                self.validate_slot(
                    slot
                )

            except ValueError:
                continue

            slots.append(
                slot
            )

        slots.sort()

        return tuple(
            slots
        )

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
        """
        Write into a temporary file in the same directory and
        atomically replace the destination afterwards.
        """

        temp_path: (
            Path | None
        ) = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=(
                    destination.name
                    + "."
                ),
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(
                    temp_file.name
                )

                temp_file.write(
                    data
                )

                temp_file.flush()

                os.fsync(
                    temp_file.fileno()
                )

            os.replace(
                temp_path,
                destination,
            )

        except Exception:
            if (
                temp_path is not None
                and temp_path.exists()
            ):
                try:
                    temp_path.unlink()

                except OSError:
                    pass

            raise