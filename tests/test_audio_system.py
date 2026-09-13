
from __future__ import annotations

import math
import struct
import wave

import pytest

from nexora.audio import (
    AudioBuffer,
    AudioBus,
    AudioChannel,
    AudioMixer,
    AudioPlayer,
    AudioSource,
    AudioSourceState,
    AudioSystem,
    MusicPlayer,
    RepeatMode,
    Sound,
    WavLoader,
)
from nexora.audio.device import AudioDevice
from nexora.audio.listener import AudioListener
from nexora.audio.pcm import decode_pcm
from nexora.audio.spatial import (
    calculate_distance,
    calculate_distance_attenuation,
    calculate_pan_gains,
    calculate_stereo_pan,
)


# ============================================================
# Helpers
# ============================================================


def make_sound(
    frames: int = 48000,
    frequency: int = 48000,
) -> Sound:
    buffer = AudioBuffer(
        data=b"\x00\x00" * frames,
        frequency=frequency,
        channels=1,
        bytes_per_sample=2,
    )

    return Sound(buffer=buffer)


def create_wav(
    tmp_path,
    *,
    name: str = "test.wav",
    frequency: int = 48_000,
    channels: int = 1,
    frames: int = 100,
    sample_width: int = 2,
    value: int = 0,
):
    path = tmp_path / name

    if channels == 1:
        samples = [value] * frames
    else:
        samples = [value] * (frames * channels)

    if sample_width == 1:
        data = bytes(
            max(0, min(255, sample + 128))
            for sample in samples
        )

    elif sample_width == 2:
        data = struct.pack(
            f"<{len(samples)}h",
            *samples,
        )

    elif sample_width == 4:
        data = struct.pack(
            f"<{len(samples)}i",
            *samples,
        )

    else:
        raise ValueError(
            "Unsupported test sample width."
        )

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(frequency)
        wav.writeframes(data)

    return path


def make_test_sequence_sound() -> Sound:
    samples = b"".join(
        value.to_bytes(
            2,
            byteorder="little",
            signed=True,
        )
        for value in range(1, 11)
    )

    buffer = AudioBuffer(
        data=samples,
        frequency=48000,
        channels=1,
        bytes_per_sample=2,
    )

    return Sound(buffer=buffer)


def make_test_sound(
    value: int = 16384,
    frames: int = 1,
) -> Sound:
    sample = value.to_bytes(
        2,
        byteorder="little",
        signed=True,
    )

    buffer = AudioBuffer(
        data=sample * frames,
        frequency=48000,
        channels=1,
        bytes_per_sample=2,
    )

    return Sound(buffer=buffer)


def create_sound(
    tmp_path,
    *,
    name: str = "test.wav",
    frequency: int = 48_000,
    channels: int = 1,
    frames: int = 100,
    value: int = 0,
) -> Sound:
    path = create_wav(
        tmp_path,
        name=name,
        frequency=frequency,
        channels=channels,
        frames=frames,
        value=value,
    )

    return Sound.load(path)


# ============================================================
# AudioBuffer
# ============================================================


def test_audio_buffer_properties():
    buffer = AudioBuffer(
        data=b"\x00" * 800,
        frequency=48_000,
        channels=2,
        bytes_per_sample=2,
    )

    assert buffer.size == 800
    assert buffer.sample_count == 200

    assert math.isclose(
        buffer.duration,
        200 / 48_000,
    )


def test_audio_buffer_empty():
    buffer = AudioBuffer(
        data=b"",
        frequency=48_000,
        channels=2,
        bytes_per_sample=2,
    )

    assert buffer.size == 0
    assert buffer.sample_count == 0
    assert buffer.duration == 0.0
    assert buffer.is_empty()


def test_audio_buffer_not_empty():
    buffer = AudioBuffer(
        data=b"\x00\x00",
        frequency=48_000,
        channels=1,
        bytes_per_sample=2,
    )

    assert not buffer.is_empty()


def test_audio_buffer_invalid_frequency():
    buffer = AudioBuffer(
        data=b"\x00\x00",
        frequency=0,
        channels=1,
        bytes_per_sample=2,
    )

    assert buffer.duration == 0.0


# ============================================================
# WAV Loader
# ============================================================


def test_wav_loader_loads_valid_file(tmp_path):
    path = create_wav(
        tmp_path,
        frequency=44_100,
        channels=2,
        frames=100,
    )

    buffer = WavLoader().load(path)

    assert buffer.frequency == 44_100
    assert buffer.channels == 2
    assert buffer.sample_count == 100
    assert buffer.size > 0


def test_wav_loader_missing_file(tmp_path):
    path = tmp_path / "missing.wav"

    with pytest.raises(FileNotFoundError):
        WavLoader().load(path)


def test_wav_loader_invalid_file(tmp_path):
    path = tmp_path / "invalid.wav"

    path.write_bytes(
        b"this is not a wav file"
    )

    with pytest.raises(ValueError):
        WavLoader().load(path)


# ============================================================
# Sound
# ============================================================


def test_sound_load(tmp_path):
    path = create_wav(
        tmp_path,
        frequency=48_000,
        channels=2,
        frames=240,
    )

    sound = Sound.load(path)

    assert sound.path == path
    assert sound.frequency == 48_000
    assert sound.channels == 2
    assert sound.size > 0

    assert math.isclose(
        sound.duration,
        240 / 48_000,
    )


def test_sound_load_normalizes_path(monkeypatch, tmp_path):
    path = tmp_path / "sounds" / "test.wav"
    path.parent.mkdir()

    buffer = AudioBuffer(
        data=b"\x00\x00",
        frequency=48000,
        channels=1,
        bytes_per_sample=2,
    )

    def fake_load(self, load_path):
        assert load_path == path.resolve()
        return buffer

    monkeypatch.setattr(
        "nexora.audio.sound.WavLoader.load",
        fake_load,
    )

    sound = Sound.load(
        path.parent / "." / path.name
    )

    assert sound.path == path.resolve()


# ============================================================
# AudioMixer
# ============================================================


def test_audio_mixer_defaults():
    mixer = AudioMixer()

    for channel in AudioChannel:
        assert mixer.get_volume(channel) == 1.0


def test_audio_mixer_set_volume():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.MUSIC,
        0.5,
    )

    assert mixer.get_volume(
        AudioChannel.MUSIC
    ) == 0.5


def test_audio_mixer_volume_lower_bound():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.SFX,
        0.0,
    )

    assert mixer.get_volume(
        AudioChannel.SFX
    ) == 0.0


def test_audio_mixer_volume_upper_bound():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.SFX,
        1.0,
    )

    assert mixer.get_volume(
        AudioChannel.SFX
    ) == 1.0


@pytest.mark.parametrize(
    "value",
    [-0.1, 1.1, 2.0],
)
def test_audio_mixer_invalid_volume(value):
    mixer = AudioMixer()

    with pytest.raises(ValueError):
        mixer.set_volume(
            AudioChannel.SFX,
            value,
        )


def test_audio_mixer_effective_volume():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.MASTER,
        0.5,
    )

    mixer.set_volume(
        AudioChannel.MUSIC,
        0.8,
    )

    assert math.isclose(
        mixer.get_effective_volume(
            AudioChannel.MUSIC
        ),
        0.4,
    )


def test_audio_mixer_master_effective_volume():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.MASTER,
        0.25,
    )

    assert mixer.get_effective_volume(
        AudioChannel.MASTER
    ) == 0.25


def test_audio_mixer_reset():
    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.MASTER,
        0.2,
    )

    mixer.set_volume(
        AudioChannel.MUSIC,
        0.4,
    )

    mixer.reset()

    for channel in AudioChannel:
        assert mixer.get_volume(channel) == 1.0


# ============================================================
# AudioSource
# ============================================================


def test_audio_source_initial_state(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    assert source.state == AudioSourceState.STOPPED
    assert source.stopped
    assert not source.playing
    assert not source.paused
    assert source.position == 0


def test_audio_source_play(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    source.play()

    assert source.state == AudioSourceState.PLAYING
    assert source.playing
    assert source.position == 0


def test_audio_source_pause(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    source.play()
    source.pause()

    assert source.paused
    assert source.state == AudioSourceState.PAUSED


def test_audio_source_resume(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    source.play()
    source.pause()
    source.resume()

    assert source.playing
    assert source.state == AudioSourceState.PLAYING


def test_audio_source_stop(tmp_path):
    sound = create_sound(
        tmp_path,
        frames=100,
    )

    source = AudioSource(sound)

    source.play()

    source._position = 50

    source.stop()

    assert source.stopped
    assert source.position == 0


def test_audio_source_play_resets_position(tmp_path):
    sound = create_sound(
        tmp_path,
        frames=100,
    )

    source = AudioSource(sound)

    source.play()
    source._position = 50

    source.play()

    assert source.playing
    assert source.position == 0


def test_audio_source_pause_only_when_playing(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    source.pause()

    assert source.stopped


def test_audio_source_resume_only_when_paused(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    source.resume()

    assert source.stopped


def test_audio_source_volume(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(
        sound,
        volume=0.5,
    )

    assert source.get_effective_volume(AudioMixer()) == pytest.approx(0.5)


@pytest.mark.parametrize(
    "value",
    [-0.1, 1.1],
)
def test_audio_source_invalid_volume(
    value,
    tmp_path,
):
    sound = create_sound(tmp_path)

    with pytest.raises(ValueError):
        AudioSource(
            sound,
            volume=value,
        )


def test_audio_source_loop(tmp_path):
    sound = create_sound(tmp_path)

    source = AudioSource(
        sound,
        loop=True,
    )

    assert source.loop

    source.loop = False

    assert not source.loop


def test_audio_source_effective_volume(tmp_path):
    sound = create_sound(tmp_path)

    mixer = AudioMixer()

    mixer.set_volume(
        AudioChannel.MASTER,
        0.5,
    )

    mixer.set_volume(
        AudioChannel.SFX,
        0.8,
    )

    source = AudioSource(
        sound,
        channel=AudioChannel.SFX,
        volume=0.5,
    )

    assert math.isclose(
        source.get_effective_volume(mixer),
        0.2,
    )


# ============================================================
# AudioPlayer
# ============================================================


def create_audio_player():
    device = object()
    mixer = AudioMixer()

    return AudioPlayer(
        device,
        mixer,
    )


def test_audio_player_initial_state():
    player = create_audio_player()

    assert player.sources == ()


def test_audio_player_add(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.add(source)

    assert source in player.sources


def test_audio_player_duplicate_add(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.add(source)
    player.add(source)

    assert player.sources == (source,)


def test_audio_player_remove(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.add(source)
    player.remove(source)

    assert source not in player.sources


def test_audio_player_remove_missing_source(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.remove(source)

    assert player.sources == ()


def test_audio_player_play(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.play(source)

    assert source in player.sources
    assert source.playing


def test_audio_player_pause(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.play(source)
    player.pause(source)

    assert source.paused


def test_audio_player_resume(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.play(source)
    player.pause(source)
    player.resume(source)

    assert source.playing


def test_audio_player_stop(tmp_path):
    player = create_audio_player()

    sound = create_sound(tmp_path)

    source = AudioSource(sound)

    player.play(source)
    player.stop(source)

    assert source.stopped
    assert source.position == 0


def test_audio_player_stop_all(tmp_path):
    player = create_audio_player()

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    source_a = AudioSource(sound_a)
    source_b = AudioSource(sound_b)

    player.play(source_a)
    player.play(source_b)

    player.stop_all()

    assert source_a.stopped
    assert source_b.stopped


def test_audio_player_mix_empty():
    player = create_audio_player()

    data = player.mix(100)

    assert data
    assert len(data) == 100 * 2 * 4


def test_audio_player_mix_silence(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        frames=100,
        value=0,
    )

    source = AudioSource(sound)

    player.play(source)

    data = player.mix(10)

    samples = struct.unpack(
        "<20f",
        data,
    )

    assert all(
        sample == 0.0
        for sample in samples
    )


def test_audio_player_source_finishes(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        frames=10,
    )

    source = AudioSource(sound)

    player.play(source)

    player.mix(10)

    assert source.stopped
    assert source.position == sound.buffer.sample_count

    player.mix(1)

    assert source.stopped


def test_audio_player_loop(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        frames=10,
    )

    source = AudioSource(
        sound,
        loop=True,
    )

    player.play(source)

    player.mix(25)

    assert source.playing
    assert source.position < 10


def test_audio_player_stereo(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        channels=2,
        frames=10,
        value=1000,
    )

    source = AudioSource(sound)

    player.play(source)

    data = player.mix(10)

    assert len(data) == 10 * 2 * 4


def test_audio_player_mono_to_stereo(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=10,
        value=1000,
    )

    source = AudioSource(sound)

    player.play(source)

    data = player.mix(10)

    samples = struct.unpack(
        "<20f",
        data,
    )

    for index in range(0, len(samples), 2):
        assert math.isclose(
            samples[index],
            samples[index + 1],
        )


def test_audio_player_volume_mixing(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=10,
        value=16384,
    )

    source = AudioSource(
        sound,
        volume=0.5,
    )

    player.play(source)

    data = player.mix(1)

    samples = struct.unpack(
        "<2f",
        data,
    )

    expected = (
        16384 / 32768
    ) * 0.5

    assert math.isclose(
        samples[0],
        expected,
        rel_tol=1e-5,
    )

    assert math.isclose(
        samples[1],
        expected,
        rel_tol=1e-5,
    )


def test_audio_player_clamps_output(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=10,
        value=32767,
    )

    source_a = AudioSource(
        sound,
        volume=1.0,
    )

    source_b = AudioSource(
        sound,
        volume=1.0,
    )

    player.play(source_a)
    player.play(source_b)

    data = player.mix(1)

    samples = struct.unpack(
        "<2f",
        data,
    )

    assert samples[0] <= 1.0
    assert samples[0] >= -1.0

    assert samples[1] <= 1.0
    assert samples[1] >= -1.0


def test_audio_player_ignores_paused_sources(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        frames=10,
        value=1000,
    )

    source = AudioSource(sound)

    player.play(source)
    source.pause()

    data = player.mix(1)

    samples = struct.unpack(
        "<2f",
        data,
    )

    assert samples == (
        0.0,
        0.0,
    )


def test_audio_player_ignores_stopped_sources(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        frames=10,
        value=1000,
    )

    source = AudioSource(sound)

    player.add(source)

    data = player.mix(1)

    samples = struct.unpack(
        "<2f",
        data,
    )

    assert samples == (
        0.0,
        0.0,
    )


def test_audio_player_zero_frame_mix():
    player = create_audio_player()

    assert player.mix(0) == b""


def test_audio_player_negative_frame_mix():
    player = create_audio_player()

    assert player.mix(-1) == b""


# ============================================================
# AudioSystem
# ============================================================


def test_audio_system_initial_state():
    audio = AudioSystem()

    assert not audio.initialized
    assert audio.mixer is not None
    assert audio.device is not None
    assert audio.player is not None
    assert audio.music is not None


def test_audio_system_volume():
    audio = AudioSystem()

    audio.set_volume(
        AudioChannel.MUSIC,
        0.4,
    )

    assert audio.get_volume(
        AudioChannel.MUSIC
    ) == 0.4


def test_audio_system_effective_volume():
    audio = AudioSystem()

    audio.set_volume(
        AudioChannel.MASTER,
        0.5,
    )

    audio.set_volume(
        AudioChannel.SFX,
        0.8,
    )

    assert math.isclose(
        audio.get_effective_volume(
            AudioChannel.SFX
        ),
        0.4,
    )


def test_audio_system_initialize():
    audio = AudioSystem()

    audio.device.initialize()

    audio._initialized = True

    assert audio.initialized

    audio.shutdown()


def test_audio_system_initialize_idempotent():
    audio = AudioSystem()

    audio.device.initialize()

    audio._initialized = True

    audio.initialize()

    assert audio.initialized

    audio.shutdown()


def test_audio_system_shutdown():
    audio = AudioSystem()

    audio.device.initialize()

    audio._initialized = True

    audio.shutdown()

    assert not audio.initialized


def test_audio_system_shutdown_idempotent():
    audio = AudioSystem()

    audio.shutdown()
    audio.shutdown()

    assert not audio.initialized


# ============================================================
# MusicPlayer integration
# ============================================================


def test_music_player_initial_state():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    assert music.current is None
    assert music.source is None
    assert music.queue == ()
    assert music.history == ()
    assert not music.playing
    assert not music.paused
    assert not music.shuffle
    assert music.repeat == RepeatMode.OFF


def test_music_player_play(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound = create_sound(tmp_path)

    music.play(sound)

    assert music.current is sound
    assert music.source is not None
    assert music.playing


def test_music_player_enqueue(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    music.enqueue(sound_a)
    music.enqueue(sound_b)

    assert music.queue == (
        sound_a,
        sound_b,
    )


def test_music_player_next(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    music.enqueue(sound_a)
    music.enqueue(sound_b)

    assert music.play_next()

    assert music.current is sound_a
    assert music.queue == (sound_b,)


def test_music_player_next_empty():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    assert not music.play_next()


def test_music_player_pause_resume(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound = create_sound(tmp_path)

    music.play(sound)
    music.pause()

    assert music.paused

    music.resume()

    assert music.playing


def test_music_player_stop(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound = create_sound(tmp_path)

    music.play(sound)
    music.stop()

    assert not music.playing
    assert music.source is not None
    assert music.source.stopped


def test_music_player_auto_next(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
        frames=1,
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
        frames=10,
    )

    music.play(sound_a)
    music.enqueue(sound_b)

    music.source._finish()

    music.update()

    assert music.current is sound_b
    assert music.playing


def test_music_player_previous(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    music.play(sound_a)
    music.play(sound_b)

    assert music.previous()

    assert music.current is sound_a


def test_music_player_previous_empty(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound = create_sound(tmp_path)

    music.play(sound)

    assert not music.previous()


def test_music_player_shuffle_initial():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    assert not music.shuffle


def test_music_player_shuffle_toggle():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    music.set_shuffle(True)

    assert music.shuffle

    music.set_shuffle(False)

    assert not music.shuffle


def test_music_player_shuffle_next(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    music.enqueue(sound_a)
    music.enqueue(sound_b)

    music.set_shuffle(True)

    assert music.play_next()

    assert music.current in (
        sound_a,
        sound_b,
    )

    assert len(music.queue) == 1


def test_music_player_repeat_initial():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    assert music.repeat == RepeatMode.OFF


def test_music_player_repeat_toggle():
    audio = AudioSystem()
    music = MusicPlayer(audio)

    music.set_repeat(RepeatMode.ONE)

    assert music.repeat == RepeatMode.ONE

    music.set_repeat(RepeatMode.ALL)

    assert music.repeat == RepeatMode.ALL

    music.set_repeat(RepeatMode.OFF)

    assert music.repeat == RepeatMode.OFF


def test_music_player_repeat_one(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound = create_sound(
        tmp_path,
        frames=10,
    )

    music.set_repeat(RepeatMode.ONE)
    music.play(sound)

    music.source._finish()

    music.update()

    assert music.current is sound
    assert music.playing
    assert music.history == ()


def test_music_player_repeat_all(tmp_path):
    audio = AudioSystem()
    music = MusicPlayer(audio)

    sound_a = create_sound(
        tmp_path,
        name="a.wav",
    )

    sound_b = create_sound(
        tmp_path,
        name="b.wav",
    )

    music.set_repeat(RepeatMode.ALL)

    music.play(sound_a)
    music.play(sound_b)

    music.source._finish()

    music.update()

    assert music.current is sound_a
    assert music.playing


# ============================================================
# AudioSource playback / seeking
# ============================================================


def test_audio_source_duration():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    assert source.duration == 1.0


def test_audio_source_position_seconds():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.seek(24000)

    assert source.position == 24000
    assert source.position_seconds == 0.5


def test_audio_source_remaining():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    assert source.remaining == 1.0

    source.seek(24000)

    assert source.remaining == 0.5


def test_audio_source_progress():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    assert source.progress == 0.0

    source.seek(24000)

    assert source.progress == 0.5

    source.seek(48000)

    assert source.progress == 1.0


def test_audio_source_seek():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.seek(12000)

    assert source.position == 12000


def test_audio_source_seek_clamps_to_end():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.seek(999999)

    assert source.position == 48000


def test_audio_source_seek_rejects_negative_frame():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source.seek(-1)


def test_audio_source_seek_seconds():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.seek_seconds(0.25)

    assert source.position == 12000
    assert source.position_seconds == 0.25


def test_audio_source_seek_seconds_clamps_to_end():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.seek_seconds(999.0)

    assert source.position == 48000


def test_audio_source_seek_seconds_rejects_negative():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source.seek_seconds(-1.0)


# ============================================================
# PCM cache
# ============================================================


def test_sound_pcm_cache():
    sound = make_sound(
        frames=100,
        frequency=48000,
    )

    first = sound.pcm
    second = sound.pcm

    assert first is second


def test_sound_pcm_cache_contains_decoded_samples():
    sound = make_sound(
        frames=100,
        frequency=48000,
    )

    samples = sound.pcm

    assert isinstance(samples, list)
    assert len(samples) == 100


def test_sound_clear_pcm_cache():
    sound = make_sound(
        frames=100,
        frequency=48000,
    )

    first = sound.pcm

    sound.clear_pcm_cache()

    second = sound.pcm

    assert second is not first


def test_audio_player_uses_pcm_cache(tmp_path):
    player = create_audio_player()

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=100,
    )

    source = AudioSource(sound)

    player.play(source)

    first = sound.pcm

    player.mix(10)

    second = sound.pcm

    assert first is second


# ============================================================
# Spatial Audio
# ============================================================


def test_audio_source_spatial_defaults():
    sound = make_sound()

    source = AudioSource(sound)

    assert source.position_2d == (0.0, 0.0)
    assert source.min_distance == 1.0
    assert source.max_distance == 1000.0


def test_audio_source_spatial_position():
    sound = make_sound()

    source = AudioSource(
        sound,
        position=(100, 50),
    )

    assert source.position_2d == (100.0, 50.0)

    source.position_2d = (-25, 75)

    assert source.position_2d == (-25.0, 75.0)


def test_audio_source_spatial_position_accepts_numeric_values():
    sound = make_sound()

    source = AudioSource(sound)

    source.position_2d = (10.5, -20.25)

    assert source.position_2d == (10.5, -20.25)


def test_audio_source_invalid_spatial_position():
    sound = make_sound()

    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source.position_2d = (1, 2, 3)


def test_audio_source_spatial_distances():
    sound = make_sound()

    source = AudioSource(
        sound,
        min_distance=5.0,
        max_distance=500.0,
    )

    assert source.min_distance == 5.0
    assert source.max_distance == 500.0


def test_audio_source_invalid_min_distance():
    sound = make_sound()

    with pytest.raises(ValueError):
        AudioSource(
            sound,
            min_distance=0.0,
        )


def test_audio_source_invalid_max_distance():
    sound = make_sound()

    with pytest.raises(ValueError):
        AudioSource(
            sound,
            max_distance=0.0,
        )


def test_audio_source_min_distance_cannot_exceed_max_distance():
    sound = make_sound()

    with pytest.raises(ValueError):
        AudioSource(
            sound,
            min_distance=100.0,
            max_distance=50.0,
        )


def test_audio_source_max_distance_cannot_be_below_min_distance():
    sound = make_sound()

    source = AudioSource(
        sound,
        min_distance=10.0,
        max_distance=100.0,
    )

    with pytest.raises(ValueError):
        source.max_distance = 5.0


def test_audio_source_min_distance_cannot_exceed_current_max_distance():
    sound = make_sound()

    source = AudioSource(
        sound,
        min_distance=10.0,
        max_distance=100.0,
    )

    with pytest.raises(ValueError):
        source.min_distance = 200.0


# ============================================================
# Fade
# ============================================================


def test_audio_source_fade_initial_state():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    assert source.fading is False
    assert source.volume == 1.0


def test_audio_source_fade_in():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.fade_in(1.0)

    assert source.fading is True
    assert source.get_effective_volume(AudioMixer()) == 0.0

    source._advance_fade(24000)

    assert source.get_effective_volume(AudioMixer()) == 0.5

    source._advance_fade(24000)

    assert source.fading is False
    assert source.volume == 1.0


def test_audio_source_fade_out():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.play()
    source.fade_out(1.0)

    assert source.fading is True
    assert source.get_effective_volume(AudioMixer()) == 1.0

    source._advance_fade(24000)

    assert source.get_effective_volume(AudioMixer()) == 0.5

    source._advance_fade(24000)

    assert source.fading is False
    assert source.volume == 0.0
    assert source.stopped is True


def test_audio_source_fade_in_zero_duration():
    sound = make_sound()

    source = AudioSource(sound)

    source.fade_in(0.0)

    assert source.fading is False
    assert source.volume == 1.0


def test_audio_source_fade_out_zero_duration():
    sound = make_sound()

    source = AudioSource(sound)

    source.play()
    source.fade_out(0.0)

    assert source.fading is False
    assert source.volume == 0.0
    assert source.stopped is True


def test_audio_source_fade_rejects_negative_duration():
    sound = make_sound()

    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source.fade_in(-1.0)

    with pytest.raises(ValueError):
        source.fade_out(-1.0)


def test_audio_source_fade_pause_does_not_advance():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.play()
    source.fade_in(1.0)

    source.pause()

    source._advance_fade(24000)

    assert source.get_effective_volume(AudioMixer()) == 0.5


def test_audio_source_fade_resume_continues():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.play()
    source.fade_in(1.0)

    source._advance_fade(24000)

    source.pause()
    source.resume()

    source._advance_fade(24000)

    assert source.fading is False
    assert source.volume == 1.0


def test_audio_source_stop_clears_fade():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.play()
    source.fade_out(1.0)

    assert source.fading is True

    source.stop()

    assert source.fading is False
    assert source.stopped is True
    assert source.position == 0


def test_audio_source_play_clears_fade():
    sound = make_sound(
        frames=48000,
        frequency=48000,
    )

    source = AudioSource(sound)

    source.play()
    source.fade_out(1.0)

    assert source.fading is True

    source.play()

    assert source.fading is False
    assert source.playing is True
    assert source.position == 0


# ============================================================
# AudioListener
# ============================================================


def test_audio_listener_default_position():
    listener = AudioListener()

    assert listener.position == (0.0, 0.0)
    assert listener.x == 0.0
    assert listener.y == 0.0


def test_audio_listener_position():
    listener = AudioListener()

    listener.position = (100, 200)

    assert listener.position == (100.0, 200.0)
    assert listener.x == 100.0
    assert listener.y == 200.0


def test_audio_listener_set_position():
    listener = AudioListener()

    listener.set_position(50, 75)

    assert listener.position == (50.0, 75.0)


def test_audio_listener_numeric_conversion():
    listener = AudioListener(
        position=(10, 20),
    )

    assert listener.position == (10.0, 20.0)


def test_audio_listener_invalid_position():
    listener = AudioListener()

    try:
        listener.position = (1, 2, 3)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError."
        )


# ============================================================
# Spatial Helpers
# ============================================================


def test_calculate_distance():
    assert calculate_distance(
        (0.0, 0.0),
        (3.0, 4.0),
    ) == 5.0


def test_calculate_distance_same_position():
    assert calculate_distance(
        (10.0, 20.0),
        (10.0, 20.0),
    ) == 0.0


def test_distance_attenuation_inside_min_distance():
    assert calculate_distance_attenuation(
        distance=5.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 1.0


def test_distance_attenuation_at_min_distance():
    assert calculate_distance_attenuation(
        distance=10.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 1.0


def test_distance_attenuation_middle():
    assert calculate_distance_attenuation(
        distance=55.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 0.5


def test_distance_attenuation_at_max_distance():
    assert calculate_distance_attenuation(
        distance=100.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 0.0


def test_distance_attenuation_beyond_max_distance():
    assert calculate_distance_attenuation(
        distance=500.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 0.0


def test_distance_attenuation_negative_distance():
    assert calculate_distance_attenuation(
        distance=-10.0,
        min_distance=10.0,
        max_distance=100.0,
    ) == 1.0


def test_distance_attenuation_invalid_min_distance():
    try:
        calculate_distance_attenuation(
            distance=10.0,
            min_distance=0.0,
            max_distance=100.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_distance_attenuation_invalid_range():
    try:
        calculate_distance_attenuation(
            distance=10.0,
            min_distance=100.0,
            max_distance=10.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_audio_source_spatial_volume_at_listener():
    source = AudioSource(
        make_sound(),
        position=(0, 0),
        min_distance=10,
        max_distance=100,
    )

    assert source.get_spatial_volume(
        (0, 0)
    ) == 1.0


def test_audio_source_spatial_volume_inside_min_distance():
    source = AudioSource(
        make_sound(),
        position=(5, 0),
        min_distance=10,
        max_distance=100,
    )

    assert source.get_spatial_volume(
        (0, 0)
    ) == 1.0


def test_audio_source_spatial_volume_middle():
    source = AudioSource(
        make_sound(),
        position=(55, 0),
        min_distance=10,
        max_distance=100,
    )

    assert source.get_spatial_volume(
        (0, 0)
    ) == 0.5


def test_audio_source_spatial_volume_at_max_distance():
    source = AudioSource(
        make_sound(),
        position=(100, 0),
        min_distance=10,
        max_distance=100,
    )

    assert source.get_spatial_volume(
        (0, 0)
    ) == 0.0


def test_stereo_pan_center():
    assert calculate_stereo_pan(
        (0.0, 100.0),
        (0.0, 0.0),
    ) == 0.0


def test_stereo_pan_left():
    assert calculate_stereo_pan(
        (-100.0, 0.0),
        (0.0, 0.0),
    ) == -1.0


def test_stereo_pan_right():
    assert calculate_stereo_pan(
        (100.0, 0.0),
        (0.0, 0.0),
    ) == 1.0


def test_stereo_pan_diagonal_left():
    assert calculate_stereo_pan(
        (-50.0, 50.0),
        (0.0, 0.0),
    ) == -0.7071067811865475


def test_stereo_pan_diagonal_right():
    assert calculate_stereo_pan(
        (50.0, 50.0),
        (0.0, 0.0),
    ) == 0.7071067811865475


def test_stereo_pan_same_position():
    assert calculate_stereo_pan(
        (0.0, 0.0),
        (0.0, 0.0),
    ) == 0.0


def test_stereo_pan_clamped():
    assert -1.0 <= calculate_stereo_pan(
        (1000.0, 1.0),
        (0.0, 0.0),
    ) <= 1.0


def test_audio_source_spatial_parameters_center():
    source = AudioSource(
        make_sound(),
        position=(0, 50),
        min_distance=10,
        max_distance=100,
    )

    volume, pan = source.get_spatial_parameters(
        (0, 0)
    )

    assert volume == 0.5555555555555556
    assert pan == 0.0


def test_audio_source_spatial_parameters_left():
    source = AudioSource(
        make_sound(),
        position=(-100, 0),
        min_distance=10,
        max_distance=200,
    )

    volume, pan = source.get_spatial_parameters(
        (0, 0)
    )

    assert volume == 0.5263157894736843
    assert pan == -1.0


def test_audio_source_spatial_parameters_right():
    source = AudioSource(
        make_sound(),
        position=(100, 0),
        min_distance=10,
        max_distance=200,
    )

    volume, pan = source.get_spatial_parameters(
        (0, 0)
    )

    assert volume == 0.5263157894736843
    assert pan == 1.0


def test_audio_source_spatial_parameters_diagonal():
    source = AudioSource(
        make_sound(),
        position=(50, 50),
        min_distance=10,
        max_distance=100,
    )

    volume, pan = source.get_spatial_parameters(
        (0, 0)
    )

    assert volume == 1.0 - (
        ((50.0 * 2**0.5) - 10.0)
        / 90.0
    )
    assert pan == 0.7071067811865475


def test_audio_player_has_listener():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    assert isinstance(
        player.listener,
        AudioListener,
    )


def test_audio_player_listener_position():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    player.listener.position = (100, 200)

    assert player.listener.position == (
        100.0,
        200.0,
    )


def test_audio_player_listener_set_position():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    player.listener.set_position(
        50,
        75,
    )

    assert player.listener.position == (
        50.0,
        75.0,
    )


def test_calculate_pan_gains_center():
    left, right = calculate_pan_gains(0.0)

    assert left == pytest.approx(1.0)
    assert right == pytest.approx(1.0)


def test_calculate_pan_gains_left():
    left, right = calculate_pan_gains(-1.0)

    assert left == pytest.approx(1.0)
    assert right == pytest.approx(0.0)


def test_calculate_pan_gains_right():
    left, right = calculate_pan_gains(1.0)

    assert left == pytest.approx(0.0)
    assert right == pytest.approx(1.0)


def test_calculate_pan_gains_invalid():
    with pytest.raises(ValueError):
        calculate_pan_gains(1.1)

    with pytest.raises(ValueError):
        calculate_pan_gains(-1.1)


def test_audio_player_spatial_source_left():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound()

    source = AudioSource(sound)
    source.position_2d = (-100.0, 0.0)

    player.listener.position = (0.0, 0.0)

    source.play()
    player.add(source)

    data = player.mix(1)

    samples = decode_pcm(
        AudioBuffer(
            data=data,
            frequency=48000,
            channels=2,
            bytes_per_sample=4,
        )
    )

    assert samples[0] > 0.0
    assert samples[1] == pytest.approx(0.0)


def test_audio_player_spatial_source_right():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound()

    source = AudioSource(sound)
    source.position_2d = (100.0, 0.0)

    player.listener.position = (0.0, 0.0)

    source.play()
    player.add(source)

    data = player.mix(1)

    samples = decode_pcm(
        AudioBuffer(
            data=data,
            frequency=48000,
            channels=2,
            bytes_per_sample=4,
        )
    )

    assert samples[0] == pytest.approx(0.0)
    assert samples[1] > 0.0


# ============================================================
# Pitch
# ============================================================


def test_audio_source_pitch_default():
    sound = make_test_sound()

    source = AudioSource(sound)

    assert source.pitch == pytest.approx(1.0)


def test_audio_source_pitch():
    sound = make_test_sound()

    source = AudioSource(
        sound,
        pitch=1.5,
    )

    assert source.pitch == pytest.approx(1.5)


def test_audio_source_pitch_setter():
    sound = make_test_sound()

    source = AudioSource(sound)

    source.pitch = 0.5

    assert source.pitch == pytest.approx(0.5)


def test_audio_source_pitch_invalid():
    sound = make_test_sound()

    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source.pitch = 0.0

    with pytest.raises(ValueError):
        source.pitch = -1.0


def test_audio_source_play_resets_playback_position():
    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(sound)

    source.seek(5)
    source.play()

    assert source.position == 0
    assert source._playback_position == pytest.approx(0.0)


def test_audio_source_seek_updates_playback_position():
    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(sound)

    source.seek(5)

    assert source.position == 5
    assert source._playback_position == pytest.approx(5.0)


def test_audio_source_seek_seconds_updates_playback_position():
    sound = make_test_sound(
        frames=48000,
    )

    source = AudioSource(sound)

    source.seek_seconds(0.5)

    assert source.position == 24000
    assert source._playback_position == pytest.approx(
        24000.0
    )


def test_audio_source_stop_resets_playback_position():
    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(sound)

    source.seek(5)
    source.stop()

    assert source.position == 0
    assert source._playback_position == pytest.approx(0.0)


def test_audio_player_pitch_one_advances_one_frame():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(
        sound,
        pitch=1.0,
    )

    source.play()
    player.add(source)

    player.mix(1)

    assert source.position == 1
    assert source._playback_position == pytest.approx(1.0)


def test_audio_player_pitch_two_advances_two_frames():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(
        sound,
        pitch=2.0,
    )

    source.play()
    player.add(source)

    player.mix(1)

    assert source.position == 2
    assert source._playback_position == pytest.approx(2.0)


def test_audio_player_pitch_half_advances_half_frame():
    mixer = AudioMixer()
    device = AudioDevice()

    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(
        sound,
        pitch=0.5,
    )

    source.play()
    player.add(source)

    player.mix(1)

    assert source.position == 0
    assert source._playback_position == pytest.approx(0.5)


def test_audio_player_pitch_two_uses_every_second_frame():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sound(
        frames=10,
    )

    source = AudioSource(
        sound,
        pitch=2.0,
    )

    source.play()
    player.add(source)

    player.mix(3)

    assert source.position == 6
    assert source._playback_position == pytest.approx(6.0)


def test_audio_player_pitch_half_interpolates_frames():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sequence_sound()

    source = AudioSource(
        sound,
        pitch=0.5,
    )

    source.play()
    player.add(source)

    data = player.mix(4)

    output = struct.unpack(
        "<8f",
        data,
    )

    assert output[0] == pytest.approx(1 / 32768)
    assert output[2] == pytest.approx(1.5 / 32768)
    assert output[4] == pytest.approx(2 / 32768)
    assert output[6] == pytest.approx(2.5 / 32768)


def test_audio_player_pitch_two_outputs_every_second_frame():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sequence_sound()

    source = AudioSource(
        sound,
        pitch=2.0,
    )

    source.play()
    player.add(source)

    data = player.mix(3)

    output = struct.unpack(
        "<6f",
        data,
    )

    assert output[0] == pytest.approx(1 / 32768)
    assert output[2] == pytest.approx(3 / 32768)
    assert output[4] == pytest.approx(5 / 32768)


def test_audio_player_pitch_half_interpolates_samples():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sequence_sound()

    source = AudioSource(
        sound,
        pitch=0.5,
    )

    source.play()
    player.add(source)

    data = player.mix(4)

    output = struct.unpack(
        "<8f",
        data,
    )

    assert output[0] == pytest.approx(1 / 32768)
    assert output[2] == pytest.approx(1.5 / 32768)
    assert output[4] == pytest.approx(2 / 32768)
    assert output[6] == pytest.approx(2.5 / 32768)


def test_audio_source_advance_playback():
    sound = make_test_sound(frames=10)
    source = AudioSource(sound)

    source._advance_playback(0.5)

    assert source.position == 0
    assert source._playback_position == pytest.approx(0.5)

    source._advance_playback(1.0)

    assert source.position == 1
    assert source._playback_position == pytest.approx(1.5)


def test_audio_source_advance_playback_invalid():
    sound = make_test_sound(frames=10)
    source = AudioSource(sound)

    with pytest.raises(ValueError):
        source._advance_playback(-1.0)


def test_audio_player_pitch_half_loops_with_fractional_position():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sequence_sound()

    source = AudioSource(
        sound,
        pitch=0.5,
        loop=True,
    )

    source.play()
    player.add(source)

    data = player.mix(8)

    output = struct.unpack(
        "<16f",
        data,
    )

    expected = [
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
    ]

    for index, value in enumerate(expected):
        assert output[index * 2] == pytest.approx(
            value / 32768
        )


def test_audio_player_pitch_loops_after_end():
    mixer = AudioMixer()
    device = AudioDevice()
    player = AudioPlayer(
        device=device,
        mixer=mixer,
    )

    sound = make_test_sequence_sound()

    source = AudioSource(
        sound,
        pitch=2.0,
        loop=True,
    )

    source.play()
    player.add(source)

    data = player.mix(6)

    output = struct.unpack(
        "<12f",
        data,
    )

    expected = [
        1.0,
        3.0,
        5.0,
        7.0,
        9.0,
        1.0,
    ]

    for index, value in enumerate(expected):
        assert output[index * 2] == pytest.approx(
            value / 32768
        )


# ============================================================
# AudioBus
# ============================================================


def test_audio_bus_default_state():
    bus = AudioBus("Master")

    assert bus.name == "Master"
    assert bus.volume == pytest.approx(1.0)
    assert bus.muted is False
    assert bus.effective_volume == pytest.approx(1.0)


def test_audio_bus_volume():
    bus = AudioBus("Music")

    bus.volume = 0.5

    assert bus.volume == pytest.approx(0.5)
    assert bus.effective_volume == pytest.approx(0.5)


def test_audio_bus_volume_constructor():
    bus = AudioBus(
        "SFX",
        volume=0.25,
    )

    assert bus.volume == pytest.approx(0.25)
    assert bus.effective_volume == pytest.approx(0.25)


def test_audio_bus_negative_volume():
    bus = AudioBus("SFX")

    with pytest.raises(ValueError):
        bus.volume = -1.0


def test_audio_bus_mute():
    bus = AudioBus(
        "Music",
        volume=0.75,
    )

    bus.mute()

    assert bus.muted is True
    assert bus.volume == pytest.approx(0.75)
    assert bus.effective_volume == pytest.approx(0.0)


def test_audio_bus_unmute():
    bus = AudioBus(
        "Music",
        volume=0.75,
        muted=True,
    )

    bus.unmute()

    assert bus.muted is False
    assert bus.effective_volume == pytest.approx(0.75)


def test_audio_bus_toggle_mute():
    bus = AudioBus("SFX")

    bus.toggle_mute()

    assert bus.muted is True
    assert bus.effective_volume == pytest.approx(0.0)

    bus.toggle_mute()

    assert bus.muted is False
    assert bus.effective_volume == pytest.approx(1.0)


def test_audio_bus_empty_name():
    with pytest.raises(ValueError):
        AudioBus("")


def test_audio_bus_mute_preserves_volume():
    bus = AudioBus(
        "Music",
        volume=0.4,
    )

    bus.mute()

    assert bus.volume == pytest.approx(0.4)

    bus.unmute()

    assert bus.effective_volume == pytest.approx(0.4)


# ============================================================
# AudioMixer Buses
# ============================================================


def test_audio_mixer_has_master_bus():
    mixer = AudioMixer()

    master = mixer.master

    assert isinstance(master, AudioBus)
    assert master.name == "Master"
    assert master.volume == pytest.approx(1.0)
    assert master.muted is False


def test_audio_mixer_buses_contains_master():
    mixer = AudioMixer()

    assert mixer.buses == (
        mixer.master,
    )


def test_audio_mixer_add_bus():
    mixer = AudioMixer()

    music = AudioBus(
        "Music",
        volume=0.75,
    )

    mixer.add_bus(music)

    assert mixer.get_bus("Music") is music
    assert mixer.buses == (
        mixer.master,
        music,
    )


def test_audio_mixer_add_multiple_buses():
    mixer = AudioMixer()

    music = AudioBus("Music")
    sfx = AudioBus("SFX")
    voice = AudioBus("Voice")

    mixer.add_bus(music)
    mixer.add_bus(sfx)
    mixer.add_bus(voice)

    assert mixer.buses == (
        mixer.master,
        music,
        sfx,
        voice,
    )


def test_audio_mixer_get_bus():
    mixer = AudioMixer()

    music = AudioBus("Music")

    mixer.add_bus(music)

    assert mixer.get_bus("Music") is music


def test_audio_mixer_get_unknown_bus():
    mixer = AudioMixer()

    with pytest.raises(KeyError):
        mixer.get_bus("Music")


def test_audio_mixer_duplicate_bus():
    mixer = AudioMixer()

    mixer.add_bus(
        AudioBus("Music")
    )

    with pytest.raises(ValueError):
        mixer.add_bus(
            AudioBus("Music")
        )


def test_audio_mixer_duplicate_master_bus():
    mixer = AudioMixer()

    with pytest.raises(ValueError):
        mixer.add_bus(
            AudioBus("Master")
        )


def test_audio_mixer_remove_bus():
    mixer = AudioMixer()

    mixer.add_bus(
        AudioBus("Music")
    )

    mixer.remove_bus("Music")

    with pytest.raises(KeyError):
        mixer.get_bus("Music")


def test_audio_mixer_cannot_remove_master():
    mixer = AudioMixer()

    with pytest.raises(ValueError):
        mixer.remove_bus("Master")


def test_audio_mixer_remove_unknown_bus():
    mixer = AudioMixer()

    with pytest.raises(KeyError):
        mixer.remove_bus("Music")


# ============================================================
# AudioSource Buses
# ============================================================


def test_audio_source_default_bus():
    sound = make_test_sound()

    source = AudioSource(sound)

    assert source.bus is None


def test_audio_source_bus_constructor():
    sound = make_test_sound()
    bus = AudioBus("Music")

    source = AudioSource(
        sound,
        bus=bus,
    )

    assert source.bus is bus


def test_audio_source_bus_setter():
    sound = make_test_sound()
    bus = AudioBus("Music")

    source = AudioSource(sound)

    source.bus = bus

    assert source.bus is bus


def test_audio_source_bus_can_be_cleared():
    sound = make_test_sound()
    bus = AudioBus("Music")

    source = AudioSource(
        sound,
        bus=bus,
    )

    source.bus = None

    assert source.bus is None


def test_audio_source_effective_volume_includes_bus():
    sound = make_test_sound()
    mixer = AudioMixer()

    bus = AudioBus("Music", volume=0.5)

    source = AudioSource(
        sound,
        channel=AudioChannel.SFX,
        volume=0.8,
        bus=bus,
    )

    mixer.set_volume(AudioChannel.SFX, 0.5)

    assert source.get_effective_volume(mixer) == 0.2


def test_audio_source_effective_volume_respects_bus_mute():
    sound = make_test_sound()
    mixer = AudioMixer()

    bus = AudioBus("Music", volume=0.5)
    bus.mute()

    source = AudioSource(
        sound,
        volume=0.8,
        bus=bus,
    )

    assert source.get_effective_volume(mixer) == 0.0


def test_audio_source_effective_volume_includes_master_bus():
    sound = make_test_sound()
    mixer = AudioMixer()

    mixer.master.volume = 0.5

    source = AudioSource(
        sound,
        volume=0.8,
    )

    assert source.get_effective_volume(mixer) == 0.4


def test_audio_source_effective_volume_respects_master_bus_mute():
    sound = make_test_sound()
    mixer = AudioMixer()

    mixer.master.mute()

    source = AudioSource(
        sound,
        volume=0.8,
    )

    assert source.get_effective_volume(mixer) == 0.0


def test_audio_source_without_bus_still_uses_master_bus():
    sound = make_test_sound()
    mixer = AudioMixer()

    mixer.master.volume = 0.25

    source = AudioSource(
        sound,
        volume=0.8,
        bus=None,
    )

    assert source.get_effective_volume(mixer) == 0.2


# ============================================================
# MusicPlayer Buses
# ============================================================


def test_music_player_play_uses_music_bus():
    audio = AudioSystem()
    sound = make_test_sound()

    audio.music.play(sound)

    assert audio.music.source is not None
    assert audio.music.source.bus is audio.mixer.get_bus("Music")


def test_music_player_previous_uses_music_bus():
    audio = AudioSystem()

    first = make_test_sound()
    second = make_test_sound()

    audio.music.play(first)
    audio.music.play(second)

    assert audio.music.previous() is True
    assert audio.music.source is not None
    assert audio.music.source.bus is audio.mixer.get_bus("Music")


# ============================================================
# Audio Cache / AudioSystem Loading
# ============================================================


def test_audio_system_load_uses_cache(monkeypatch, tmp_path):
    audio = AudioSystem()

    path = tmp_path / "test.wav"
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

    assert audio.load(path) is sound
    assert audio.load(path) is sound
    assert calls == 1


def test_audio_system_unload_removes_cached_sound(
    monkeypatch,
    tmp_path,
):
    audio = AudioSystem()

    path = tmp_path / "test.wav"
    sound = object()

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        lambda self, load_path: sound,
    )

    audio.load(path)

    assert audio.cache.get(path) is sound

    audio.unload(path)

    assert audio.cache.get(path) is None


def test_audio_system_clear_cache(
    monkeypatch,
    tmp_path,
):
    audio = AudioSystem()

    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        lambda self, load_path: object(),
    )

    audio.load(first)
    audio.load(second)

    assert len(audio.cache.sounds) == 2

    audio.clear_cache()

    assert audio.cache.sounds == ()


# ============================================================
# AudioPlayer lifecycle / fade integration
# ============================================================


def test_audio_player_stops_source_when_sound_finishes():
    sound = make_test_sequence_sound()
    source = AudioSource(sound)

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)

    player.mix(10)

    assert source.stopped
    assert source.position == sound.buffer.sample_count


def test_audio_player_loops_source_when_sound_finishes():
    sound = make_test_sequence_sound()
    source = AudioSource(
        sound,
        loop=True,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)

    player.mix(12)

    assert source.playing
    assert source.position < sound.buffer.sample_count


def test_audio_player_finishes_with_pitch():
    sound = make_test_sequence_sound()
    source = AudioSource(
        sound,
        pitch=2.0,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)

    player.mix(10)

    assert source.stopped
    assert source.position == sound.buffer.sample_count


def test_audio_player_empty_sound_stops_source():
    buffer = AudioBuffer(
        data=b"",
        frequency=48_000,
        channels=1,
        bytes_per_sample=2,
    )

    sound = Sound(buffer=buffer)
    source = AudioSource(sound)

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)

    player.mix(1)

    assert source.stopped


def test_audio_player_fade_out_progresses_during_mix():
    sound = make_test_sound(
        value=16384,
        frames=48000,
    )
    source = AudioSource(sound)

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)
    source.fade_out(1.0)

    player.mix(24000)

    assert source.fading is True
    assert source.get_effective_volume(mixer) == pytest.approx(0.5)


def test_audio_player_fade_with_pitch():
    sound = make_test_sound(
        value=16384,
        frames=48000,
    )
    source = AudioSource(
        sound,
        pitch=2.0,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)
    source.fade_out(1.0)

    player.mix(12000)

    assert source.fading is True
    assert source.get_effective_volume(mixer) == pytest.approx(0.75)
    assert source.position == 24000


def test_audio_player_fade_with_loop():
    sound = make_test_sequence_sound()
    source = AudioSource(
        sound,
        loop=True,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)
    source.fade_out(1.0)

    player.mix(10)

    assert source.playing is True
    assert source.fading is True
    assert source.get_effective_volume(mixer) == pytest.approx(
        1.0 - (10 / 48000)
    )


def test_audio_player_fade_out_stops_at_end():
    sound = make_test_sound(
        value=16384,
        frames=48000,
    )
    source = AudioSource(sound)

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.play(source)
    source.fade_out(2.0)

    player.mix(48000)

    assert source.stopped is True
    assert source.fading is False
    assert source.volume == 0.0
    assert source.position == sound.buffer.sample_count

def test_audio_player_spatial_pan_changes_stereo_output():
    sound = make_test_sound(
        value=16384,
        frames=1,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.listener.position = (0.0, 0.0)

    left_source = AudioSource(
        sound,
        position=(-10.0, 0.0),
    )

    right_source = AudioSource(
        sound,
        position=(10.0, 0.0),
    )

    player.play(left_source)
    left_output = player.mix(1)

    player.stop(left_source)

    player.play(right_source)
    right_output = player.mix(1)

    left_samples = struct.unpack("<2f", left_output)
    right_samples = struct.unpack("<2f", right_output)

    assert left_samples[0] > left_samples[1]
    assert right_samples[1] > right_samples[0]

def test_audio_player_spatial_distance_attenuation():
    sound = make_test_sound(
        value=16384,
        frames=10,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.listener.position = (0.0, 0.0)

    near_source = AudioSource(
        sound,
        position=(1.0, 0.0),
        min_distance=1.0,
        max_distance=10.0,
    )

    far_source = AudioSource(
        sound,
        position=(5.0, 0.0),
        min_distance=1.0,
        max_distance=10.0,
    )

    player.play(near_source)
    near_output = player.mix(1)

    player.stop(near_source)

    player.play(far_source)
    far_output = player.mix(1)

    near_samples = struct.unpack("<2f", near_output)
    far_samples = struct.unpack("<2f", far_output)

    near_volume = abs(near_samples[1])
    far_volume = abs(far_samples[1])

    assert near_volume > far_volume

def test_audio_player_spatial_attenuation_preserves_pan():
    sound = make_test_sound(
        value=16384,
        frames=10,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.listener.position = (0.0, 0.0)

    source = AudioSource(
        sound,
        position=(5.0, 5.0),
        min_distance=1.0,
        max_distance=20.0,
    )

    player.play(source)

    output = player.mix(1)

    left, right = struct.unpack("<2f", output)

    assert left > 0.0
    assert right > 0.0
    assert right > left

def test_audio_player_spatial_center_source():
    sound = make_test_sound(
        value=16384,
        frames=10,
    )

    device = AudioDevice()
    mixer = AudioMixer()
    player = AudioPlayer(device, mixer)

    player.listener.position = (0.0, 0.0)

    source = AudioSource(
        sound,
        position=(0.0, 0.0),
        min_distance=1.0,
        max_distance=10.0,
    )

    player.play(source)

    output = player.mix(1)

    left, right = struct.unpack("<2f", output)

    assert left == pytest.approx(right)
    assert left > 0.0