from __future__ import annotations


class AudioListener:
    """Represents the listener position in the audio world."""

    def __init__(
        self,
        position: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self._position = (0.0, 0.0)

        self.position = position

    @property
    def position(self) -> tuple[float, float]:
        return self._position

    @position.setter
    def position(
        self,
        value: tuple[float, float],
    ) -> None:
        if len(value) != 2:
            raise ValueError(
                "Audio listener position must contain exactly two values."
            )

        self._position = (
            float(value[0]),
            float(value[1]),
        )

    @property
    def x(self) -> float:
        return self._position[0]

    @property
    def y(self) -> float:
        return self._position[1]

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        self.position = (x, y)