from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

from nexora.assets import AssetLoader, AssetManager, AssetStatus


class TextLoader(AssetLoader[str]):
    """Small test loader that does not require pygame."""

    def __init__(self) -> None:
        self.load_count = 0
        self._lock = threading.Lock()

    def load(self, path: Path) -> str:
        with self._lock:
            self.load_count += 1

        return path.read_text(encoding="utf-8")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("NEXORA ASSET MANAGER TEST")
    print("=" * 60)
    print(f"Python: {sys.version.split()[0]}")

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"GIL: {gil_enabled}")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        # ----------------------------------------------------------
        # Setup
        # ----------------------------------------------------------

        asset_file = root / "test.txt"
        asset_file.write_text(
            "Hello from Nexora!",
            encoding="utf-8",
        )

        manager = AssetManager(root)

        loader = TextLoader()
        manager.register_loader(".txt", loader)

        # ----------------------------------------------------------
        # 1. Path resolution
        # ----------------------------------------------------------

        print("\n1. PATH RESOLUTION")

        resolved = manager.resolve("test.txt")

        check(resolved == asset_file.resolve(), "Path resolution failed.")
        check(manager.exists("test.txt"), "Asset should exist.")

        print("✅ Asset path resolved correctly")
        print(f"   {resolved}")

        # ----------------------------------------------------------
        # 2. Loading
        # ----------------------------------------------------------

        print("\n2. LOADING")

        value = manager.load("test.txt")

        check(value == "Hello from Nexora!", "Loaded content is incorrect.")
        check(manager.is_loaded("test.txt"), "Asset should be loaded.")
        check(manager.count() == 1, "Cache should contain one asset.")

        print("✅ Asset loaded")
        print(f"   Value: {value}")

        # ----------------------------------------------------------
        # 3. Cache
        # ----------------------------------------------------------

        print("\n3. CACHE")

        first = manager.load("test.txt")
        second = manager.load("test.txt")

        check(first is second, "Cached asset should return the same object.")
        check(loader.load_count == 1, "Loader was called more than once.")

        print("✅ Cache returns existing asset")
        print(f"   Loader calls: {loader.load_count}")

        # ----------------------------------------------------------
        # 4. Asset state
        # ----------------------------------------------------------

        print("\n4. ASSET STATE")

        asset = manager.get_asset("test.txt")

        check(asset is not None, "Asset object should exist.")
        check(asset.status is AssetStatus.LOADED, "Asset should be loaded.")
        check(asset.loaded, "Asset.loaded should be True.")
        check(not asset.failed, "Asset.failed should be False.")

        print("✅ Asset state is correct")
        print(f"   Status: {asset.status.value}")

        # ----------------------------------------------------------
        # 5. Force reload
        # ----------------------------------------------------------

        print("\n5. FORCE RELOAD")

        asset_file.write_text(
            "Reloaded!",
            encoding="utf-8",
        )

        reloaded = manager.load(
            "test.txt",
            force_reload=True,
        )

        check(reloaded == "Reloaded!", "Force reload failed.")
        check(loader.load_count == 2, "Force reload did not call loader.")

        print("✅ Force reload works")
        print(f"   Loader calls: {loader.load_count}")

        # ----------------------------------------------------------
        # 6. Unload
        # ----------------------------------------------------------

        print("\n6. UNLOAD")

        removed = manager.unload("test.txt")

        check(removed, "Asset should have been removed.")
        check(manager.get("test.txt") is None, "Asset is still cached.")
        check(manager.count() == 0, "Cache should be empty.")

        print("✅ Asset unloaded")

        # ----------------------------------------------------------
        # 7. Reload after unload
        # ----------------------------------------------------------

        print("\n7. RELOAD AFTER UNLOAD")

        value = manager.load("test.txt")

        check(value == "Reloaded!", "Reload after unload failed.")
        check(loader.load_count == 3, "Loader should have been called again.")

        print("✅ Asset can be loaded again")

        # ----------------------------------------------------------
        # 8. Thread safety
        # ----------------------------------------------------------

        print("\n8. THREAD SAFETY")

        manager.clear()
        loader.load_count = 0

        results: list[str] = []
        errors: list[BaseException] = []
        result_lock = threading.Lock()

        def worker() -> None:
            try:
                value = manager.load("test.txt")

                with result_lock:
                    results.append(value)

            except BaseException as exc:
                with result_lock:
                    errors.append(exc)

        threads = [
            threading.Thread(
                target=worker,
                name=f"AssetTest-{index}",
            )
            for index in range(16)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        check(not errors, f"Thread errors occurred: {errors!r}")
        check(len(results) == 16, "Not all threads returned a result.")
        check(
            all(value == "Reloaded!" for value in results),
            "Threads received incorrect asset data.",
        )

        print("✅ Concurrent access works")
        print(f"   Threads: {len(threads)}")
        print(f"   Results: {len(results)}")

        # ----------------------------------------------------------
        # 9. Clear
        # ----------------------------------------------------------

        print("\n9. CLEAR CACHE")

        check(manager.count() == 1, "Expected one cached asset.")

        manager.clear()

        check(manager.count() == 0, "Cache was not cleared.")
        check(manager.get("test.txt") is None, "Asset still exists.")

        print("✅ Cache cleared")

    print("\n" + "=" * 60)
    print("ASSET MANAGER TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
