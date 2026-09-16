from __future__ import annotations

from pathlib import Path

from nexora.scene.serialization.common import apply_common_node_state, node_to_state


def _insert_child(parent, child, index: int) -> None:
    parent.add_child(child)
    children = parent.children
    if child in children:
        children.remove(child)
    index = max(0, min(int(index), len(children)))
    children.insert(index, child)


def _build_node_from_state(state, world, registry, *, context=None):
    data = dict(state)
    node = registry.create(data["type"], data.get("name", "Node"), world, context=context or {})
    apply_common_node_state(node, data)
    registry.load_properties(node, dict(data.get("properties", {})), context=context or {})
    for child_state in data.get("children", []):
        node.add_child(_build_node_from_state(child_state, world, registry, context=context))
    return node


def texture_source_for_assets(asset_path: str | Path, assets) -> str:
    path = Path(asset_path).resolve()
    root = Path(assets.root).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def prefab_instance_overrides_for_node(node, registry) -> dict:
    """Capture the editable root state of a prefab instance.

    Prefab instances are saved as a source path plus root overrides.  Keeping
    the current root state in the overrides means moving, renaming, or
    changing an instance in the editor survives a save/reload cycle.
    """

    transform = node.transform

    return {
        "name": str(node.name),
        "enabled": bool(node.enabled),
        "visible": bool(node.visible),
        "transform": {
            "x": float(transform.x),
            "y": float(transform.y),
            "rotation": float(transform.rotation),
            "scale_x": float(transform.scale_x),
            "scale_y": float(transform.scale_y),
        },
        "properties": registry.dump_properties(node),
    }


class AddImageSpriteCommand:
    def __init__(self, *, parent, registry, assets, asset_path, name, x, y, context=None) -> None:
        self.parent = parent
        self.registry = registry
        self.assets = assets
        self.asset_path = Path(asset_path).resolve()
        self.name = str(name).strip() or self.asset_path.stem or "Sprite"
        self.x = float(x); self.y = float(y)
        self.context = dict(context or {}); self.context.setdefault("assets", assets)
        self.label = f"Add Sprite {self.name}"
        self._node = None; self._state = None; self._index = len(parent.children)

    @property
    def node(self): return self._node

    def execute(self):
        if self._state is None:
            node = self.registry.create("AnimatedSprite", self.name, self.parent.world, context=self.context)
            source = texture_source_for_assets(self.asset_path, self.assets)
            texture = self.assets.texture(source)
            node.texture = texture
            node._nexora_texture_source = source
            node.width = float(texture.width); node.height = float(texture.height)
            node.transform.x = self.x; node.transform.y = self.y
            _insert_child(self.parent, node, self._index)
            self._node = node
            self._state = node_to_state(node, self.registry)
            return node
        node = _build_node_from_state(self._state, self.parent.world, self.registry, context=self.context)
        _insert_child(self.parent, node, self._index)
        self._node = node
        return node

    def undo(self):
        if self._node is None: return None
        self._state = node_to_state(self._node, self.registry)
        self._node.destroy(); self._node = None
        return None


class InstantiatePrefabCommand:
    """Undoable placement of one prefab instance into a scene tree."""

    def __init__(
        self,
        *,
        parent,
        prefab_serializer,
        registry,
        prefab_path,
        name,
        x,
        y,
        context=None,
    ) -> None:
        self.parent = parent
        self.prefab_serializer = prefab_serializer
        self.registry = registry
        self.prefab_path = Path(prefab_path).resolve()
        self.name = (
            str(name).strip()
            or self.prefab_path.stem
            or "Prefab"
        )
        self.x = float(x)
        self.y = float(y)
        self.context = dict(context or {})
        self.label = f"Add Prefab {self.name}"
        self._node = None
        self._index = len(parent.children)
        self._overrides = {
            "name": self.name,
            "transform": {
                "x": self.x,
                "y": self.y,
            },
        }

    @property
    def node(self):
        return self._node

    def execute(self):
        node = self.prefab_serializer.instantiate(
            self.prefab_path,
            self.parent.world,
            context=self.context,
            overrides=self._overrides,
        )
        _insert_child(self.parent, node, self._index)
        self._node = node
        self._overrides = prefab_instance_overrides_for_node(
            node,
            self.registry,
        )
        return node

    def undo(self):
        if self._node is None:
            return None

        self._overrides = prefab_instance_overrides_for_node(
            self._node,
            self.registry,
        )
        self._node.destroy()
        self._node = None
        return None
