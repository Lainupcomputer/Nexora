from __future__ import annotations


class SceneSerializationError(Exception):
    """Base error for Nexora scene/prefab serialization."""


class InvalidSceneFileError(SceneSerializationError):
    """Raised when a scene/prefab container is invalid."""


class SceneIntegrityError(SceneSerializationError):
    """Raised when HMAC verification fails."""


class UnsupportedSceneVersionError(SceneSerializationError):
    """Raised for unsupported container/schema versions."""


class UnregisteredNodeTypeError(SceneSerializationError):
    """Raised when a node type is not registered in the NodeFactory."""


class SceneMigrationError(SceneSerializationError):
    """Raised when a required scene/prefab migration is unavailable or fails."""
