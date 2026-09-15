from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .errors import SceneMigrationError, UnsupportedSceneVersionError


Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationRegistry:
    """Sequential schema migrations for scene/prefab state dictionaries."""

    def __init__(self, current_version: int) -> None:
        current_version = int(current_version)
        if current_version <= 0:
            raise ValueError("current_version must be greater than zero")
        self.current_version = current_version
        self._migrations: dict[int, Migration] = {}

    def register(self, from_version: int, migration: Migration) -> None:
        from_version = int(from_version)
        if from_version <= 0:
            raise ValueError("from_version must be greater than zero")
        if not callable(migration):
            raise TypeError("migration must be callable")
        self._migrations[from_version] = migration

    def migrate(self, state: dict[str, Any]) -> dict[str, Any]:
        version = int(state.get("schema_version", 1))

        if version > self.current_version:
            raise UnsupportedSceneVersionError(
                f"Schema version {version} is newer than supported version "
                f"{self.current_version}."
            )

        current = dict(state)
        while version < self.current_version:
            migration = self._migrations.get(version)
            if migration is None:
                raise SceneMigrationError(
                    f"Missing migration from schema version {version} "
                    f"to {version + 1}."
                )
            try:
                current = migration(current)
            except Exception as exc:
                raise SceneMigrationError(
                    f"Migration from schema version {version} failed."
                ) from exc

            version += 1
            current["schema_version"] = version

        return current
