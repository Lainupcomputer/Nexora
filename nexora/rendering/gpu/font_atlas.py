from __future__ import annotations

from dataclasses import dataclass

import sdl3

from nexora.rendering.text import Font
from nexora.rendering.gpu.texture import GPUTexture


@dataclass(slots=True, frozen=True)
class AtlasGlyph:
    """GPU atlas information for one glyph."""

    codepoint: int

    # Position in atlas pixels
    x: int
    y: int

    # Size in atlas pixels
    width: int
    height: int

    # Normalized UV coordinates
    u: float
    v: float
    u_size: float
    v_size: float


class GPUFontAtlas:
    """
    GPU-resident font atlas.

    SDL_ttf rasterizes glyphs on the CPU. The resulting glyph images
    are packed into one GPU texture.

    The CPU-side Font remains responsible for glyph metrics such as:

        bearing_x
        bearing_y
        advance

    The atlas only stores the bitmap and its UV coordinates.
    """

    __slots__ = (
        "device",
        "font",
        "width",
        "height",
        "padding",
        "texture",
        "_glyphs",
    )

    def __init__(
        self,
        device,
        font: Font,
        *,
        width: int = 1024,
        height: int = 1024,
        padding: int = 2,
        charset: str | None = None,
    ) -> None:
        self.device = device
        self.font = font

        self.width = int(width)
        self.height = int(height)
        self.padding = int(padding)

        if self.width <= 0:
            raise ValueError("Atlas width must be greater than zero.")

        if self.height <= 0:
            raise ValueError("Atlas height must be greater than zero.")

        if self.padding < 0:
            raise ValueError("Atlas padding cannot be negative.")

        self.texture: GPUTexture | None = None
        self._glyphs: dict[int, AtlasGlyph] = {}

        if charset is None:
            charset = self._default_charset()

        self._build(charset)

    # ------------------------------------------------------------------
    # Default charset
    # ------------------------------------------------------------------

    @staticmethod
    def _default_charset() -> str:
        """
        Default character set for the first atlas implementation.

        Includes:
        - ASCII 32-126
        - German umlauts
        - common accented characters
        - Euro symbol
        """

        return (
            "".join(
                chr(codepoint)
                for codepoint in range(32, 127)
            )
            + "äöüÄÖÜß"
            + "éèêëÉÈÊË"
            + "áàâãåÁÀÂÃÅ"
            + "íìîïÍÌÎÏ"
            + "óòôõøÓÒÔÕØ"
            + "úùûÚÙÛ"
            + "çÇñÑ"
            + "€"
        )

    # ------------------------------------------------------------------
    # Atlas construction
    # ------------------------------------------------------------------

    def _build(self, charset: str) -> None:
        """
        Rasterize and pack all requested glyphs into the atlas.
        """

        glyphs = []
        seen: set[int] = set()

        # --------------------------------------------------------------
        # Load glyphs from SDL_ttf
        # --------------------------------------------------------------

        for character in charset:
            codepoint = ord(character)

            if codepoint in seen:
                continue

            seen.add(codepoint)

            if not self.font.has_glyph(codepoint):
                continue

            glyph = self.font.glyph(codepoint)

            # Some glyphs can have no visible bitmap.
            #
            # Their advance is still available through Font.glyph(),
            # so the text renderer can handle them later.
            if glyph.width <= 0 or glyph.height <= 0:
                continue

            glyphs.append(glyph)

        # --------------------------------------------------------------
        # Create empty RGBA atlas
        # --------------------------------------------------------------

        atlas_pixels = bytearray(
            self.width
            * self.height
            * 4
        )

        # --------------------------------------------------------------
        # Simple row-based packing
        # --------------------------------------------------------------

        cursor_x = self.padding
        cursor_y = self.padding
        row_height = 0

        for glyph in glyphs:

            # Start a new row if the glyph does not fit horizontally.
            if (
                cursor_x
                + glyph.width
                + self.padding
                > self.width
            ):
                cursor_x = self.padding
                cursor_y += row_height + self.padding
                row_height = 0

            # Check vertical space.
            if (
                cursor_y
                + glyph.height
                + self.padding
                > self.height
            ):
                raise RuntimeError(
                    "GPU font atlas is full. "
                    f"Atlas size: "
                    f"{self.width}x{self.height}. "
                    f"Glyph "
                    f"U+{glyph.codepoint:04X} "
                    f"({glyph.width}x{glyph.height}) "
                    "could not be placed."
                )

            # ----------------------------------------------------------
            # Copy glyph pixels into atlas
            # ----------------------------------------------------------

            self._copy_glyph(
                destination=atlas_pixels,
                source=glyph.pixels,
                source_pitch=glyph.pitch,
                width=glyph.width,
                height=glyph.height,
                destination_x=cursor_x,
                destination_y=cursor_y,
            )

            # ----------------------------------------------------------
            # Calculate normalized UV coordinates
            # ----------------------------------------------------------

            atlas_glyph = AtlasGlyph(
                codepoint=glyph.codepoint,

                x=cursor_x,
                y=cursor_y,

                width=glyph.width,
                height=glyph.height,

                u=cursor_x / self.width,
                v=cursor_y / self.height,

                u_size=glyph.width / self.width,
                v_size=glyph.height / self.height,
            )

            self._glyphs[glyph.codepoint] = atlas_glyph

            # Move cursor for next glyph.
            cursor_x += glyph.width + self.padding

            row_height = max(
                row_height,
                glyph.height,
            )

        # --------------------------------------------------------------
        # Upload complete atlas to GPU
        # --------------------------------------------------------------

        self.texture = GPUTexture(
            self.device,
            self.width,
            self.height,
            format=sdl3.SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
            data=atlas_pixels,
            bytes_per_pixel=4,
        )

    # ------------------------------------------------------------------
    # Pixel copy
    # ------------------------------------------------------------------

    def _copy_glyph(
        self,
        *,
        destination: bytearray,
        source: bytes,
        source_pitch: int,
        width: int,
        height: int,
        destination_x: int,
        destination_y: int,
    ) -> None:
        """
        Copy one SDL_ttf glyph surface into the atlas.

        SDL surfaces can have a pitch larger than width * 4,
        therefore every row is copied separately.
        """

        row_size = width * 4

        if source_pitch < row_size:
            raise RuntimeError(
                "Glyph surface pitch is smaller than "
                "width * 4: "
                f"pitch={source_pitch}, "
                f"width={width}"
            )

        atlas_pitch = self.width * 4

        for row in range(height):

            source_offset = (
                row * source_pitch
            )

            destination_offset = (
                (destination_y + row)
                * atlas_pitch
                + destination_x * 4
            )

            destination[
                destination_offset:
                destination_offset + row_size
            ] = source[
                source_offset:
                source_offset + row_size
            ]

    # ------------------------------------------------------------------
    # Glyph lookup
    # ------------------------------------------------------------------

    def get_glyph(
        self,
        codepoint: int,
    ) -> AtlasGlyph | None:
        """
        Return atlas information for a codepoint.

        Returns None if the glyph is not contained in the atlas.
        """

        return self._glyphs.get(
            int(codepoint)
        )

    def has_glyph(
        self,
        codepoint: int,
    ) -> bool:
        """
        Check whether a glyph exists in the atlas.
        """

        return int(codepoint) in self._glyphs

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def glyph_count(self) -> int:
        """Number of glyph bitmaps stored in the atlas."""

        return len(self._glyphs)

    # ------------------------------------------------------------------
    # Lifetime
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """
        Release the GPU atlas texture.
        """

        if self.texture is not None:
            self.texture.destroy()
            self.texture = None

        self._glyphs.clear()

    def __enter__(self) -> GPUFontAtlas:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.destroy()