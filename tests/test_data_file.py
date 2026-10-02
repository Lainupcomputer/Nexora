from __future__ import annotations

from pathlib import Path

import pytest

from nexora.data import (
    DataFile,
    DataIntegrityError,
    DataType,
    DataTypeMismatchError,
    decode_file,
    encode_file,
    load_file,
    save_file,
)

KEY = b"nexora-data-test-signing-key-0123456789abcdef"


def test_data_file_roundtrip_unsigned(tmp_path: Path) -> None:
    path = save_file(
        tmp_path / "item.nitem",
        DataFile(DataType.Item, 1, {"item": {"id": "iron"}}),
    )
    assert path.read_bytes().startswith(b"NXDATA01")
    loaded = load_file(path, expected_type=DataType.Item)
    assert loaded.data_type is DataType.Item
    assert loaded.version == 1
    assert loaded.data["item"]["id"] == "iron"


def test_data_file_roundtrip_signed() -> None:
    raw = encode_file(
        DataFile(DataType.Scene, 1, {"name": "World"}),
        signing_key=KEY,
    )
    loaded = decode_file(raw, expected_type=DataType.Scene, signing_key=KEY)
    assert loaded.data == {"name": "World"}


def test_data_file_rejects_wrong_type() -> None:
    raw = encode_file(DataFile(DataType.Item, 1, {}))
    with pytest.raises(DataTypeMismatchError):
        decode_file(raw, expected_type=DataType.Scene)


def test_data_file_detects_tampering() -> None:
    raw = bytearray(
        encode_file(DataFile(DataType.SaveGame, 1, {"value": 1}), signing_key=KEY)
    )
    raw[-1] ^= 1
    with pytest.raises(DataIntegrityError):
        decode_file(bytes(raw), expected_type=DataType.SaveGame, signing_key=KEY)


def test_audio_preset_codec_roundtrip(tmp_path):
    from nexora.audio import AudioPreset, GainEffect
    from nexora.data.codecs import audio_preset

    preset = AudioPreset.from_effects("Test", (GainEffect(0.75),), description="demo")
    path = tmp_path / "test.npreset"
    audio_preset.save(preset, path)
    loaded = audio_preset.load(path)

    assert loaded.name == "Test"
    assert loaded.description == "demo"
    assert loaded.effects[0]["type"] == "gain"


def test_audio_mixer_codec_roundtrip(tmp_path):
    from nexora.data.codecs import audio_mixer

    snapshot = {"headroom_db": -3.0, "buses": [{"name": "Master", "volume": 0.8}]}
    path = tmp_path / "audio_mixer.nmix"
    audio_mixer.save(snapshot, path)

    assert audio_mixer.load(path) == snapshot
