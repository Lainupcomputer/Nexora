from __future__ import annotations

from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.font_atlas import GPUFontAtlas
from nexora.rendering.text import TextSystem


FONT_PATH = Path(
    "assets/fonts/DejaVuSans.ttf"
)


def main() -> None:
    context = GPUContext(
        800,
        450,
        title="Nexora - Font Atlas Test",
        debug=True,
        vsync=True,
    )

    text_system = TextSystem()
    font = None
    atlas = None

    running = True

    try:
        # --------------------------------------------------------------
        # Font
        # --------------------------------------------------------------

        font = text_system.font(
            FONT_PATH,
            32,
        )

        print()
        print("========================================")
        print(" Nexora GPU Font Atlas Test")
        print("========================================")
        print()

        print("Font:")
        print(f"  Path:      {font.path}")
        print(f"  Size:      {font.size}")
        print(f"  Height:    {font.height}")
        print(f"  Ascent:    {font.ascent}")
        print(f"  Descent:   {font.descent}")
        print(f"  Line skip: {font.line_skip}")
        print()

        # --------------------------------------------------------------
        # Atlas
        # --------------------------------------------------------------

        print("Creating GPU font atlas...")

        atlas = GPUFontAtlas(
            context.device,
            font,
            width=1024,
            height=1024,
            padding=2,
        )

        print()
        print("Atlas:")
        print(f"  Size:       {atlas.width}x{atlas.height}")
        print(f"  Glyphs:     {atlas.glyph_count}")
        print(
            "  GPU texture:",
            atlas.texture.texture
            if atlas.texture is not None
            else None,
        )
        print()

        # --------------------------------------------------------------
        # Glyph inspection
        # --------------------------------------------------------------

        test_text = "Nexora Engine!"

        print("Glyphs:")
        print()

        for character in test_text:
            codepoint = ord(character)

            font_glyph = font.glyph(
                codepoint
            )

            atlas_glyph = atlas.get_glyph(
                codepoint
            )

            print(
                f"  {character!r} "
                f"U+{codepoint:04X}"
            )

            print(
                f"    bitmap: "
                f"{font_glyph.width}x"
                f"{font_glyph.height}"
            )

            print(
                f"    bearing: "
                f"({font_glyph.bearing_x}, "
                f"{font_glyph.bearing_y})"
            )

            print(
                f"    advance: "
                f"{font_glyph.advance}"
            )

            if atlas_glyph is not None:
                print(
                    f"    atlas: "
                    f"({atlas_glyph.x}, "
                    f"{atlas_glyph.y}) "
                    f"{atlas_glyph.width}x"
                    f"{atlas_glyph.height}"
                )

                print(
                    f"    uv: "
                    f"({atlas_glyph.u:.6f}, "
                    f"{atlas_glyph.v:.6f}) "
                    f"size=("
                    f"{atlas_glyph.u_size:.6f}, "
                    f"{atlas_glyph.v_size:.6f})"
                )

            else:
                print(
                    "    atlas: MISSING"
                )

            print()

        # --------------------------------------------------------------
        # Validation
        # --------------------------------------------------------------

        print("Validation:")

        assert atlas.texture is not None, (
            "Atlas GPU texture was not created."
        )

        for character in test_text:
            codepoint = ord(character)

            assert atlas.has_glyph(
                codepoint
            ), (
                f"Missing glyph in atlas: "
                f"{character!r} "
                f"(U+{codepoint:04X})"
            )

        print("  [OK] GPU texture created")
        print("  [OK] All test glyphs present")
        print("  [OK] Font metrics available")
        print("  [OK] Atlas UV coordinates available")
        print()

        print(
            "Font atlas successfully created."
        )
        print()
        print(
            "Close the window to finish the test."
        )

        # --------------------------------------------------------------
        # Keep window alive
        # --------------------------------------------------------------

        while running:

            for event in context.poll_events():

                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

            # ----------------------------------------------------------
            # We don't render anything yet.
            #
            # This test only verifies:
            #
            # SDL3
            # SDL_ttf
            # Font
            # Glyph rasterization
            # GPUFontAtlas
            # GPUTexture
            # GPU device
            #
            # Rendering the atlas comes with GPUTextRenderer.
            # ----------------------------------------------------------

            # Small frame so the GPU/window stays alive.
            if context.begin_frame():

                render_pass = context.begin_render_pass(
                    (0.05, 0.05, 0.07, 1.0)
                )

                context.end_render_pass(
                    render_pass
                )

                context.end_frame()

    finally:
        # --------------------------------------------------------------
        # Correct destruction order
        # --------------------------------------------------------------

        if atlas is not None:
            atlas.destroy()

        if font is not None:
            font.close()

        text_system.shutdown()

        context.destroy()


if __name__ == "__main__":
    main()