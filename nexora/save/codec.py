from __future__ import annotations

from typing import Any

from nexora.data.codecs import savegame as savegame_codec
from nexora.data.errors import (
    DataIntegrityError,
    DataTypeMismatchError,
    InvalidDataFileError,
    UnsafeDataError,
    UnsupportedDataVersionError,
)
from nexora.data.file import (
    normalize_signing_key as _normalize_signing_key,
    restricted_loads as _restricted_loads,
    validate_data_value as _validate_data_value,
    validate_pickle_opcodes as _validate_pickle_opcodes,
)
from nexora.save.errors import (
    InvalidSaveError,
    SaveIntegrityError,
    UnsafeSaveDataError,
    UnsupportedSaveVersionError,
)


def _translate(exc: Exception) -> Exception:
    if isinstance(exc, UnsafeDataError):
        return UnsafeSaveDataError(str(exc))
    if isinstance(exc, DataIntegrityError):
        return SaveIntegrityError(str(exc))
    if isinstance(exc, UnsupportedDataVersionError):
        return UnsupportedSaveVersionError(str(exc))
    if isinstance(exc, (InvalidDataFileError, DataTypeMismatchError)):
        return InvalidSaveError(str(exc))
    return exc


def normalize_signing_key(key: bytes | str) -> bytes:
    return _normalize_signing_key(key)


def validate_save_value(value: Any, **kwargs) -> None:
    try:
        _validate_data_value(value, **kwargs)
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


def validate_pickle_opcodes(payload: bytes) -> None:
    try:
        _validate_pickle_opcodes(payload)
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


def restricted_loads(payload: bytes):
    try:
        return _restricted_loads(payload)
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


def encode_save(value, *, signing_key: bytes | str) -> bytes:
    try:
        return savegame_codec.encode(value, signing_key=signing_key)
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


def decode_save(raw: bytes, *, signing_key: bytes | str, max_payload_size: int):
    try:
        return savegame_codec.decode(
            raw,
            signing_key=signing_key,
            max_file_size=max_payload_size,
        )
    except Exception as exc:
        translated = _translate(exc)
        if translated is exc:
            raise
        raise translated from exc


__all__ = [
    "decode_save",
    "encode_save",
    "normalize_signing_key",
    "restricted_loads",
    "validate_pickle_opcodes",
    "validate_save_value",
]
