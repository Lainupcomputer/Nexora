from __future__ import annotations

import os


# ==============================================================
# SDL GPU
# ==============================================================

# Default to Vulkan.
#
# Respect an existing environment variable so applications can
# select another SDL_GPU backend before importing Nexora.
os.environ.setdefault(
    "SDL_GPU_DRIVER",
    "vulkan",
)

from nexora.core.engine import Engine
from nexora.core.game import Game

__all__ = [
    "Engine",
    "Game",
]
