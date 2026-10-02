from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, decode_file, encode_file, load_file, save_file
from nexora.data.errors import InvalidDataFileError, UnsupportedDataVersionError

VERSION = 1


def encode(
    envelope: dict[str, Any],
    *,
    signing_key: bytes | str,
) -> bytes:
    return encode_file(
        DataFile(DataType.SaveGame, VERSION, envelope),
        signing_key=signing_key,
    )


def decode(
    raw: bytes,
    *,
    signing_key: bytes | str,
    max_file_size: int,
) -> dict[str, Any]:
    document = decode_file(
        raw,
        expected_type=DataType.SaveGame,
        signing_key=signing_key,
        max_payload_size=max_file_size,
    )
    if document.version != VERSION:
        raise UnsupportedDataVersionError(
            f"Unsupported Nexora Savegame data version: {document.version}"
        )
    if not isinstance(document.data, dict):
        raise InvalidDataFileError("Invalid Nexora Savegame data.")
    return dict(document.data)


def save(
    envelope: dict[str, Any],
    path: str | Path,
    *,
    signing_key: bytes | str,
    max_file_size: int,
) -> Path:
    return save_file(
        path,
        DataFile(DataType.SaveGame, VERSION, envelope),
        signing_key=signing_key,
        max_file_size=max_file_size,
    )


def load(
    path: str | Path,
    *,
    signing_key: bytes | str,
    max_file_size: int,
) -> dict[str, Any]:
    document = load_file(
        path,
        expected_type=DataType.SaveGame,
        signing_key=signing_key,
        max_file_size=max_file_size,
    )
    if document.version != VERSION:
        raise UnsupportedDataVersionError(
            f"Unsupported Nexora Savegame data version: {document.version}"
        )
    if not isinstance(document.data, dict):
        raise InvalidDataFileError("Invalid Nexora Savegame data.")
    return dict(document.data)
