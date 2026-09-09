from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pygame

from nexora.assets import AssetManager


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("NEXORA TEXTURE LOADER TEST")
    print("=" * 60)
    print(f"Python: {sys.version.split()[0]}")

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"GIL: {gil_enabled}")

    pygame.init()

    try:
        pygame.display.set_mode((320, 240))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            texture_path = root / "test_texture.png"

            # Create a test texture without requiring an external asset.
            surface = pygame.Surface((64, 64), pygame.SRCALPHA)
            surface.fill((255, 80, 80, 255))

            pygame.draw.circle(
                surface,
                (255, 255, 255, 255),
                (32, 32),
                20,
            )

            pygame.image.save(surface, texture_path)

            print("\n1. CREATE TEST TEXTURE")

            check(texture_path.exists(), "Test texture was not created.")

            print("✅ PNG texture created")
            print(f"   Size: {surface.get_size()}")

            # ------------------------------------------------------
            # Asset Manager
            # ------------------------------------------------------

            manager = AssetManager(root)

            print("\n2. LOAD TEXTURE")

            texture = manager.load_texture("test_texture.png")

            check(
                isinstance(texture, pygame.Surface),
                "Loaded texture is not a pygame.Surface.",
            )

            check(
                texture.get_size() == (64, 64),
                "Texture has incorrect dimensions.",
            )

            print("✅ Texture loaded")
            print(f"   Surface: {texture}")
            print(f"   Size: {texture.get_size()}")

            # ------------------------------------------------------
            # Cache
            # ------------------------------------------------------

            print("\n3. TEXTURE CACHE")

            cached_texture = manager.load_texture(
                "test_texture.png"
            )

            check(
                cached_texture is texture,
                "Texture cache did not return the same object.",
            )

            check(
                manager.count() == 1,
                "Expected exactly one cached asset.",
            )

            print("✅ Texture cache works")

            # ------------------------------------------------------
            # Get
            # ------------------------------------------------------

            print("\n4. GET CACHED TEXTURE")

            retrieved = manager.get("test_texture.png")

            check(
                retrieved is texture,
                "get() returned the wrong texture.",
            )

            print("✅ Cached texture retrieved")

            # ------------------------------------------------------
            # Unload
            # ------------------------------------------------------

            print("\n5. UNLOAD")

            check(
                manager.unload("test_texture.png"),
                "Texture could not be unloaded.",
            )

            check(
                manager.get("test_texture.png") is None,
                "Texture is still cached.",
            )

            print("✅ Texture unloaded")

    finally:
        pygame.quit()

    print("\n" + "=" * 60)
    print("TEXTURE LOADER TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()