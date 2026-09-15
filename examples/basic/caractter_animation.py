from __future__ import annotations

from nexora.animation import AnimationSet
from nexora.nodes import AnimatedSprite


class Player(AnimatedSprite):
    def __init__(
        self,
        name: str,
        world,
        input_manager,
        texture,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.input = input_manager
        self.texture = texture

        # Größe eines einzelnen Sprite-Sheet-Frames.
        self.width = 64.0
        self.height = 128.0

        # Füße bleiben auf der Position des Charakters.
        self.origin = (
            0.5,
            1.0,
        )

        # Unser Idle-Sheet hat:
        # 6 Frames nebeneinander, 1 Reihe, 6 FPS.
        animations = AnimationSet(
            columns=6,
            rows=1,
        )

        animations.add_row(
            "idle",
            row=0,
            frame_count=6,
            fps=6.0,
            loop=True,
        )

        self.add_animations(
            animations,
        )

        # Direkter Start beim Erstellen der Node.
        self.play(
            "idle",
        )

    def is_moving(self) -> bool:
        return any(
            (
                self.input.key_down("A"),
                self.input.key_down("D"),
                self.input.key_down("W"),
                self.input.key_down("S"),
                self.input.key_down("LEFT"),
                self.input.key_down("RIGHT"),
                self.input.key_down("UP"),
                self.input.key_down("DOWN"),
            )
        )

    def update(
        self,
        delta_time: float,
    ) -> None:
        # Führt die Animation weiter.
        super().update(
            delta_time,
        )

        # Nur auf idle schalten, wenn wirklich keine Bewegungstaste
        # gehalten wird und idle nicht bereits läuft.
        if not self.is_moving():
            current = self.current_animation

            if (
                current is None
                or current.name != "idle"
            ):
                self.play(
                    "idle",
                )