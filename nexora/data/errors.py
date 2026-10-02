from __future__ import annotations


class DataError(Exception):
    """Base class for Nexora data container errors."""


class InvalidDataFileError(DataError):
    """The file is malformed or cannot be decoded safely."""


class DataIntegrityError(DataError):
    """Authenticated data failed integrity verification."""


class UnsupportedDataVersionError(DataError):
    """The generic Nexora data container version is unsupported."""


class DataTypeMismatchError(DataError):
    """The document type does not match the requested type."""


class UnsafeDataError(DataError):
    """The payload contains unsupported or unsafe Python data."""


__all__ = [
    "DataError",
    "InvalidDataFileError",
    "DataIntegrityError",
    "UnsupportedDataVersionError",
    "DataTypeMismatchError",
    "UnsafeDataError",
]
