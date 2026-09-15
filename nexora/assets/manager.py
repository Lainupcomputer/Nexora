from __future__ import annotations

import threading
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, TypeVar

from nexora.assets.asset import Asset, AssetStatus
from nexora.assets.loader import AssetLoader, FontLoader, ImageData, TextureLoader
from nexora.assets.group import AssetGroupDefinition, normalize_group_name
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

        # Asset groups -------------------------------------------------
        # Definitions are declarative. Active groups are reference-counted
        # independently from individual resources so dependencies and shared
        # assets remain resident until the last group releases them.
        self._groups: dict[str, AssetGroupDefinition] = {}
        self._group_ref_counts: dict[str, int] = {}
        self._group_resource_refs: dict[tuple[str, object], int] = {}

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
    # Asset groups
    # ==============================================================

    def register_group(
        self,
        name: str,
        *,
        fonts: Iterable[FontAssetRequest | tuple[str | Path, float]] = (),
        sounds: Iterable[str | Path] = (),
        textures: Iterable[str | Path] = (),
        dependencies: Iterable[str] = (),
        persistent: bool = False,
        replace: bool = False,
    ) -> AssetGroupDefinition:
        """Register a named asset group.

        Groups are definitions only; registering one does not load anything.
        """
        definition = AssetGroupDefinition.create(
            name,
            fonts=fonts,
            sounds=sounds,
            textures=textures,
            dependencies=dependencies,
            persistent=persistent,
        )

        with self._lock:
            if definition.name in self._groups and not replace:
                raise ValueError(
                    f"Asset group {definition.name!r} is already registered."
                )
            if self._group_ref_counts.get(definition.name, 0) > 0:
                raise RuntimeError(
                    f"Cannot replace active asset group {definition.name!r}."
                )
            self._groups[definition.name] = definition
            self._group_ref_counts.setdefault(definition.name, 0)

        return definition

    def unregister_group(self, name: str) -> bool:
        name = normalize_group_name(name)
        with self._lock:
            if self._group_ref_counts.get(name, 0) > 0:
                raise RuntimeError(
                    f"Cannot unregister active asset group {name!r}."
                )
            existed = self._groups.pop(name, None) is not None
            self._group_ref_counts.pop(name, None)
            return existed

    def get_group(self, name: str) -> AssetGroupDefinition | None:
        name = normalize_group_name(name)
        with self._lock:
            return self._groups.get(name)

    def group_names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._groups)

    def loaded_groups(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                name
                for name, count in self._group_ref_counts.items()
                if count > 0
            )

    def group_ref_count(self, name: str) -> int:
        name = normalize_group_name(name)
        with self._lock:
            return int(self._group_ref_counts.get(name, 0))

    def is_group_loaded(self, name: str) -> bool:
        return self.group_ref_count(name) > 0

    def _require_group(self, name: str) -> AssetGroupDefinition:
        name = normalize_group_name(name)
        definition = self._groups.get(name)
        if definition is None:
            raise KeyError(f"Unknown asset group: {name!r}")
        return definition

    def _group_acquire_deltas(self, name: str) -> Counter[str]:
        """Return reference increments for a group and all dependency edges."""
        root = normalize_group_name(name)
        deltas: Counter[str] = Counter()

        def visit(current: str, stack: tuple[str, ...]) -> None:
            definition = self._require_group(current)
            if current in stack:
                cycle = " -> ".join((*stack, current))
                raise ValueError(f"Asset group dependency cycle: {cycle}")

            deltas[current] += 1
            next_stack = (*stack, current)
            for dependency in definition.dependencies:
                visit(dependency, next_stack)

        with self._lock:
            visit(root, ())

        return deltas

    def _transitioning_groups(
        self,
        deltas: Counter[str],
        *,
        force_reload: bool,
    ) -> list[AssetGroupDefinition]:
        with self._lock:
            result = []
            for name in deltas:
                definition = self._require_group(name)
                if force_reload or self._group_ref_counts.get(name, 0) == 0:
                    result.append(definition)
            return result

    def _collect_group_assets(
        self,
        definitions: Iterable[AssetGroupDefinition],
    ) -> tuple[list[FontAssetRequest], list[str | Path], list[str | Path]]:
        fonts: list[FontAssetRequest] = []
        sounds: list[str | Path] = []
        textures: list[str | Path] = []
        seen_fonts: set[tuple[str, float]] = set()
        seen_sounds: set[str] = set()
        seen_textures: set[str] = set()

        for definition in definitions:
            for font in definition.fonts:
                key = self._font_cache_key(font.path, font.size)
                if key not in seen_fonts:
                    seen_fonts.add(key)
                    fonts.append(font)

            for sound in definition.sounds:
                key = self._cache_key(sound)
                if key not in seen_sounds:
                    seen_sounds.add(key)
                    sounds.append(sound)

            for texture in definition.textures:
                key = self._cache_key(texture)
                if key not in seen_textures:
                    seen_textures.add(key)
                    textures.append(texture)

        return fonts, sounds, textures

    def _group_resource_tokens(
        self,
        definition: AssetGroupDefinition,
    ) -> tuple[tuple[str, object], ...]:
        tokens: list[tuple[str, object]] = []
        tokens.extend(
            ("font", self._font_cache_key(font.path, font.size))
            for font in definition.fonts
        )
        tokens.extend(
            ("audio", self._cache_key(path))
            for path in definition.sounds
        )
        tokens.extend(
            ("texture", self._cache_key(path))
            for path in definition.textures
        )
        return tuple(tokens)

    def _commit_group_acquire(self, deltas: Counter[str]) -> None:
        with self._lock:
            for name, delta in deltas.items():
                previous = self._group_ref_counts.get(name, 0)
                self._group_ref_counts[name] = previous + int(delta)

                if previous == 0:
                    definition = self._require_group(name)
                    for token in self._group_resource_tokens(definition):
                        self._group_resource_refs[token] = (
                            self._group_resource_refs.get(token, 0) + 1
                        )

    def load_group(
        self,
        name: str,
        *,
        callbacks: AssetLoadCallbacks | None = None,
        force_reload: bool = False,
    ) -> AssetGroupDefinition:
        """Synchronously acquire a group and all of its dependencies.

        All newly required resources are loaded globally in the same order as
        the normal asset pipeline: Font -> Audio -> Texture.
        """
        name = normalize_group_name(name)
        deltas = self._group_acquire_deltas(name)
        definitions = self._transitioning_groups(
            deltas,
            force_reload=force_reload,
        )
        fonts, sounds, textures = self._collect_group_assets(definitions)

        self.preload(
            fonts=fonts,
            sounds=sounds,
            textures=textures,
            callbacks=callbacks,
            force_reload=force_reload,
        )
        self._commit_group_acquire(deltas)
        return self._require_group(name)

    def add_group_loading_stages(
        self,
        task,
        name: str,
        *,
        callbacks: AssetLoadCallbacks | None = None,
        force_reload: bool = False,
        font_weight: float = 1.0,
        audio_weight: float = 1.0,
        texture_weight: float = 1.0,
        commit_weight: float = 0.05,
    ) -> list[object]:
        """Add one group's loading pipeline to a SceneLoadTask.

        Dependencies are resolved first, duplicate assets are removed, and the
        resulting resources still load in Font -> Audio -> Texture order.
        Group references are committed only after all loading stages succeed.
        """
        name = normalize_group_name(name)
        deltas = self._group_acquire_deltas(name)
        definitions = self._transitioning_groups(
            deltas,
            force_reload=force_reload,
        )
        fonts, sounds, textures = self._collect_group_assets(definitions)

        stages = self.add_loading_stages(
            task,
            fonts=fonts,
            sounds=sounds,
            textures=textures,
            callbacks=callbacks,
            force_reload=force_reload,
            font_weight=font_weight,
            audio_weight=audio_weight,
            texture_weight=texture_weight,
        )

        def commit() -> None:
            self._commit_group_acquire(deltas)

        commit_stage = task.add_stage(
            f"assets_group_{name}",
            weight=max(0.0001, float(commit_weight)),
            status=f"Asset-Gruppe bereit: {name}",
            callback=commit,
        )
        stages.append(commit_stage)
        return stages

    def unload_group(
        self,
        name: str,
        *,
        force: bool = False,
        unload_assets: bool = True,
    ) -> bool:
        """Release one reference to a group and its dependency closure.

        Resources shared with another active group remain loaded. Persistent
        groups ignore normal unload requests and require force=True.
        """
        name = normalize_group_name(name)
        with self._lock:
            definition = self._require_group(name)
            if self._group_ref_counts.get(name, 0) <= 0:
                return False
            if definition.persistent and not force:
                return False

        deltas = self._group_acquire_deltas(name)
        groups_to_release: list[AssetGroupDefinition] = []

        with self._lock:
            # Validate before mutating so a broken ref graph cannot partially
            # unload a group.
            for group_name, delta in deltas.items():
                current = self._group_ref_counts.get(group_name, 0)
                if current < delta:
                    raise RuntimeError(
                        f"Asset group reference underflow for {group_name!r}: "
                        f"{current} < {delta}."
                    )

            for group_name, delta in deltas.items():
                current = self._group_ref_counts[group_name]
                new_value = current - int(delta)
                child = self._require_group(group_name)

                if child.persistent and not force:
                    new_value = max(1, new_value)

                self._group_ref_counts[group_name] = new_value
                if current > 0 and new_value == 0:
                    groups_to_release.append(child)

            releasable: list[tuple[str, object]] = []
            for child in groups_to_release:
                for token in self._group_resource_tokens(child):
                    count = self._group_resource_refs.get(token, 0) - 1
                    if count <= 0:
                        self._group_resource_refs.pop(token, None)
                        releasable.append(token)
                    else:
                        self._group_resource_refs[token] = count

        if unload_assets:
            for kind, key in releasable:
                if kind == "font":
                    path_key, size = key
                    self.unload_font(Path(path_key), size)
                elif kind == "audio":
                    self.unload_sound(Path(str(key)))
                elif kind == "texture":
                    self.unload_texture(Path(str(key)), unload_image=True)

        return True

    def clear_groups(self, *, unload_assets: bool = True) -> None:
        """Force-release every active group while keeping definitions."""
        with self._lock:
            names = [
                name
                for name, count in self._group_ref_counts.items()
                if count > 0
            ]

        # Force each group down to zero. Repeated references require repeated
        # releases, so loop until no active references remain.
        for name in names:
            while self.group_ref_count(name) > 0:
                self.unload_group(
                    name,
                    force=True,
                    unload_assets=unload_assets,
                )

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
            for name in self._group_ref_counts:
                self._group_ref_counts[name] = 0
            self._group_resource_refs.clear()

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
