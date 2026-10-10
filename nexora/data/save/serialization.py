from __future__ import annotations

from typing import Any

from nexora.data import (
    DataIntegrityError,
    DataTypeMismatchError,
    InvalidDataFileError,
    UnsafeDataError,
    UnsupportedDataVersionError,
)
from nexora.data.codecs import savegame as savegame_codec
from nexora.data.save.errors import (
    InvalidSaveError,
    SaveIntegrityError,
    UnsafeSaveDataError,
    UnsupportedSaveVersionError,
)


def translate_data_error(exc: Exception) -> Exception:
    """Translate shared data errors to the public save API."""
    if isinstance(exc, UnsafeDataError):
        return UnsafeSaveDataError(str(exc))
    if isinstance(exc, DataIntegrityError):
        return SaveIntegrityError(str(exc))
    if isinstance(exc, UnsupportedDataVersionError):
        return UnsupportedSaveVersionError(str(exc))
    if isinstance(exc, (InvalidDataFileError, DataTypeMismatchError)):
        return InvalidSaveError(str(exc))
    return exc


def encode_save(
    envelope: dict[str, Any],
    *,
    signing_key: bytes | str,
) -> bytes:
    try:
        return savegame_codec.encode(
            envelope,
            signing_key=signing_key,
        )
    except Exception as exc:
        translated = translate_data_error(exc)
        if translated is exc:
            raise
        raise translated from exc


def decode_save(
    raw: bytes,
    *,
    signing_key: bytes | str,
    max_payload_size: int,
) -> dict[str, Any]:
    try:
        return savegame_codec.decode(
            raw,
            signing_key=signing_key,
            max_file_size=max_payload_size,
        )
    except Exception as exc:
        translated = translate_data_error(exc)
        if translated is exc:
            raise
        raise translated from exc
