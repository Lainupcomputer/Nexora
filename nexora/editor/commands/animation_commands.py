from __future__ import annotations


class AnimationClipCommand:
    """Undoable add/remove operation for a node-owned animation clip."""

    def __init__(self, target, clip) -> None:
        if not hasattr(target, "add_animation") or not hasattr(target, "remove_animation"):
            raise TypeError("Animation target must provide add_animation/remove_animation.")
        self.target = target
        self.clip = clip
        self.label = f"Add Animation {clip.name}"

    def execute(self):
        self.target.add_animation(self.clip)
        return self.target

    def undo(self):
        self.target.remove_animation(self.clip.name)
        return self.target
