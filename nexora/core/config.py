from dataclasses import dataclass


@dataclass(slots=True)
class GameConfig:
    title: str = "Nexora Game"
    width: int = 1280
    height: int = 720

    target_fps: int = 60
    vsync: bool = False

    resizable: bool = True
    fullscreen: bool = False

    max_delta_time: float = 0.1