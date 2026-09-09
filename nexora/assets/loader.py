from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class AssetLoader(ABC, Generic[T]):
    """
    Base class for loading a specific asset type.
    """

    @abstractmethod
    def load(self, path: Path) -> T:
        raise NotImplementedError


class TextureLoader(AssetLoader):
    """
    Loads image files into pygame Surfaces.

    Texture loading is intentionally kept in its own loader so that
    asynchronous loading and additional asset types can be added later.
    """

    def load(self, path: Path):
        import pygame

        return pygame.image.load(str(path)).convert_alpha()