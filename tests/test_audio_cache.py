from pathlib import Path


import pytest

from nexora.audio import AudioCache, Sound


def test_audio_cache_starts_empty():
    cache = AudioCache()

    assert cache.sounds == ()


def test_audio_cache_loads_sound(monkeypatch, tmp_path):
    cache = AudioCache()
    path = tmp_path / "test.wav"

    sound = object()

    def fake_load(self, load_path):
        assert load_path == path
        return sound

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        fake_load,
    )

    result = cache.load(path)

    assert result is sound
    assert cache.get(path) is sound
    assert cache.sounds == (sound,)


def test_audio_cache_returns_cached_sound(monkeypatch, tmp_path):
    cache = AudioCache()
    path = tmp_path / "test.wav"

    first = object()
    second = object()

    calls = 0

    def fake_load(self, load_path):
        nonlocal calls
        calls += 1

        if calls == 1:
            return first

        return second

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        fake_load,
    )

    assert cache.load(path) is first
    assert cache.load(path) is first
    assert calls == 1


def test_audio_cache_get_missing_returns_none(tmp_path):
    cache = AudioCache()

    assert cache.get(
        tmp_path / "missing.wav"
    ) is None


def test_audio_cache_remove(tmp_path):
    cache = AudioCache()
    path = tmp_path / "test.wav"

    sound = object()

    cache._sounds[path] = sound

    cache.remove(path)

    assert cache.get(path) is None
    assert cache.sounds == ()


def test_audio_cache_remove_missing_does_nothing(tmp_path):
    cache = AudioCache()

    cache.remove(
        tmp_path / "missing.wav"
    )

    assert cache.sounds == ()


def test_audio_cache_clear(tmp_path):
    cache = AudioCache()

    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"

    cache._sounds[first] = object()
    cache._sounds[second] = object()

    cache.clear()

    assert cache.sounds == ()

def test_audio_cache_normalizes_paths(
    monkeypatch,
    tmp_path,
):
    cache = AudioCache()

    path = tmp_path / "sounds" / "test.wav"
    path.parent.mkdir()

    sound = object()
    calls = 0

    def fake_load(self, load_path):
        nonlocal calls
        calls += 1

        assert load_path == path.resolve()

        return sound

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        fake_load,
    )

    relative_path = path.parent / "." / path.name

    assert cache.load(path) is sound
    assert cache.load(relative_path) is sound
    assert calls == 1


def test_audio_cache_get_normalizes_paths(tmp_path):
    cache = AudioCache()

    path = tmp_path / "test.wav"
    sound = object()

    cache._sounds[path.resolve()] = sound

    assert cache.get(path) is sound


def test_audio_cache_remove_normalizes_paths(tmp_path):
    cache = AudioCache()

    path = tmp_path / "test.wav"
    sound = object()

    cache._sounds[path.resolve()] = sound

    cache.remove(
        path.parent / "." / path.name
    )

    assert cache.sounds == ()

def test_audio_cache_count():
    cache = AudioCache()

    assert cache.count == 0

    cache._sounds[Path("first.wav").resolve()] = object()
    cache._sounds[Path("second.wav").resolve()] = object()

    assert cache.count == 2


def test_audio_cache_contains(tmp_path):
    cache = AudioCache()

    path = tmp_path / "test.wav"
    sound = object()

    cache._sounds[path.resolve()] = sound

    assert cache.contains(path)
    assert cache.contains(
        path.parent / "." / path.name
    )


def test_audio_cache_contains_missing(tmp_path):
    cache = AudioCache()

    assert not cache.contains(
        tmp_path / "missing.wav"
    )