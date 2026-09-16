from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransformSnapshot:
    """Serializable-in-memory editor snapshot of one local transform."""

    x: float
    y: float
    rotation: float
    scale_x: float
    scale_y: float

    @classmethod
    def from_node(
        cls,
        node,
    ) -> TransformSnapshot:
        transform = node.transform

        return cls(
            x=float(transform.x),
            y=float(transform.y),
            rotation=float(transform.rotation),
            scale_x=float(transform.scale_x),
            scale_y=float(transform.scale_y),
        )

    def apply(
        self,
        node,
    ) -> None:
        transform = node.transform

        transform.x = float(self.x)
        transform.y = float(self.y)
        transform.rotation = float(self.rotation)
        transform.scale_x = float(self.scale_x)
        transform.scale_y = float(self.scale_y)


class TransformNodeCommand:
    """One undoable viewport transform operation.

    Gizmo dragging updates the node live. At mouse release this command is
    pushed to the normal editor command stack. execute() is intentionally
    idempotent, so executing it at release simply reapplies the already visible
    final transform and records one clean history item.
    """

    def __init__(
        self,
        node,
        before: TransformSnapshot,
        after: TransformSnapshot,
        *,
        label: str = "Transform Node",
    ) -> None:
        self.node = node
        self.before = before
        self.after = after
        self.label = str(label)

    def execute(
        self,
    ):
        self.after.apply(
            self.node
        )

        return self.node

    def undo(
        self,
    ):
        self.before.apply(
            self.node
        )

        return self.node
