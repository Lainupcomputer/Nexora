from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nexora.scene import Scene


@dataclass(slots=True, frozen=True)
class SceneTreeEntry:
    node: object
    depth: int
    branch: str

    @property
    def label(self) -> str:
        name = str(getattr(self.node, "name", type(self.node).__name__))
        prefix = "    " * max(0, self.depth)
        marker = "▾ " if getattr(self.node, "children", ()) else "  "
        return f"{prefix}{marker}{name}"


class EditorDocument:
    """Editable scene document owned by the editor.

    The document scene is deliberately separate from the running EditorScene.
    It owns the current file path and dirty state and provides the small set of
    operations the editor UI needs for new/open/save workflows.
    """

    def __init__(
        self,
        scene: Scene | None = None,
        *,
        path: str | Path | None = None,
    ) -> None:
        self.scene = scene or Scene("Untitled")
        self.path = Path(path).resolve() if path is not None else None
        self.dirty = False

    @property
    def display_name(self) -> str:
        if self.path is not None:
            return self.path.stem
        return self.scene.name

    @property
    def title(self) -> str:
        suffix = " *" if self.dirty else ""
        return f"{self.display_name}{suffix}"

    def mark_dirty(self) -> None:
        self.dirty = True

    def mark_clean(self) -> None:
        self.dirty = False

    def replace(
        self,
        scene: Scene,
        *,
        path: str | Path | None = None,
        dirty: bool = False,
        destroy_previous: bool = True,
    ) -> None:
        previous = self.scene
        self.scene = scene
        self.path = Path(path).resolve() if path is not None else None
        self.dirty = bool(dirty)

        if destroy_previous and previous is not scene:
            destroy = getattr(previous, "destroy", None)
            if callable(destroy):
                destroy()

    def new(self, name: str = "Untitled") -> Scene:
        name = str(name).strip() or "Untitled"
        scene = Scene(name)
        self.replace(scene, path=None, dirty=True)
        return scene

    def load(self, serializer, path: str | Path, *, context: dict | None = None) -> Scene:
        resolved = Path(path).expanduser().resolve()
        scene = serializer.load(resolved, context=context)
        self.replace(scene, path=resolved, dirty=False)
        return scene

    def save(self, serializer) -> Path:
        if self.path is None:
            raise ValueError("Document has no path. Use save_as() first.")

        saved = serializer.save(self.scene, self.path).resolve()
        self.path = saved
        self.dirty = False
        return saved

    def save_as(self, serializer, path: str | Path) -> Path:
        saved = serializer.save(
            self.scene,
            Path(path).expanduser().resolve(),
        ).resolve()
        self.path = saved
        self.dirty = False
        return saved

    def iter_tree_entries(self) -> tuple[SceneTreeEntry, ...]:
        entries: list[SceneTreeEntry] = []

        def append_tree(node, depth: int, branch: str) -> None:
            entries.append(
                SceneTreeEntry(
                    node=node,
                    depth=depth,
                    branch=branch,
                )
            )
            for child in tuple(getattr(node, "children", ())):
                append_tree(child, depth + 1, branch)

        append_tree(self.scene.root, 0, "world")
        append_tree(self.scene.ui, 0, "ui")
        return tuple(entries)
