from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nexora.scene.scene import Scene
from nexora.scene.serialization import SceneSerializer


SceneFactory = Callable[[], Scene]


@dataclass(slots=True)
class SceneRegistration:
    """Registered scene factory."""

    name: str
    factory: SceneFactory
    keep_loaded: bool = True


@dataclass(slots=True)
class SerializedSceneRegistration:
    """Registered .nxscene source."""

    name: str
    path: Path
    asset_groups: tuple[str, ...]
    metadata: dict[str, Any]
    keep_loaded: bool = False


class SceneRegistryMixin:
    @property
    def scene_serializer(self) -> SceneSerializer | None:
        return self._scene_serializer

    def bind_scene_serializer(
        self,
        serializer: SceneSerializer,
    ) -> None:
        if not isinstance(serializer, SceneSerializer):
            raise TypeError("serializer must be a SceneSerializer.")
        self._scene_serializer = serializer

    def bind_assets(self, asset_manager) -> None:
        if asset_manager is None:
            raise ValueError("asset_manager cannot be None.")
        self._asset_manager = asset_manager

    def bind_serialization_context_provider(
        self,
        provider: Callable[[], dict[str, Any]] | None,
    ) -> None:
        if provider is not None and not callable(provider):
            raise TypeError("provider must be callable or None.")
        self._serialization_context_provider = provider

    def _serialization_context(
        self,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if self._serialization_context_provider is not None:
            provided = self._serialization_context_provider()
            if provided:
                context.update(dict(provided))
        if extra:
            context.update(dict(extra))
        return context

    def _require_scene_serializer(self) -> SceneSerializer:
        if self._scene_serializer is None:
            raise RuntimeError(
                "SceneManager has no SceneSerializer. "
                "Bind one before using serialized scenes."
            )
        return self._scene_serializer

    def _require_asset_manager(self):
        if self._asset_manager is None:
            raise RuntimeError(
                "SceneManager has no AssetManager. "
                "Bind one before loading serialized scene asset groups."
            )
        return self._asset_manager

    def register(
        self,
        name: str,
        factory: SceneFactory,
        *,
        keep_loaded: bool = True,
    ) -> None:
        """
        Register a scene factory.

        Registration itself does not create the Scene.

        Example:

            scenes.register(
                "Dungeon",
                lambda: DungeonScene(),
                keep_loaded=False,
            )
        """

        name = str(
            name
        )

        if not name:
            raise ValueError(
                "Scene name cannot be empty."
            )

        if not callable(
            factory
        ):
            raise TypeError(
                "Scene factory must be callable."
            )

        if name in self._registrations:
            raise ValueError(
                f"Scene '{name}' is already registered."
            )

        self._registrations[
            name
        ] = SceneRegistration(
            name=name,
            factory=factory,
            keep_loaded=bool(
                keep_loaded
            ),
        )

    def unregister(
        self,
        name: str,
        *,
        unload: bool = False,
    ) -> None:
        """
        Remove a scene registration.

        unload=True also destroys an existing loaded instance.
        """

        self._ensure_not_transitioning()

        if name not in self._registrations:
            raise KeyError(
                f"Scene '{name}' is not registered."
            )

        if (
            unload
            and self.is_loaded(
                name
            )
        ):
            self.unload(
                name
            )

        del self._registrations[
            name
        ]

    def is_registered(
        self,
        name: str,
    ) -> bool:
        return (
            name in self._registrations
            or name in self._serialized_registrations
        )

    def registration(
        self,
        name: str,
    ) -> SceneRegistration | None:
        return self._registrations.get(
            name
        )

    def register_serialized(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        keep_loaded: bool = False,
        replace: bool = False,
    ) -> SerializedSceneRegistration:
        serializer = self._require_scene_serializer()
        source = Path(path).expanduser().resolve()
        metadata = serializer.inspect_metadata(source)

        resolved_name = str(name or metadata["name"]).strip()
        if not resolved_name:
            raise ValueError("Serialized scene name cannot be empty.")

        if resolved_name in self._registrations:
            raise ValueError(
                f"Scene '{resolved_name}' already has a factory registration."
            )
        if resolved_name in self._scenes:
            raise ValueError(
                f"Scene '{resolved_name}' is already loaded."
            )
        if resolved_name in self._serialized_registrations and not replace:
            raise ValueError(
                f"Serialized scene '{resolved_name}' is already registered."
            )

        groups = tuple(
            dict.fromkeys(str(group).strip() for group in metadata.get("asset_groups", ()) if str(group).strip())
        )
        registration = SerializedSceneRegistration(
            name=resolved_name,
            path=source,
            asset_groups=groups,
            metadata=dict(metadata.get("metadata", {})),
            keep_loaded=bool(keep_loaded),
        )
        self._serialized_registrations[resolved_name] = registration
        return registration

    def unregister_serialized(
        self,
        name: str,
        *,
        unload: bool = False,
    ) -> None:
        self._ensure_not_transitioning()
        if name not in self._serialized_registrations:
            raise KeyError(f"Serialized scene '{name}' is not registered.")
        if unload and self.is_loaded(name):
            self.unload(name)
        del self._serialized_registrations[name]

    def serialized_registration(
        self,
        name: str,
    ) -> SerializedSceneRegistration | None:
        return self._serialized_registrations.get(name)

    @property
    def serialized_names(self) -> tuple[str, ...]:
        return tuple(self._serialized_registrations.keys())

    def resolve_serialized_scene_name(
        self,
        reference: str | Path,
    ) -> str:
        """Resolve a serialized scene name from a name or .nxscene path.

        Exact registered names win. Path references are matched against the
        registered SerializedSceneRegistration paths. A basename-only match is
        accepted when it is unique.
        """

        raw = str(reference).strip()
        if not raw:
            raise ValueError("Serialized scene reference cannot be empty.")

        if raw in self._serialized_registrations:
            return raw

        candidate_path = Path(raw).expanduser()
        try:
            resolved_path = candidate_path.resolve()
        except OSError:
            resolved_path = candidate_path

        exact_matches: list[str] = []
        basename_matches: list[str] = []

        for name, registration in self._serialized_registrations.items():
            registered_path = registration.path

            if registered_path == resolved_path:
                exact_matches.append(name)
                continue

            if registered_path.name == candidate_path.name:
                basename_matches.append(name)

        if len(exact_matches) == 1:
            return exact_matches[0]

        if len(exact_matches) > 1:
            raise ValueError(
                f"Serialized scene reference {raw!r} is ambiguous."
            )

        if len(basename_matches) == 1:
            return basename_matches[0]

        if len(basename_matches) > 1:
            raise ValueError(
                f"Serialized scene basename {candidate_path.name!r} is ambiguous."
            )

        raise KeyError(
            f"No registered serialized scene matches {raw!r}."
        )
