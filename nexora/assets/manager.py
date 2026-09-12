from __future__ import annotations

import threading

from pathlib import Path
from typing import (
    Any,
    TypeVar,
)

from nexora.assets.asset import (
    Asset,
    AssetStatus,
)

from nexora.assets.loader import (
    AssetLoader,
    FontLoader,
    ImageData,
    TextureLoader,
)

from nexora.rendering.text import (
    Font,
    TextSystem,
)


T = TypeVar("T")


class AssetManager:
    """
    Central manager for Nexora assets.

    Ordinary assets are cached by normalized absolute path.

    Fonts use a separate cache because font size is part of the
    identity of a loaded font.

    Example:

        fonts/Roboto-Regular.ttf @ 16
        fonts/Roboto-Regular.ttf @ 32

    are separate cached resources.
    """

    def __init__(
        self,
        asset_root: str | Path = "assets",
    ) -> None:
        # ======================================================
        # Root
        # ======================================================

        self.root = Path(
            asset_root
        ).resolve()

        # ======================================================
        # Generic assets
        # ======================================================

        self._assets: dict[
            str,
            Asset,
        ] = {}

        self._loaders: dict[
            str,
            AssetLoader[Any],
        ] = {}

        # ======================================================
        # Text / fonts
        # ======================================================

        self.text_system = (
            TextSystem()
        )

        self.text_system.initialize()

        self._font_loader = (
            FontLoader(
                self.text_system
            )
        )

        self._fonts: dict[
            tuple[str, float],
            Font,
        ] = {}

        # ======================================================
        # Lock
        # ======================================================

        self._lock = (
            threading.RLock()
        )

        # ======================================================
        # Default loaders
        # ======================================================

        texture_loader = (
            TextureLoader()
        )

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

    # ==============================================================
    # Paths
    # ==============================================================

    def resolve(
        self,
        path: str | Path,
    ) -> Path:
        """
        Resolve an asset path relative to the asset root.
        """

        path = Path(
            path
        )

        if not path.is_absolute():
            path = (
                self.root
                / path
            )

        return path.resolve()

    def exists(
        self,
        path: str | Path,
    ) -> bool:
        return (
            self.resolve(
                path
            ).is_file()
        )

    # ==============================================================
    # Loaders
    # ==============================================================

    def register_loader(
        self,
        extension: str,
        loader: AssetLoader[Any],
    ) -> None:
        extension = (
            extension.lower()
        )

        if not extension.startswith(
            "."
        ):
            extension = (
                f".{extension}"
            )

        with self._lock:
            self._loaders[
                extension
            ] = loader

    def unregister_loader(
        self,
        extension: str,
    ) -> None:
        extension = (
            extension.lower()
        )

        if not extension.startswith(
            "."
        ):
            extension = (
                f".{extension}"
            )

        with self._lock:
            self._loaders.pop(
                extension,
                None,
            )

    # ==============================================================
    # Generic loading
    # ==============================================================

    def load(
        self,
        path: str | Path,
        *,
        force_reload: bool = False,
    ) -> Any:
        """
        Load an asset using the registered loader for its extension.
        """

        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            cached = (
                self._assets.get(
                    cache_key
                )
            )

            if (
                cached is not None
                and cached.loaded
                and not force_reload
            ):
                return (
                    cached.value
                )

            loader = (
                self._loaders.get(
                    resolved.suffix.lower()
                )
            )

            if loader is None:
                raise ValueError(
                    "No asset loader registered "
                    "for extension "
                    f"{resolved.suffix!r}."
                )

            if not resolved.is_file():
                raise FileNotFoundError(
                    f"Asset not found: "
                    f"{resolved}"
                )

            asset = Asset(
                path=cache_key,
                status=AssetStatus.LOADING,
            )

            self._assets[
                cache_key
            ] = asset

        try:
            value = (
                loader.load(
                    resolved
                )
            )

        except BaseException as exc:
            with self._lock:
                asset.status = (
                    AssetStatus.FAILED
                )

                asset.error = exc

            raise

        with self._lock:
            asset.value = value
            asset.status = (
                AssetStatus.LOADED
            )

            asset.error = None

        return value

    # ==============================================================
    # Texture loading
    # ==============================================================

    def load_texture(
        self,
        path: str | Path,
        *,
        force_reload: bool = False,
    ) -> ImageData:
        """
        Load an image into CPU-side RGBA image data.
        """

        value = self.load(
            path,
            force_reload=force_reload,
        )

        if not isinstance(
            value,
            ImageData,
        ):
            raise TypeError(
                f"Asset '{path}' is not "
                "an ImageData texture."
            )

        return value

    # ==============================================================
    # Font loading
    # ==============================================================

    @staticmethod
    def _normalize_font_size(
        size: float,
    ) -> float:
        size = float(
            size
        )

        if size <= 0.0:
            raise ValueError(
                "Font size must be greater "
                "than zero."
            )

        return size

    def _font_cache_key(
        self,
        path: str | Path,
        size: float,
    ) -> tuple[str, float]:
        resolved = (
            self.resolve(
                path
            )
        )

        size = (
            self._normalize_font_size(
                size
            )
        )

        return (
            str(
                resolved
            ).lower(),
            size,
        )

    def load_font(
        self,
        path: str | Path,
        size: float,
        *,
        force_reload: bool = False,
    ) -> Font:
        """
        Load and cache a font.

        Font cache identity consists of:

            absolute path + font size
        """

        resolved = (
            self.resolve(
                path
            )
        )

        size = (
            self._normalize_font_size(
                size
            )
        )

        cache_key = (
            str(
                resolved
            ).lower(),
            size,
        )

        with self._lock:
            cached = (
                self._fonts.get(
                    cache_key
                )
            )

            if (
                cached is not None
                and not force_reload
            ):
                return cached

            if not resolved.is_file():
                raise FileNotFoundError(
                    f"Font asset not found: "
                    f"{resolved}"
                )

            # If force reload is requested,
            # close the previous font first.
            if cached is not None:
                cached.close()

                self._fonts.pop(
                    cache_key,
                    None,
                )

            font = (
                self._font_loader.load(
                    resolved,
                    size,
                )
            )

            self._fonts[
                cache_key
            ] = font

            return font

    def get_font(
        self,
        path: str | Path,
        size: float,
    ) -> Font | None:
        """
        Return a cached font without loading it.
        """

        cache_key = (
            self._font_cache_key(
                path,
                size,
            )
        )

        with self._lock:
            return self._fonts.get(
                cache_key
            )

    def is_font_loaded(
        self,
        path: str | Path,
        size: float,
    ) -> bool:
        cache_key = (
            self._font_cache_key(
                path,
                size,
            )
        )

        with self._lock:
            return (
                cache_key
                in self._fonts
            )

    def unload_font(
        self,
        path: str | Path,
        size: float | None = None,
    ) -> int:
        """
        Unload cached font resources.

        If size is supplied, only that font instance is removed.

        If size is None, every cached size for the given font file
        is removed.

        Returns the number of unloaded font objects.
        """

        resolved = (
            self.resolve(
                path
            )
        )

        normalized_path = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            if size is not None:
                normalized_size = (
                    self._normalize_font_size(
                        size
                    )
                )

                key = (
                    normalized_path,
                    normalized_size,
                )

                font = (
                    self._fonts.pop(
                        key,
                        None,
                    )
                )

                if font is None:
                    return 0

                font.close()

                return 1

            keys = [
                key
                for key
                in self._fonts
                if key[0]
                == normalized_path
            ]

            for key in keys:
                font = (
                    self._fonts.pop(
                        key
                    )
                )

                font.close()

            return len(
                keys
            )

    # ==============================================================
    # Generic cache
    # ==============================================================

    def get(
        self,
        path: str | Path,
    ) -> Any | None:
        """
        Return a cached generic asset without loading it.
        """

        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            asset = (
                self._assets.get(
                    cache_key
                )
            )

            if (
                asset is None
                or not asset.loaded
            ):
                return None

            return asset.value

    def is_loaded(
        self,
        path: str | Path,
    ) -> bool:
        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            asset = (
                self._assets.get(
                    cache_key
                )
            )

            return (
                asset is not None
                and asset.loaded
            )

    def is_loading(
        self,
        path: str | Path,
    ) -> bool:
        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            asset = (
                self._assets.get(
                    cache_key
                )
            )

            return (
                asset is not None
                and asset.status
                is AssetStatus.LOADING
            )

    def is_failed(
        self,
        path: str | Path,
    ) -> bool:
        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            asset = (
                self._assets.get(
                    cache_key
                )
            )

            return (
                asset is not None
                and asset.failed
            )

    def unload(
        self,
        path: str | Path,
    ) -> bool:
        """
        Remove one generic asset from the cache.
        """

        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            return (
                self._assets.pop(
                    cache_key,
                    None,
                )
                is not None
            )

    def clear(
        self,
    ) -> None:
        """
        Clear all cached assets.

        Font objects are explicitly closed.
        """

        with self._lock:
            self._assets.clear()

            fonts = list(
                self._fonts.values()
            )

            self._fonts.clear()

        for font in fonts:
            font.close()

    # ==============================================================
    # Information
    # ==============================================================

    def count(
        self,
    ) -> int:
        """
        Return total number of cached generic assets and fonts.
        """

        with self._lock:
            return (
                len(
                    self._assets
                )
                + len(
                    self._fonts
                )
            )

    def asset_count(
        self,
    ) -> int:
        with self._lock:
            return len(
                self._assets
            )

    def font_count(
        self,
    ) -> int:
        with self._lock:
            return len(
                self._fonts
            )

    def paths(
        self,
    ) -> list[str]:
        """
        Return cached generic asset paths.
        """

        with self._lock:
            return [
                asset.path
                for asset
                in self._assets.values()
            ]

    def font_keys(
        self,
    ) -> list[
        tuple[str, float]
    ]:
        with self._lock:
            return list(
                self._fonts.keys()
            )

    def get_asset(
        self,
        path: str | Path,
    ) -> Asset | None:
        resolved = (
            self.resolve(
                path
            )
        )

        cache_key = (
            str(
                resolved
            ).lower()
        )

        with self._lock:
            return self._assets.get(
                cache_key
            )

    # ==============================================================
    # Shutdown
    # ==============================================================

    def shutdown(
        self,
    ) -> None:
        """
        Release all managed asset resources.

        Fonts must be closed before SDL_ttf is shut down.
        """

        self.clear()

        self.text_system.shutdown()