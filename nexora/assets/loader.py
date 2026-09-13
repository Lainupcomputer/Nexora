from __future__ import annotations

import ctypes

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

import sdl3

from nexora.rendering.text import (
    Font,
    TextSystem,
)


T = TypeVar("T")


# ==============================================================
# Image data
# ==============================================================


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
    def byte_size(
        self,
    ) -> int:
        return len(
            self.pixels
        )


# ==============================================================
# Base loader
# ==============================================================


class AssetLoader(
    ABC,
    Generic[T],
):
    """
    Base class for loading a specific asset type.
    """

    @abstractmethod
    def load(
        self,
        path: Path,
    ) -> T:
        raise NotImplementedError


# ==============================================================
# Texture loader
# ==============================================================


class TextureLoader(
    AssetLoader[ImageData],
):
    """
    Loads image files through SDL3.

    The loader returns CPU-side RGBA data instead of an SDL_Surface
    or GPU resource so the result can later be uploaded by the
    rendering system.
    """

    def load(
        self,
        path: Path,
    ) -> ImageData:
        path = Path(
            path
        )

        if not path.is_file():
            raise FileNotFoundError(
                path
            )

        suffix = (
            path.suffix.lower()
        )

        if suffix == ".png":
            surface = sdl3.SDL_LoadPNG(
                str(path).encode(
                    "utf-8"
                )
            )

        else:
            surface = sdl3.IMG_Load(
                str(path).encode(
                    "utf-8"
                )
            )

        if not surface:
            error = (
                sdl3.SDL_GetError()
            )

            if isinstance(
                error,
                bytes,
            ):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"Failed to load image "
                f"'{path}': {error}"
            )

        try:
            return (
                self._surface_to_rgba(
                    surface
                )
            )

        finally:
            sdl3.SDL_DestroySurface(
                surface
            )

    @staticmethod
    def _surface_to_rgba(
        surface,
    ) -> ImageData:
        """
        Convert an SDL_Surface to tightly packed RGBA8 data.
        """

        width = int(
            surface.contents.w
        )

        height = int(
            surface.contents.h
        )

        if (
            width <= 0
            or height <= 0
        ):
            raise RuntimeError(
                "SDL image has invalid dimensions"
            )

        converted = (
            sdl3.SDL_ConvertSurface(
                surface,
                sdl3.SDL_PIXELFORMAT_RGBA32,
            )
        )

        if not converted:
            error = (
                sdl3.SDL_GetError()
            )

            if isinstance(
                error,
                bytes,
            ):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                "SDL_ConvertSurface failed: "
                f"{error}"
            )

        try:
            converted_surface = (
                converted.contents
            )

            pitch = int(
                converted_surface.pitch
            )

            pixel_ptr = (
                converted_surface.pixels
            )

            if not pixel_ptr:
                raise RuntimeError(
                    "SDL surface contains "
                    "no pixel data"
                )

            row_size = (
                width * 4
            )

            if pitch == row_size:
                pixels = (
                    ctypes.string_at(
                        pixel_ptr,
                        row_size * height,
                    )
                )

            else:
                output = bytearray(
                    row_size * height
                )

                for y in range(
                    height
                ):
                    source = (
                        ctypes.string_at(
                            pixel_ptr
                            + y * pitch,
                            row_size,
                        )
                    )

                    start = (
                        y * row_size
                    )

                    output[
                        start:
                        start + row_size
                    ] = source

                pixels = bytes(
                    output
                )

            return ImageData(
                width=width,
                height=height,
                pixels=pixels,
                bytes_per_pixel=4,
            )

        finally:
            sdl3.SDL_DestroySurface(
                converted
            )


# ==============================================================
# Font loader
# ==============================================================


class FontLoader:
    """
    Loads font assets through Nexora's TextSystem.

    Font loading differs from ordinary asset loading because the
    font size is part of the asset identity.

    For example:

        Roboto-Regular.ttf @ 16
        Roboto-Regular.ttf @ 32

    are two separate font assets.
    """

    def __init__(
        self,
        text_system: TextSystem,
    ) -> None:
        self.text_system = (
            text_system
        )

    def load(
        self,
        path: Path,
        size: float,
    ) -> Font:
        path = Path(
            path
        )

        if not path.is_file():
            raise FileNotFoundError(
                path
            )

        size = float(
            size
        )

        if size <= 0.0:
            raise ValueError(
                "Font size must be greater "
                "than zero."
            )

        return self.text_system.font(
            path,
            size,
        )