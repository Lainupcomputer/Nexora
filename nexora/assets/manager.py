from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, TypeVar

from nexora.assets.asset import Asset, AssetStatus
from nexora.assets.loader import (
    AssetLoader,
    ImageData,
    TextureLoader,
)

T = TypeVar("T")


class AssetManager:
    """
    Central manager for Nexora assets.

    Assets are cached by their normalized absolute path.

    Texture assets are loaded through SDL3/SDL3_image and returned
    as CPU-side ImageData. GPU resources are created separately on
    the rendering thread.
    """

    def __init__(
        self,
        asset_root: str | Path = "assets",
    ) -> None:
        self.root = Path(asset_root).resolve()

        self._assets: dict[str, Asset] = {}
        self._loaders: dict[str, AssetLoader[Any]] = {}

        self._lock = threading.RLock()

        texture_loader = TextureLoader()

        for extension in (
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".webp",
        ):
            self.register_loader(
                extension,
                texture_loader,
            )

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def resolve(self, path: str | Path) -> Path:
        """
        Resolve an asset path relative to the asset root.
        """

        path = Path(path)

        if not path.is_absolute():
            path = self.root / path

        return path.resolve()

    def exists(self, path: str | Path) -> bool:
        return self.resolve(path).is_file()

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def register_loader(
        self,
        extension: str,
        loader: AssetLoader[Any],
    ) -> None:
        extension = extension.lower()

        if not extension.startswith("."):
            extension = f".{extension}"

        with self._lock:
            self._loaders[extension] = loader

    def unregister_loader(
        self,
        extension: str,
    ) -> None:
        extension = extension.lower()

        if not extension.startswith("."):
            extension = f".{extension}"

        with self._lock:
            self._loaders.pop(extension, None)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(
        self,
        path: str | Path,
        *,
        force_reload: bool = False,
    ) -> Any:
        """
        Load an asset using the registered loader for its extension.
        """

        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            cached = self._assets.get(cache_key)

            if (
                cached is not None
                and cached.loaded
                and not force_reload
            ):
                return cached.value

            loader = self._loaders.get(
                resolved.suffix.lower()
            )

            if loader is None:
                raise ValueError(
                    "No asset loader registered for extension "
                    f"{resolved.suffix!r}."
                )

            if not resolved.is_file():
                raise FileNotFoundError(
                    f"Asset not found: {resolved}"
                )

            asset = Asset(
                path=cache_key,
                status=AssetStatus.LOADING,
            )

            self._assets[cache_key] = asset

        try:
            value = loader.load(resolved)

        except BaseException as exc:
            with self._lock:
                asset.status = AssetStatus.FAILED
                asset.error = exc

            raise

        with self._lock:
            asset.value = value
            asset.status = AssetStatus.LOADED
            asset.error = None

        return value

    def load_texture(
        self,
        path: str | Path,
        *,
        force_reload: bool = False,
    ) -> ImageData:
        """
        Load an image into CPU-side RGBA image data.

        The returned ImageData does not contain a GPU resource.
        GPU upload is handled separately by the renderer.
        """

        value = self.load(
            path,
            force_reload=force_reload,
        )

        if not isinstance(value, ImageData):
            raise TypeError(
                f"Asset '{path}' is not an ImageData texture."
            )

        return value

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def get(
        self,
        path: str | Path,
    ) -> Any | None:
        """
        Return a cached asset without loading it.
        """

        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            asset = self._assets.get(cache_key)

            if asset is None or not asset.loaded:
                return None

            return asset.value

    def is_loaded(
        self,
        path: str | Path,
    ) -> bool:
        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            asset = self._assets.get(cache_key)

            return (
                asset is not None
                and asset.loaded
            )

    def is_loading(
        self,
        path: str | Path,
    ) -> bool:
        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            asset = self._assets.get(cache_key)

            return (
                asset is not None
                and asset.status is AssetStatus.LOADING
            )

    def is_failed(
        self,
        path: str | Path,
    ) -> bool:
        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            asset = self._assets.get(cache_key)

            return (
                asset is not None
                and asset.failed
            )

    def unload(
        self,
        path: str | Path,
    ) -> bool:
        """
        Remove one asset from the cache.
        """

        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            return (
                self._assets.pop(
                    cache_key,
                    None,
                )
                is not None
            )

    def clear(self) -> None:
        """
        Remove all cached assets.
        """

        with self._lock:
            self._assets.clear()

    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._assets)

    def paths(self) -> list[str]:
        with self._lock:
            return [
                asset.path
                for asset in self._assets.values()
            ]

    def get_asset(
        self,
        path: str | Path,
    ) -> Asset | None:
        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            return self._assets.get(cache_key)