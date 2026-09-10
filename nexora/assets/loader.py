from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

import ctypes
import sdl3


T = TypeVar("T")


@dataclass(slots=True)
class ImageData:
    """
    CPU-side RGBA image data.

    This object contains no SDL or GPU resource and can therefore
    safely be passed between worker threads.
    """

    width: int
    height: int
    pixels: bytes
    bytes_per_pixel: int = 4

    @property
    def byte_size(self) -> int:
        return len(self.pixels)


class AssetLoader(ABC, Generic[T]):
    """
    Base class for loading a specific asset type.
    """

    @abstractmethod
    def load(self, path: Path) -> T:
        raise NotImplementedError


class TextureLoader(AssetLoader[ImageData]):
    """
    Loads image files through SDL3.

    Supported formats depend on the SDL3 image loader available
    through PySDL3.

    The loader returns CPU-side RGBA data instead of an SDL_Surface
    or GPU resource so the result can be processed asynchronously.
    """

    def load(self, path: Path) -> ImageData:
        path = Path(path)

        if not path.is_file():
            raise FileNotFoundError(path)

        suffix = path.suffix.lower()

        if suffix == ".png":
            surface = sdl3.SDL_LoadPNG(
                str(path).encode("utf-8")
            )
        else:
            surface = sdl3.IMG_Load(
                str(path).encode("utf-8")
            )

        if not surface:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"Failed to load image '{path}': {error}"
            )

        try:
            return self._surface_to_rgba(surface)

        finally:
            sdl3.SDL_DestroySurface(surface)

    @staticmethod
    def _surface_to_rgba(surface) -> ImageData:
        """
        Convert an SDL_Surface to tightly packed RGBA8 data.
        """

        width = int(surface.contents.w)
        height = int(surface.contents.h)

        if width <= 0 or height <= 0:
            raise RuntimeError(
                "SDL image has invalid dimensions"
            )

        converted = sdl3.SDL_ConvertSurface(
            surface,
            sdl3.SDL_PIXELFORMAT_RGBA32,
        )

        if not converted:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_ConvertSurface failed: {error}"
            )

        try:
            converted_surface = converted.contents

            pitch = int(converted_surface.pitch)
            pixel_ptr = converted_surface.pixels

            if not pixel_ptr:
                raise RuntimeError(
                    "SDL surface contains no pixel data"
                )

            row_size = width * 4

            # SDL surfaces may have padding at the end of each row.
            # Copy only the actual RGBA pixels into tightly packed
            # storage.
            if pitch == row_size:
                pixels = ctypes.string_at(
                    pixel_ptr,
                    row_size * height,
                )
            else:
                output = bytearray(
                    row_size * height
                )

                for y in range(height):
                    source = ctypes.string_at(
                        pixel_ptr + y * pitch,
                        row_size,
                    )

                    start = y * row_size
                    output[
                        start:start + row_size
                    ] = source

                pixels = bytes(output)

            return ImageData(
                width=width,
                height=height,
                pixels=pixels,
                bytes_per_pixel=4,
            )

        finally:
            sdl3.SDL_DestroySurface(converted)