from nexora.rendering.text import TextSystem
import sdl3
import ctypes


text = TextSystem()

font = text.font(
    "assets/fonts/DejaVuSans.ttf",
    32,
)

print("Font:", font.path)
print("Size:", font.size)
print("Height:", font.height)
print("Ascent:", font.ascent)
print("Descent:", font.descent)
print("Line skip:", font.line_skip)

for character in "Nexora Engine!":
    glyph = font.glyph(ord(character))

    print(
        repr(character),
        "size=", (glyph.width, glyph.height),
        "bearing=", (glyph.bearing_x, glyph.bearing_y),
        "advance=", glyph.advance,
        "pitch=", glyph.pitch,
        "pixels=", len(glyph.pixels),
    )

font.close()
text.shutdown()