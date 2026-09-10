from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path

import sdl3

from nexora.rendering.gpu.texture import GPUTexture


@dataclass(slots=True, frozen=True)
class Glyph:
    """Cached information about one rendered glyph."""

    codepoint: int

    width: int
    height: int

    bearing_x: int
    bearing_y: int

    advance: int

    pixels: bytes
    pitch: int


class Font:
    """SDL3_ttf font used by Nexora's GPU text renderer."""

    __slots__ = (
        "_font",
        "_path",
        "_size",
        "_closed",
        "_glyphs",
    )

    def __init__(
        self,
        path: str | Path,
        size: float,
    ) -> None:
        if size <= 0:
            raise ValueError("Font size must be greater than zero.")

        self._path = Path(path)
        self._size = float(size)
        self._closed = False
        self._glyphs: dict[int, Glyph] = {}

        if not self._path.is_file():
            raise FileNotFoundError(
                f"Font file does not exist: {self._path}"
            )

        if not sdl3.TTF_WasInit():
            if not sdl3.TTF_Init():
                raise RuntimeError(
                    f"TTF_Init failed: {self._error()}"
                )

        font = sdl3.TTF_OpenFont(
            str(self._path).encode("utf-8"),
            float(size),
        )

        if not font:
            raise RuntimeError(
                f"TTF_OpenFont failed for '{self._path}': {self._error()}"
            )

        self._font = font

    @staticmethod
    def _error() -> str:
        error = sdl3.SDL_GetError()

        if isinstance(error, bytes):
            return error.decode("utf-8", errors="replace")

        if error is None:
            return "<unknown SDL error>"

        return str(error)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def size(self) -> float:
        return self._size

    @property
    def height(self) -> int:
        self._ensure_open()
        return int(sdl3.TTF_GetFontHeight(self._font))

    @property
    def ascent(self) -> int:
        self._ensure_open()
        return int(sdl3.TTF_GetFontAscent(self._font))

    @property
    def descent(self) -> int:
        self._ensure_open()
        return int(sdl3.TTF_GetFontDescent(self._font))

    @property
    def line_skip(self) -> int:
        self._ensure_open()
        return int(sdl3.TTF_GetFontLineSkip(self._font))

    def has_glyph(self, codepoint: int) -> bool:
        self._ensure_open()

        return bool(
            sdl3.TTF_FontHasGlyph(
                self._font,
                int(codepoint),
            )
        )

    def glyph(self, codepoint: int) -> Glyph:
        """Return a cached glyph, rasterizing it on first access."""

        self._ensure_open()

        codepoint = int(codepoint)

        cached = self._glyphs.get(codepoint)

        if cached is not None:
            return cached

        glyph = self._load_glyph(codepoint)
        self._glyphs[codepoint] = glyph

        return glyph

    def _load_glyph(self, codepoint: int) -> Glyph:
        image_type = sdl3.TTF_ImageType()
        surface = sdl3.TTF_GetGlyphImage(
            self._font,
            codepoint,
            ctypes.byref(image_type),
        )

        if not surface:
            # Spaces and some other glyphs may legitimately have
            # no bitmap. Metrics still provide their advance.
            return self._load_empty_glyph(codepoint)

        try:
            width = int(surface.contents.w)
            height = int(surface.contents.h)
            pitch = int(surface.contents.pitch)

            if width <= 0 or height <= 0:
                return self._load_empty_glyph(codepoint)

            pixels_size = pitch * height

            pixels = ctypes.string_at(
                surface.contents.pixels,
                pixels_size,
            )

            metrics = self._metrics(codepoint)

            return Glyph(
                codepoint=codepoint,
                width=width,
                height=height,
                bearing_x=metrics[0],
                bearing_y=metrics[1],
                advance=metrics[4],
                pixels=pixels,
                pitch=pitch,
            )

        finally:
            sdl3.SDL_DestroySurface(surface)

    def _load_empty_glyph(self, codepoint: int) -> Glyph:
        metrics = self._metrics(codepoint)

        return Glyph(
            codepoint=codepoint,
            width=0,
            height=0,
            bearing_x=metrics[0],
            bearing_y=metrics[1],
            advance=metrics[4],
            pixels=b"",
            pitch=0,
        )

    def _metrics(self, codepoint: int) -> tuple[int, int, int, int, int]:
        min_x = ctypes.c_int()
        max_x = ctypes.c_int()
        min_y = ctypes.c_int()
        max_y = ctypes.c_int()
        advance = ctypes.c_int()

        success = sdl3.TTF_GetGlyphMetrics(
            self._font,
            codepoint,
            ctypes.byref(min_x),
            ctypes.byref(max_x),
            ctypes.byref(min_y),
            ctypes.byref(max_y),
            ctypes.byref(advance),
        )

        if not success:
            raise RuntimeError(
                f"TTF_GetGlyphMetrics failed for U+{codepoint:04X}: "
                f"{self._error()}"
            )

        return (
            min_x.value,
            max_x.value,
            min_y.value,
            max_y.value,
            advance.value,
        )

    def clear_cache(self) -> None:
        self._glyphs.clear()

    def close(self) -> None:
        if self._closed:
            return

        if self._font:
            sdl3.TTF_CloseFont(self._font)

        self._font = None
        self._glyphs.clear()
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Font has already been closed.")

    def __enter__(self) -> Font:
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()


class TextSystem:
    """Global SDL_ttf lifetime and font factory."""

    __slots__ = ("_initialized",)

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        if not sdl3.TTF_WasInit():
            if not sdl3.TTF_Init():
                raise RuntimeError(
                    f"TTF_Init failed: {Font._error()}"
                )

        self._initialized = True

    def font(
        self,
        path: str | Path,
        size: float,
    ) -> Font:
        self.initialize()
        return Font(path, size)

    def shutdown(self) -> None:
        if not self._initialized:
            return

        if sdl3.TTF_WasInit():
            sdl3.TTF_Quit()

        self._initialized = False