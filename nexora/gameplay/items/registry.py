from __future__ import annotations

"""Runtime registry for Nexora data-backed ``.nitem`` resources."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .asset import ITEM_ASSET_SUFFIX, ItemAsset, ItemDefinition


Callback = Callable[..., Any]


@dataclass(slots=True)
class ItemResource:
    """One loaded item together with resolved runtime references."""

    item: ItemDefinition
    source_path: Path
    asset_paths: dict[str, Path] = field(default_factory=dict)
    assets: dict[str, Any] = field(default_factory=dict)
    callbacks: dict[str, Callback] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def __getattr__(self, name: str) -> Any:
        """Keep resource access convenient for runtime systems."""
        return getattr(self.item, name)


class ItemCallbackRegistry:
    """Maps stable callback IDs from item files to live Python callables."""

    def __init__(self) -> None:
        self._callbacks: dict[str, Callback] = {}

    def register(self, callback_id: str, callback: Callback) -> Callback:
        callback_id = str(callback_id).strip()
        if not callback_id:
            raise ValueError("callback_id must not be empty")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._callbacks[callback_id] = callback
        return callback

    def unregister(self, callback_id: str) -> Callback | None:
        return self._callbacks.pop(str(callback_id), None)

    def resolve(self, callback_id: str) -> Callback | None:
        return self._callbacks.get(str(callback_id).strip())

    def __contains__(self, callback_id: object) -> bool:
        return callback_id in self._callbacks


class ItemRegistry:
    """Discover, load and resolve all project and mod item resources.

    Relative search paths are resolved against ``project_path``.  The default
    path is ``items``.  Paths are processed in order, so a later path
    can intentionally override an item with the same ID from an earlier path.
    """

    def __init__(
        self,
        project_path: str | Path = ".",
        *,
        item_paths: Iterable[str | Path] | None = None,
        asset_manager: Any | None = None,
        callbacks: ItemCallbackRegistry | None = None,
    ) -> None:
        self.project_path = Path(project_path).expanduser().resolve()
        self.asset_manager = asset_manager
        self.callbacks = callbacks or ItemCallbackRegistry()
        self._paths: list[Path] = []
        self._items: dict[str, ItemResource] = {}
        self.errors: dict[Path, str] = {}
        self.duplicates: list[tuple[str, Path, Path]] = []
        self.add_path(self.project_path / "items")
        for path in item_paths or ():
            self.add_path(path)

    @property
    def paths(self) -> tuple[Path, ...]:
        return tuple(self._paths)

    @property
    def items(self) -> tuple[ItemResource, ...]:
        return tuple(self._items.values())

    def add_path(self, path: str | Path, *, prepend: bool = False) -> Path:
        resolved = self._resolve_project_path(path)
        if resolved not in self._paths:
            if prepend:
                self._paths.insert(0, resolved)
            else:
                self._paths.append(resolved)
        return resolved

    def remove_path(self, path: str | Path) -> bool:
        resolved = self._resolve_project_path(path)
        if resolved not in self._paths:
            return False
        self._paths.remove(resolved)
        return True

    def clear(self) -> None:
        self._items.clear()
        self.errors.clear()
        self.duplicates.clear()

    def load_all(self, on_progress: Callable[[int, int, Path], None] | None = None) -> tuple[ItemResource, ...]:
        self.clear()
        files: list[Path] = []
        for root in self._paths:
            if root.is_dir():
                files.extend(sorted(root.rglob(f"*{ITEM_ASSET_SUFFIX}"), key=lambda path: str(path).lower()))
        total = len(files)
        for current, path in enumerate(files, 1):
            try:
                asset = ItemAsset.load(path)
                resource = self._resolve_resource(asset.item, path)
                previous = self._items.get(resource.item.item_id)
                if previous is not None:
                    self.duplicates.append((resource.item.item_id, previous.source_path, path))
                self._items[resource.item.item_id] = resource
            except Exception as exc:
                self.errors[path] = str(exc)
            if on_progress is not None:
                on_progress(current, total, path)
        return self.items

    def reload(self, on_progress: Callable[[int, int, Path], None] | None = None) -> tuple[ItemResource, ...]:
        return self.load_all(on_progress=on_progress)

    def get(self, item_id: str) -> ItemResource | None:
        return self._items.get(str(item_id))

    def require(self, item_id: str) -> ItemResource:
        resource = self.get(item_id)
        if resource is None:
            raise KeyError(f"Unknown item ID: {item_id}")
        return resource

    def find(self, query: str) -> tuple[ItemResource, ...]:
        query = str(query).strip().lower()
        if not query:
            return self.items
        return tuple(
            resource
            for resource in self.items
            if query in resource.item.item_id.lower()
            or query in resource.item.name.lower()
            or any(query in tag.lower() for tag in resource.item.tags)
        )

    def _resolve_project_path(self, path: str | Path) -> Path:
        value = Path(path).expanduser()
        if not value.is_absolute():
            value = self.project_path / value
        return value.resolve()

    def _resolve_asset_path(self, value: str | Path, source_path: Path) -> Path:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        project_asset = (self.project_path / "assets" / candidate).resolve()
        if project_asset.is_file():
            return project_asset
        return (source_path.parent / candidate).resolve()

    def _resolve_resource(self, item: ItemDefinition, source_path: Path) -> ItemResource:
        resource = ItemResource(item=item, source_path=source_path.resolve())
        visual_values = {
            "icon": item.icon,
            "world_sprite": item.visuals.get("world_sprite", ""),
            "drop_sprite": item.visuals.get("drop_sprite", ""),
            "animation": item.use_action.get("animation", ""),
        }
        for name, value in visual_values.items():
            if value:
                path = self._resolve_asset_path(value, source_path)
                resource.asset_paths[name] = path
                if not path.is_file():
                    resource.warnings.append(f"Missing {name} asset: {value}")
                    continue
                self._load_runtime_asset(resource, name, path)

        for name, value in item.audio.items():
            if not value:
                continue
            path = self._resolve_asset_path(value, source_path)
            resource.asset_paths[f"audio:{name}"] = path
            if not path.is_file():
                resource.warnings.append(f"Missing audio asset: {value}")
                continue
            self._load_runtime_asset(resource, f"audio:{name}", path)

        callback_values = dict(item.use_action.get("callbacks", {}))
        for key in ("callback", "use_callback", "equip_callback", "drop_callback"):
            if item.use_action.get(key):
                callback_values[key] = item.use_action[key]
        for name, callback_id in callback_values.items():
            callback = self.callbacks.resolve(str(callback_id))
            if callback is None:
                resource.warnings.append(f"Unregistered callback: {callback_id}")
            else:
                resource.callbacks[name] = callback
        return resource

    def _load_runtime_asset(self, resource: ItemResource, name: str, path: Path) -> None:
        if self.asset_manager is None:
            return
        try:
            if name.startswith("audio:"):
                resource.assets[name] = self.asset_manager.sound(path)
            elif name == "animation":
                resource.assets[name] = path
            elif getattr(self.asset_manager, "_gpu_device", None) is not None:
                resource.assets[name] = self.asset_manager.texture(path)
            else:
                resource.assets[name] = self.asset_manager.load_texture(path)
        except Exception as exc:
            resource.warnings.append(f"Could not resolve {name} asset {path.name}: {exc}")


__all__ = ["Callback", "ItemCallbackRegistry", "ItemRegistry", "ItemResource"]
