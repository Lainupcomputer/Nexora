from __future__ import annotations

from pathlib import Path

import pytest

from nexora.assets.loader import ImageData, TextureLoader
from nexora.assets.manager import AssetManager


ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
DEMO_TEXTURE = ASSET_DIR / "demo_sprite.png"


@pytest.fixture
def demo_texture() -> Path:
    if not DEMO_TEXTURE.is_file():
        pytest.skip("assets/demo_sprite.png is not available")

    return DEMO_TEXTURE


def test_texture_loader(demo_texture: Path):
    loader = TextureLoader()

    image = loader.load(demo_texture)

    assert isinstance(image, ImageData)
    assert image.width > 0
    assert image.height > 0
    assert image.bytes_per_pixel == 4

    expected_size = (
        image.width
        * image.height
        * image.bytes_per_pixel
    )

    assert len(image.pixels) == expected_size
    assert image.byte_size == expected_size


def test_asset_manager_load_texture(demo_texture: Path):
    manager = AssetManager(ASSET_DIR)

    image = manager.load_texture("demo_sprite.png")

    assert isinstance(image, ImageData)
    assert image.width > 0
    assert image.height > 0
    assert image.bytes_per_pixel == 4

    expected_size = (
        image.width
        * image.height
        * 4
    )

    assert len(image.pixels) == expected_size


def test_asset_manager_cache(demo_texture: Path):
    manager = AssetManager(ASSET_DIR)

    first = manager.load_texture("demo_sprite.png")
    second = manager.load_texture("demo_sprite.png")

    # Same cached ImageData object.
    assert first is second

    assert manager.is_loaded("demo_sprite.png")
    assert manager.get("demo_sprite.png") is first
    assert manager.get_asset("demo_sprite.png") is not None
    assert manager.count() == 1


def test_asset_manager_unload(demo_texture: Path):
    manager = AssetManager(ASSET_DIR)

    manager.load_texture("demo_sprite.png")

    assert manager.is_loaded("demo_sprite.png")
    assert manager.count() == 1

    assert manager.unload("demo_sprite.png")

    assert not manager.is_loaded("demo_sprite.png")
    assert manager.get("demo_sprite.png") is None
    assert manager.count() == 0


def test_asset_manager_clear(demo_texture: Path):
    manager = AssetManager(ASSET_DIR)

    manager.load_texture("demo_sprite.png")

    assert manager.count() == 1

    manager.clear()

    assert manager.count() == 0
    assert manager.get("demo_sprite.png") is None