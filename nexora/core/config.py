from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EngineConfig:
    """
    Nexora engine configuration.
    """

    # ======================================================
    # Window
    # ======================================================

    title: str = "Nexora"

    width: int = 1280
    height: int = 720

    target_fps: int = 60

    resizable: bool = False
    vsync: bool = True

    # ======================================================
    # Save system
    # ======================================================

    save_path: str | Path = "saves"

    save_signing_key: bytes | str = (
        b"nexora-default-save-signing-key-"
        b"change-this-in-production"
    )

    save_version: int = 1

    save_max_file_size: int = (
        64
        * 1024
        * 1024
    )