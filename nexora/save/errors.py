from __future__ import annotations


class SaveError(Exception):
    """
    Base exception for Nexora save errors.
    """


class SaveNotFoundError(SaveError):
    """
    Requested save slot does not exist.
    """


class InvalidSaveError(SaveError):
    """
    Save file is malformed or unsupported.
    """


class SaveIntegrityError(SaveError):
    """
    Save file failed integrity/authenticity verification.
    """


class UnsupportedSaveVersionError(SaveError):
    """
    Save file uses an unsupported format version.
    """


class UnsafeSaveDataError(SaveError):
    """
    Save contains unsupported or unsafe data.
    """