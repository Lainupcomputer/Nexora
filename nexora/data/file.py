from __future__ import annotations

import hashlib
import hmac
import io
import os
import pickle
import pickletools
import struct
import tempfile
from pathlib import Path
from typing import Any

from .document import DataFile
from .errors import (
    DataIntegrityError,
    DataTypeMismatchError,
    InvalidDataFileError,
    UnsafeDataError,
    UnsupportedDataVersionError,
)
from .types import DataType

MAGIC = b"NXDATA01"
CONTAINER_VERSION = 1
FLAG_SIGNED = 0x01
DIGEST_SIZE = 32
DEFAULT_MAX_PAYLOAD_SIZE = 128 * 1024 * 1024

_HEADER_STRUCT = struct.Struct(">8sHBQ32s")
_HEADER_PREFIX_STRUCT = struct.Struct(">8sHBQ")

_SAFE_SCALAR_TYPES = (type(None), bool, int, float, str, bytes)
_FORBIDDEN_OPCODES = {
    "GLOBAL",
    "STACK_GLOBAL",
    "REDUCE",
    "BUILD",
    "OBJ",
    "INST",
    "NEWOBJ",
    "NEWOBJ_EX",
    "EXT1",
    "EXT2",
    "EXT4",
    "PERSID",
    "BINPERSID",
}


def normalize_signing_key(key: bytes | str) -> bytes:
    if isinstance(key, str):
        key = key.encode("utf-8")
    if not isinstance(key, bytes):
        raise TypeError("signing_key must be bytes or str.")
    if len(key) < 32:
        raise ValueError("signing_key must contain at least 32 bytes.")
    return key


def validate_data_value(
    value: Any,
    *,
    max_depth: int = 64,
    max_items: int = 1_000_000,
    max_string_size: int = 4 * 1024 * 1024,
    max_bytes_size: int = 32 * 1024 * 1024,
) -> None:
    """Validate data before it enters the generic Pickle container."""
    count = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise UnsafeDataError("Data exceeds maximum nesting depth.")
        count += 1
        if count > max_items:
            raise UnsafeDataError("Data exceeds maximum item count.")

        if isinstance(current, _SAFE_SCALAR_TYPES):
            if isinstance(current, str) and len(current.encode("utf-8")) > max_string_size:
                raise UnsafeDataError("String exceeds maximum size.")
            if isinstance(current, bytes) and len(current) > max_bytes_size:
                raise UnsafeDataError("Bytes object exceeds maximum size.")
            continue
        if isinstance(current, (list, tuple)):
            stack.extend((item, depth + 1) for item in current)
            continue
        if isinstance(current, dict):
            for key, item in current.items():
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
            continue
        raise UnsafeDataError(f"Unsupported data type: {type(current).__name__}")


def validate_pickle_opcodes(payload: bytes) -> None:
    try:
        for opcode, _argument, position in pickletools.genops(payload):
            if opcode.name in _FORBIDDEN_OPCODES:
                raise UnsafeDataError(
                    f"Unsafe pickle opcode '{opcode.name}' at byte {position}."
                )
    except UnsafeDataError:
        raise
    except Exception as exc:
        raise InvalidDataFileError("Could not parse pickle payload.") from exc


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        raise pickle.UnpicklingError(
            f"Global object loading is disabled: {module}.{name}"
        )

    def persistent_load(self, pid):
        raise pickle.UnpicklingError("Persistent pickle IDs are disabled.")


def restricted_loads(payload: bytes) -> Any:
    validate_pickle_opcodes(payload)
    try:
        value = RestrictedUnpickler(io.BytesIO(payload)).load()
    except (pickle.UnpicklingError, EOFError, ValueError, TypeError) as exc:
        raise InvalidDataFileError("Invalid pickle payload.") from exc
    validate_data_value(value)
    return value


def encode_file(document: DataFile, *, signing_key: bytes | str | None = None) -> bytes:
    if not isinstance(document, DataFile):
        raise TypeError("document must be a DataFile.")

    root = {
        "data_type": document.data_type.value,
        "version": document.version,
        "data": document.data,
    }
    validate_data_value(root)
    payload = pickle.dumps(root, protocol=pickle.HIGHEST_PROTOCOL)
    validate_pickle_opcodes(payload)

    flags = FLAG_SIGNED if signing_key is not None else 0
    prefix = _HEADER_PREFIX_STRUCT.pack(MAGIC, CONTAINER_VERSION, flags, len(payload))
    if signing_key is None:
        digest = bytes(DIGEST_SIZE)
    else:
        digest = hmac.new(
            normalize_signing_key(signing_key), prefix + payload, hashlib.sha256
        ).digest()
    return _HEADER_STRUCT.pack(
        MAGIC, CONTAINER_VERSION, flags, len(payload), digest
    ) + payload


def decode_file(
    raw: bytes,
    *,
    expected_type: DataType | None = None,
    signing_key: bytes | str | None = None,
    max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
) -> DataFile:
    if max_payload_size <= 0:
        raise ValueError("max_payload_size must be greater than zero.")
    if len(raw) < _HEADER_STRUCT.size:
        raise InvalidDataFileError("Nexora data file is too small.")
    try:
        magic, container_version, flags, payload_length, stored_digest = _HEADER_STRUCT.unpack(
            raw[: _HEADER_STRUCT.size]
        )
    except struct.error as exc:
        raise InvalidDataFileError("Invalid Nexora data header.") from exc

    if magic != MAGIC:
        raise InvalidDataFileError("Unexpected Nexora data file magic.")
    if container_version != CONTAINER_VERSION:
        raise UnsupportedDataVersionError(
            f"Unsupported Nexora data container version: {container_version}"
        )
    if flags & ~FLAG_SIGNED:
        raise InvalidDataFileError("Nexora data file contains unknown flags.")
    if payload_length > int(max_payload_size):
        raise InvalidDataFileError("Payload exceeds configured maximum size.")
    if len(raw) != _HEADER_STRUCT.size + payload_length:
        raise InvalidDataFileError("Payload length does not match header.")

    payload = raw[_HEADER_STRUCT.size :]
    if flags & FLAG_SIGNED:
        if signing_key is None:
            raise DataIntegrityError("A signing key is required for this Nexora data file.")
        prefix = _HEADER_PREFIX_STRUCT.pack(
            magic, container_version, flags, payload_length
        )
        expected_digest = hmac.new(
            normalize_signing_key(signing_key), prefix + payload, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(stored_digest, expected_digest):
            raise DataIntegrityError("Nexora data authentication failed.")
    elif stored_digest != bytes(DIGEST_SIZE):
        raise InvalidDataFileError("Unsigned Nexora data file has an invalid digest field.")

    root = restricted_loads(payload)
    if not isinstance(root, dict):
        raise InvalidDataFileError("Nexora data root must be a dictionary.")
    try:
        data_type = DataType(root["data_type"])
        version = int(root["version"])
        data = root["data"]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidDataFileError("Nexora data document header is invalid.") from exc
    if version <= 0:
        raise InvalidDataFileError("Nexora data schema version must be positive.")
    if expected_type is not None and data_type is not DataType(expected_type):
        raise DataTypeMismatchError(
            f"Expected {DataType(expected_type).value}, got {data_type.value}."
        )
    return DataFile(data_type=data_type, version=version, data=data)


def atomic_write(path: str | Path, raw: bytes) -> Path:
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=destination.name + ".",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
        return destination.resolve()
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def save_file(
    path: str | Path,
    document: DataFile,
    *,
    signing_key: bytes | str | None = None,
    max_file_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
) -> Path:
    raw = encode_file(document, signing_key=signing_key)
    if len(raw) > int(max_file_size):
        raise InvalidDataFileError("Encoded Nexora data file exceeds maximum size.")
    return atomic_write(path, raw)


def load_file(
    path: str | Path,
    *,
    expected_type: DataType | None = None,
    signing_key: bytes | str | None = None,
    max_file_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
) -> DataFile:
    source = Path(path).expanduser().resolve()
    try:
        if source.stat().st_size > int(max_file_size):
            raise InvalidDataFileError("Nexora data file exceeds maximum size.")
        raw = source.read_bytes()
    except OSError as exc:
        raise InvalidDataFileError(f"Could not read Nexora data file: {source}") from exc
    return decode_file(
        raw,
        expected_type=expected_type,
        signing_key=signing_key,
        max_payload_size=max_file_size,
    )


__all__ = [
    "MAGIC",
    "CONTAINER_VERSION",
    "DEFAULT_MAX_PAYLOAD_SIZE",
    "RestrictedUnpickler",
    "atomic_write",
    "decode_file",
    "encode_file",
    "load_file",
    "normalize_signing_key",
    "restricted_loads",
    "save_file",
    "validate_data_value",
    "validate_pickle_opcodes",
]
