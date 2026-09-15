from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Iterable, TypeVar

from nexora.assets.asset import Asset, AssetStatus
from nexora.assets.loader import AssetLoader, FontLoader, ImageData, TextureLoader
from nexora.assets.preload import (
    AssetCategory,
    AssetLoadCallbacks,
    AssetLoadProgress,
    FontAssetRequest,
    normalize_font_requests,
)
from nexora.audio.cache import AudioCache
from nexora.audio.sound import Sound
from nexora.rendering.gpu.texture import GPUTexture
from nexora.rendering.text import Font, TextSystem


T = TypeVar("T")


class AssetManager:
    """
    Central Nexora asset manager.

    CPU image data, GPU textures, fonts and decoded sounds are cached separately.
    The manager can also expose its ordered asset pipeline as SceneLoadTask stages:

        Font -> Audio -> Texture

    Existing load_texture()/load_font() APIs remain available for compatibility.
    """

    def __init__(self, asset_root: str | Path = "assets") -> None:
        self.root = Path(asset_root).resolve()

        self._assets: dict[str, Asset] = {}
        self._loaders: dict[str, AssetLoader[Any]] = {}

        self.text_system = TextSystem()
        self.text_system.initialize()
        self._font_loader = FontLoader(self.text_system)
        self._fonts: dict[tuple[str, float], Font] = {}

        self._gpu_device = None
        self._textures: dict[str, GPUTexture] = {}

        self._audio_cache: AudioCache | None = None
        self._managed_sound_paths: set[Path] = set()

        self._lock = threading.RLock()

        texture_loader = TextureLoader()
        for extension in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
            self.register_loader(extension, texture_loader)

    # ============================================================== 
    # Service binding
    # ============================================================== 

    def bind_gpu(self, gpu_context_or_device) -> None:
        """Bind the GPU service used by texture()."""
        device = getattr(gpu_context_or_device, "device", gpu_context_or_device)
        if device is None:
            raise ValueError("GPU device cannot be None.")
        self._gpu_device = device

    def bind_audio_cache(self, audio_cache: AudioCache) -> None:
        """Bind AudioSystem.cache so sound() shares the engine audio cache."""
        if not isinstance(audio_cache, AudioCache):
            raise TypeError("audio_cache must be an AudioCache.")
        self._audio_cache = audio_cache

    # ============================================================== 
    # Paths / loaders
    # ============================================================== 

    def resolve(self, path: str | Path) -> Path:
        path = Path(path)
        if not path.is_absolute():
            path = self.root / path
        return path.resolve()

    def _cache_key(self, path: str | Path) -> str:
        return str(self.resolve(path)).lower()

    def exists(self, path: str | Path) -> bool:
        return self.resolve(path).is_file()

    def register_loader(self, extension: str, loader: AssetLoader[Any]) -> None:
        extension = extension.lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        with self._lock:
            self._loaders[extension] = loader

    def unregister_loader(self, extension: str) -> None:
        extension = extension.lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        with self._lock:
            self._loaders.pop(extension, None)

    # ============================================================== 
    # Generic CPU assets / images
    # ============================================================== 

    def load(self, path: str | Path, *, force_reload: bool = False) -> Any:
        resolved = self.resolve(path)
        cache_key = str(resolved).lower()

        with self._lock:
            cached = self._assets.get(cache_key)
            if cached is not None and cached.loaded and not force_reload:
                return cached.value

            loader = self._loaders.get(resolved.suffix.lower())
            if loader is None:
                raise ValueError(
                    f"No asset loader registered for extension {resolved.suffix!r}."
                )
            if not resolved.is_file():
                raise FileNotFoundError(f"Asset not found: {resolved}")

            asset = Asset(path=cache_key, status=AssetStatus.LOADING)
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

    def load_texture(self, path: str | Path, *, force_reload: bool = False) -> ImageData:
        """Compatibility API: load CPU-side RGBA image data."""
        value = self.load(path, force_reload=force_reload)
        if not isinstance(value, ImageData):
            raise TypeError(f"Asset '{path}' is not an ImageData texture.")
        return value

    def image(self, path: str | Path, *, force_reload: bool = False) -> ImageData:
        return self.load_texture(path, force_reload=force_reload)

    # ============================================================== 
    # GPU textures
    # ============================================================== 

    def texture(self, path: str | Path, *, force_reload: bool = False) -> GPUTexture:
        if self._gpu_device is None:
            raise RuntimeError(
                "AssetManager has no GPU device. Call bind_gpu() before texture()."
            )

        key = self._cache_key(path)
        with self._lock:
            cached = self._textures.get(key)
            if cached is not None and not force_reload:
                return cached

        image = self.image(path, force_reload=force_reload)
        replacement = GPUTexture(
            self._gpu_device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        with self._lock:
            old = self._textures.get(key)
            self._textures[key] = replacement

        if old is not None and old is not replacement:
            old.destroy()
        return replacement

    def get_texture(self, path: str | Path) -> GPUTexture | None:
        with self._lock:
            return self._textures.get(self._cache_key(path))

    def is_texture_loaded(self, path: str | Path) -> bool:
        return self.get_texture(path) is not None

    def unload_texture(self, path: str | Path, *, unload_image: bool = False) -> bool:
        key = self._cache_key(path)
        with self._lock:
            texture = self._textures.pop(key, None)
        if texture is not None:
            texture.destroy()
        if unload_image:
            with self._lock:
                self._assets.pop(key, None)
        return texture is not None

    # ============================================================== 
    # Fonts
    # ============================================================== 

    @staticmethod
    def _normalize_font_size(size: float) -> float:
        size = float(size)
        if size <= 0.0:
            raise ValueError("Font size must be greater than zero.")
        return size

    def _font_cache_key(self, path: str | Path, size: float) -> tuple[str, float]:
        return (self._cache_key(path), self._normalize_font_size(size))

    def load_font(
        self,
        path: str | Path,
        size: float,
        *,
        force_reload: bool = False,
    ) -> Font:
        resolved = self.resolve(path)
        size = self._normalize_font_size(size)
        cache_key = (str(resolved).lower(), size)

        with self._lock:
            cached = self._fonts.get(cache_key)
            if cached is not None and not force_reload:
                return cached
            if not resolved.is_file():
                raise FileNotFoundError(f"Font asset not found: {resolved}")
            if cached is not None:
                cached.close()
                self._fonts.pop(cache_key, None)

            font = self._font_loader.load(resolved, size)
            self._fonts[cache_key] = font
            return font

    def font(
        self,
        path: str | Path,
        size: float,
        *,
        force_reload: bool = False,
    ) -> Font:
        return self.load_font(path, size, force_reload=force_reload)

    def get_font(self, path: str | Path, size: float) -> Font | None:
        with self._lock:
            return self._fonts.get(self._font_cache_key(path, size))

    def is_font_loaded(self, path: str | Path, size: float) -> bool:
        return self.get_font(path, size) is not None

    def unload_font(self, path: str | Path, size: float | None = None) -> int:
        normalized_path = self._cache_key(path)
        with self._lock:
            if size is not None:
                key = (normalized_path, self._normalize_font_size(size))
                font = self._fonts.pop(key, None)
                if font is None:
                    return 0
                fonts = [font]
            else:
                keys = [key for key in self._fonts if key[0] == normalized_path]
                fonts = [self._fonts.pop(key) for key in keys]

        for font in fonts:
            font.close()
        return len(fonts)

    # ============================================================== 
    # Audio assets
    # ============================================================== 

    def sound(self, path: str | Path, *, force_reload: bool = False) -> Sound:
        if self._audio_cache is None:
            raise RuntimeError(
                "AssetManager has no audio cache. Call bind_audio_cache() before sound()."
            )

        resolved = self.resolve(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"Audio asset not found: {resolved}")

        if force_reload:
            self._audio_cache.remove(resolved)

        sound = self._audio_cache.load(resolved)
        self._managed_sound_paths.add(resolved)
        return sound

    def get_sound(self, path: str | Path) -> Sound | None:
        if self._audio_cache is None:
            return None
        return self._audio_cache.get(self.resolve(path))

    def is_sound_loaded(self, path: str | Path) -> bool:
        return self.get_sound(path) is not None

    def unload_sound(self, path: str | Path) -> bool:
        if self._audio_cache is None:
            return False
        resolved = self.resolve(path)
        existed = self._audio_cache.contains(resolved)
        self._audio_cache.remove(resolved)
        self._managed_sound_paths.discard(resolved)
        return existed

    # ============================================================== 
    # Ordered preload pipeline
    # ============================================================== 

    @staticmethod
    def _emit(callback, value=None) -> None:
        if callback is None:
            return
        if value is None:
            callback()
        else:
            callback(value)

    def _progress(
        self,
        category: AssetCategory,
        current: int,
        total: int,
        asset_path: str | Path | None = None,
    ) -> AssetLoadProgress:
        normalized = 1.0 if total == 0 else current / total
        return AssetLoadProgress(
            category=category,
            current=current,
            total=total,
            progress=max(0.0, min(1.0, normalized)),
            asset_path=None if asset_path is None else str(asset_path),
        )

    def preload(
        self,
        *,
        fonts: Iterable[FontAssetRequest | tuple[str | Path, float]] = (),
        sounds: Iterable[str | Path] = (),
        textures: Iterable[str | Path] = (),
        callbacks: AssetLoadCallbacks | None = None,
        force_reload: bool = False,
    ) -> None:
        """Synchronously preload assets in Font -> Audio -> Texture order."""
        callbacks = callbacks or AssetLoadCallbacks()
        font_items = normalize_font_requests(fonts)
        sound_items = list(sounds)
        texture_items = list(textures)

        stages = (
            (AssetCategory.FONT, font_items),
            (AssetCategory.AUDIO, sound_items),
            (AssetCategory.TEXTURE, texture_items),
        )

        try:
            for category, items in stages:
                if not items:
                    continue
                self._emit(
                    callbacks.on_stage_started,
                    self._progress(category, 0, len(items)),
                )
                self._emit(
                    callbacks.on_progress,
                    self._progress(category, 0, len(items)),
                )

                for index, item in enumerate(items, start=1):
                    if category is AssetCategory.FONT:
                        self.font(item.path, item.size, force_reload=force_reload)
                        path = item.path
                    elif category is AssetCategory.AUDIO:
                        self.sound(item, force_reload=force_reload)
                        path = item
                    else:
                        self.texture(item, force_reload=force_reload)
                        path = item

                    progress = self._progress(category, index, len(items), path)
                    self._emit(callbacks.on_asset_loaded, progress)
                    self._emit(callbacks.on_progress, progress)

        except BaseException as exc:
            self._emit(callbacks.on_failed, exc)
            raise

        self._emit(callbacks.on_completed)

    def add_loading_stages(
        self,
        task,
        *,
        fonts: Iterable[FontAssetRequest | tuple[str | Path, float]] = (),
        sounds: Iterable[str | Path] = (),
        textures: Iterable[str | Path] = (),
        callbacks: AssetLoadCallbacks | None = None,
        force_reload: bool = False,
        font_weight: float = 1.0,
        audio_weight: float = 1.0,
        texture_weight: float = 1.0,
    ) -> list[object]:
        """
        Add incremental asset stages to a SceneLoadTask.

        Exactly one asset is initialized per task.update() call, which keeps the
        LoadingScene responsive while status/progress callbacks are emitted.
        """
        callbacks = callbacks or AssetLoadCallbacks()
        font_items = normalize_font_requests(fonts)
        sound_items = list(sounds)
        texture_items = list(textures)
        created: list[object] = []
        remaining_categories = sum(bool(x) for x in (font_items, sound_items, texture_items))
        completed_categories = 0

        def add_category(category: AssetCategory, items, weight: float, loader) -> None:
            nonlocal completed_categories
            if not items:
                return

            state = {
                "index": 0,
                "started": False,
                "completion_pending": False,
            }
            stage_ref: dict[str, object] = {}

            def update(_delta_time: float) -> bool:
                nonlocal completed_categories
                stage = stage_ref["stage"]
                total = len(items)

                if not state["started"]:
                    state["started"] = True
                    initial = self._progress(category, 0, total)
                    stage.progress = 0.0
                    stage.status = initial.status
                    self._emit(callbacks.on_stage_started, initial)
                    self._emit(callbacks.on_progress, initial)

                if state["completion_pending"]:
                    state["completion_pending"] = False
                    stage.progress = 1.0
                    return True

                index = state["index"]
                if index >= total:
                    stage.progress = 1.0
                    return True

                item = items[index]
                try:
                    path = loader(item)
                except BaseException as exc:
                    self._emit(callbacks.on_failed, exc)
                    raise

                state["index"] = index + 1
                progress = self._progress(category, state["index"], total, path)
                stage.progress = progress.progress
                stage.status = progress.status
                self._emit(callbacks.on_asset_loaded, progress)
                self._emit(callbacks.on_progress, progress)

                if state["index"] >= total:
                    completed_categories += 1
                    if completed_categories >= remaining_categories:
                        self._emit(callbacks.on_completed)

                    # Keep 100% visible for one rendered frame before
                    # SceneLoadTask advances to the next asset category.
                    state["completion_pending"] = True
                    return False

                return False

            stage = task.add_stage(
                f"assets_{category.value.lower()}",
                weight=weight,
                status=f"Initialisiere Assets: {category.value} 0%",
                update=update,
            )
            stage_ref["stage"] = stage
            created.append(stage)

        add_category(
            AssetCategory.FONT,
            font_items,
            font_weight,
            lambda item: (self.font(item.path, item.size, force_reload=force_reload), item.path)[1],
        )
        add_category(
            AssetCategory.AUDIO,
            sound_items,
            audio_weight,
            lambda item: (self.sound(item, force_reload=force_reload), item)[1],
        )
        add_category(
            AssetCategory.TEXTURE,
            texture_items,
            texture_weight,
            lambda item: (self.texture(item, force_reload=force_reload), item)[1],
        )

        if not created:
            self._emit(callbacks.on_completed)

        return created

    # ============================================================== 
    # Generic cache / cleanup
    # ============================================================== 

    def get(self, path: str | Path) -> Any | None:
        with self._lock:
            asset = self._assets.get(self._cache_key(path))
            return None if asset is None or not asset.loaded else asset.value

    def is_loaded(self, path: str | Path) -> bool:
        with self._lock:
            asset = self._assets.get(self._cache_key(path))
            return asset is not None and asset.loaded

    def is_loading(self, path: str | Path) -> bool:
        with self._lock:
            asset = self._assets.get(self._cache_key(path))
            return asset is not None and asset.status is AssetStatus.LOADING

    def is_failed(self, path: str | Path) -> bool:
        with self._lock:
            asset = self._assets.get(self._cache_key(path))
            return asset is not None and asset.failed

    def unload(self, path: str | Path) -> bool:
        """Unload every managed representation of one path."""
        key = self._cache_key(path)
        changed = self.unload_texture(path, unload_image=False)
        changed = self.unload_sound(path) or changed
        with self._lock:
            changed = self._assets.pop(key, None) is not None or changed
        return changed

    def clear(self) -> None:
        with self._lock:
            textures = list(self._textures.values())
            self._textures.clear()
            self._assets.clear()
            fonts = list(self._fonts.values())
            self._fonts.clear()
            sound_paths = tuple(self._managed_sound_paths)
            self._managed_sound_paths.clear()

        for texture in textures:
            texture.destroy()
        for font in fonts:
            font.close()
        if self._audio_cache is not None:
            for path in sound_paths:
                self._audio_cache.remove(path)

    def count(self) -> int:
        """Compatibility count: CPU assets + fonts."""
        with self._lock:
            return len(self._assets) + len(self._fonts)

    def asset_count(self) -> int:
        with self._lock:
            return len(self._assets)

    def font_count(self) -> int:
        with self._lock:
            return len(self._fonts)

    def texture_count(self) -> int:
        with self._lock:
            return len(self._textures)

    def sound_count(self) -> int:
        return len(self._managed_sound_paths)

    def paths(self) -> list[str]:
        with self._lock:
            return [asset.path for asset in self._assets.values()]

    def font_keys(self) -> list[tuple[str, float]]:
        with self._lock:
            return list(self._fonts.keys())

    def get_asset(self, path: str | Path) -> Asset | None:
        with self._lock:
            return self._assets.get(self._cache_key(path))

    def shutdown(self) -> None:
        self.clear()
        self.text_system.shutdown()
