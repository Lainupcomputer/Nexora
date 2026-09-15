from __future__ import annotations

import hashlib
import hmac
import struct
from typing import Any

from nexora.save.codec import (
    normalize_signing_key,
    restricted_loads,
    validate_pickle_opcodes,
    validate_save_value,
)

from .errors import (
    InvalidSceneFileError,
    SceneIntegrityError,
    UnsupportedSceneVersionError,
)


CONTAINER_VERSION = 1
DIGEST_SIZE = 32
SCENE_MAGIC = b"NXSCN001"
PREFAB_MAGIC = b"NXPFB001"

_HEADER_STRUCT = struct.Struct(">8sHQ32s")
_HEADER_PREFIX_STRUCT = struct.Struct(">8sHQ")


def encode_secure_pickle(
    value: Any,
    *,
    signing_key: bytes | str,
    magic: bytes,
) -> bytes:
    """Encode safe primitive data into an authenticated Nexora container."""
    import pickle

    if len(magic) != 8:
        raise ValueError("magic must contain exactly 8 bytes")

    key = normalize_signing_key(signing_key)
    validate_save_value(value)

    payload = pickle.dumps(
        value,
        protocol=pickle.HIGHEST_PROTOCOL,
    )
    validate_pickle_opcodes(payload)

    prefix = _HEADER_PREFIX_STRUCT.pack(
        magic,
        CONTAINER_VERSION,
        len(payload),
    )
    digest = hmac.new(
        key,
        prefix + payload,
        hashlib.sha256,
    ).digest()

    return _HEADER_STRUCT.pack(
        magic,
        CONTAINER_VERSION,
        len(payload),
        digest,
    ) + payload


def decode_secure_pickle(
    raw: bytes,
    *,
    signing_key: bytes | str,
    expected_magic: bytes,
    max_payload_size: int,
) -> Any:
    """Authenticate a Nexora container before restricted unpickling."""
    key = normalize_signing_key(signing_key)

    if max_payload_size <= 0:
        raise ValueError("max_payload_size must be greater than zero")

    header_size = _HEADER_STRUCT.size
    if len(raw) < header_size:
        raise InvalidSceneFileError("Scene/prefab file is too small.")

    try:
        magic, version, payload_length, stored_digest = _HEADER_STRUCT.unpack(
            raw[:header_size]
        )
    except struct.error as exc:
        raise InvalidSceneFileError("Invalid scene/prefab header.") from exc

    if magic != expected_magic:
        raise InvalidSceneFileError("Unexpected Nexora scene/prefab file type.")

    if version != CONTAINER_VERSION:
        raise UnsupportedSceneVersionError(
            f"Unsupported container version: {version}"
        )

    if payload_length > int(max_payload_size):
        raise InvalidSceneFileError("Payload exceeds configured maximum size.")

    expected_size = header_size + payload_length
    if len(raw) != expected_size:
        raise InvalidSceneFileError("Payload length does not match header.")

    payload = raw[header_size:]
    prefix = _HEADER_PREFIX_STRUCT.pack(
        magic,
        version,
        payload_length,
    )
    expected_digest = hmac.new(
        key,
        prefix + payload,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(stored_digest, expected_digest):
        raise SceneIntegrityError("Scene/prefab authentication failed.")

    try:
        return restricted_loads(payload)
    except Exception as exc:
        raise InvalidSceneFileError("Invalid scene/prefab payload.") from exc
