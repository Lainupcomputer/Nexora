from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, decode_file, encode_file, load_file, save_file


def encode_state(
    state: dict[str, Any],
    *,
    version: int,
    signing_key: bytes | str,
) -> bytes:
    return encode_file(
        DataFile(DataType.Scene, version, state),
        signing_key=signing_key,
    )


def decode_state(
    raw: bytes,
    *,
    version: int,
    signing_key: bytes | str,
    max_file_size: int,
) -> dict[str, Any]:
    document = decode_file(
        raw,
        expected_type=DataType.Scene,
        signing_key=signing_key,
        max_payload_size=max_file_size,
    )
    if document.version != version:
        raise ValueError(f"Unsupported Nexora Scene data version: {document.version}")
    if not isinstance(document.data, dict):
        raise ValueError("Invalid Nexora Scene data.")
    return dict(document.data)


def save_state(
    state: dict[str, Any],
    path: str | Path,
    *,
    version: int,
    signing_key: bytes | str,
    max_file_size: int,
) -> Path:
    return save_file(
        path,
        DataFile(DataType.Scene, version, state),
        signing_key=signing_key,
        max_file_size=max_file_size,
    )


def load_state(
    path: str | Path,
    *,
    version: int,
    signing_key: bytes | str,
    max_file_size: int,
) -> dict[str, Any]:
    document = load_file(
        path,
        expected_type=DataType.Scene,
        signing_key=signing_key,
        max_file_size=max_file_size,
    )
    if document.version != version:
        raise ValueError(f"Unsupported Nexora Scene data version: {document.version}")
    if not isinstance(document.data, dict):
        raise ValueError("Invalid Nexora Scene data.")
    return dict(document.data)
