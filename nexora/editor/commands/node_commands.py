from __future__ import annotations

from copy import deepcopy

from nexora.scene.serialization.common import (
    apply_common_node_state,
    node_to_state,
)


def _insert_child(parent, child, index: int) -> None:
    parent.add_child(child)
    children = parent.children
    if child in children:
        children.remove(child)
    index = max(0, min(int(index), len(children)))
    children.insert(index, child)


def _build_node_from_state(state, world, registry, *, context=None):
    data = deepcopy(dict(state))
    node = registry.create(
        data["type"],
        data.get("name", "Node"),
        world,
        context=context or {},
    )
    apply_common_node_state(node, data)
    registry.load_properties(
        node,
        dict(data.get("properties", {})),
        context=context or {},
    )
    for child_state in data.get("children", []):
        child = _build_node_from_state(
            child_state,
            world,
            registry,
            context=context,
        )
        node.add_child(child)
    return node


class AddNodeCommand:
    def __init__(
        self,
        *,
        parent,
        registry,
        type_id: str,
        name: str,
        context: dict | None = None,
        configure=None,
    ) -> None:
        self.parent = parent
        self.registry = registry
        self.type_id = str(type_id)
        self.name = str(name).strip() or self.type_id
        self.context = dict(context or {})
        self.configure = configure
        self.label = f"Add {self.name}"
        self._state = None
        self._node = None
        self._index = len(parent.children)

    @property
    def node(self):
        return self._node

    def execute(self):
        if self._state is None:
            node = self.registry.create(
                self.type_id,
                self.name,
                self.parent.world,
                context=self.context,
            )
            _insert_child(self.parent, node, self._index)
            try:
                if self.configure is not None:
                    self.configure(node)
                self._state = node_to_state(node, self.registry)
            except Exception:
                node.destroy()
                raise
            self._node = node
            return node

        node = _build_node_from_state(
            self._state,
            self.parent.world,
            self.registry,
            context=self.context,
        )
        _insert_child(self.parent, node, self._index)
        self._node = node
        return node

    def undo(self):
        node = self._node
        if node is None:
            return None
        self._state = node_to_state(node, self.registry)
        node.destroy()
        self._node = None
        return None


class DeleteNodeCommand:
    def __init__(
        self,
        *,
        node,
        registry,
        context: dict | None = None,
    ) -> None:
        if node.parent is None:
            raise ValueError("Cannot delete a tree root node.")
        self.registry = registry
        self.context = dict(context or {})
        self.parent = node.parent
        self._index = self.parent.children.index(node)
        self._state = node_to_state(node, registry)
        self._node = node
        self.label = f"Delete {node.name}"

    @property
    def node(self):
        return self._node

    def execute(self):
        node = self._node
        if node is not None:
            self._state = node_to_state(node, self.registry)
            node.destroy()
            self._node = None
        return None

    def undo(self):
        node = _build_node_from_state(
            self._state,
            self.parent.world,
            self.registry,
            context=self.context,
        )
        _insert_child(self.parent, node, self._index)
        self._node = node
        return node


class RenameNodeCommand:
    def __init__(self, node, new_name: str) -> None:
        self.node = node
        self.old_name = str(node.name)
        self.new_name = str(new_name).strip()
        if not self.new_name:
            raise ValueError("Node name cannot be empty.")
        self.label = f"Rename {self.old_name}"

    def execute(self):
        self.node.name = self.new_name
        return self.node

    def undo(self):
        self.node.name = self.old_name
        return self.node
