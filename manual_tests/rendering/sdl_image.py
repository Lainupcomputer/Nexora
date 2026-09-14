from pathlib import Path

from nexora.assets.loader import TextureLoader


loader = TextureLoader()

path = Path("assets/demo_sprite.png")

image = loader.load(path)

print("Image loaded successfully")
print(f"Size: {image.width} x {image.height}")
print(f"Bytes per pixel: {image.bytes_per_pixel}")
print(f"Pixel bytes: {image.byte_size}")

expected = (
    image.width
    * image.height
    * image.bytes_per_pixel
)

print(f"Expected bytes: {expected}")
print(f"Valid size: {image.byte_size == expected}")