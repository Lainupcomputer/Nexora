
from __future__ import annotations

import math
import struct
import wave


import pytest

pytestmark = pytest.mark.audio
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
    device = AudioDevice()
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


def test_audio_system_load_uses_cache(
    monkeypatch,
    tmp_path,
):
    audio = AudioSystem()

    path = (
        tmp_path
        / "test.wav"
    )

    buffer = object()

    calls = 0

    def fake_load(
        self,
        load_path,
    ):
        nonlocal calls

        calls += 1

        assert (
            load_path
            == path.resolve()
        )

        return buffer

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        fake_load,
    )

    # ----------------------------------------------------------
    # First load
    # ----------------------------------------------------------

    sound = audio.load(
        path
    )

    assert (
        sound.buffer
        is buffer
    )

    assert (
        sound.path
        == path.resolve()
    )

    assert (
        calls
        == 1
    )

    # ----------------------------------------------------------
    # Second load must use cache
    # ----------------------------------------------------------

    cached = audio.load(
        path
    )

    assert (
        cached
        is sound
    )

    assert (
        calls
        == 1
    )


def test_audio_system_unload_removes_cached_sound(
    monkeypatch,
    tmp_path,
):
    audio = AudioSystem()

    path = (
        tmp_path
        / "test.wav"
    )

    buffer = object()

    monkeypatch.setattr(
        "nexora.audio.cache.WavLoader.load",
        lambda self, load_path: buffer,
    )

    # ----------------------------------------------------------
    # Load
    # ----------------------------------------------------------

    sound = audio.load(
        path
    )

    assert (
        sound.buffer
        is buffer
    )

    assert (
        audio.cache.get(
            path
        )
        is sound
    )

    # ----------------------------------------------------------
    # Unload
    # ----------------------------------------------------------

    audio.unload(
        path
    )

    assert (
        audio.cache.get(
            path
        )
        is None
    )
    

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
<<<<<<< Updated upstream
    assert left > 0.0
=======
    assert left > 0.0

# ============================================================
# Bus DSP routing
# ============================================================


def test_audio_bus_effect_stack_order():
    bus = AudioBus("Test")
    first = GainEffect(0.5)
    second = GainEffect(0.25)

    bus.add_effect(first)
    bus.add_effect(second)

    assert bus.effects == (first, second)

    bus.remove_effect(first)
    assert bus.effects == (second,)


def test_audio_player_processes_child_bus_before_parent(tmp_path):
    player = create_audio_player()
    player.mixer.create_bus("Weapons", parent="SFX")
    player.mixer.get_bus("Weapons").add_effect(GainEffect(0.5))
    player.mixer.get_bus("SFX").add_effect(GainEffect(0.5))

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=16384,
    )
    source = AudioSource(sound, bus="Weapons")
    player.play(source)

    data = player.mix(1)
    left, right = struct.unpack("<2f", data)
    expected = (16384 / 32768) * 0.5 * 0.5
    assert math.isclose(left, expected, rel_tol=1e-5)
    assert math.isclose(right, expected, rel_tol=1e-5)


def test_audio_bus_volume_applied_once_per_hierarchy_level(tmp_path):
    player = create_audio_player()
    weapons = player.mixer.create_bus("Weapons", parent="SFX", volume=0.5)
    player.mixer.get_bus("SFX").volume = 0.5
    player.mixer.master.volume = 0.5

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=16384,
    )
    source = AudioSource(sound, bus=weapons)
    player.play(source)

    data = player.mix(1)
    left, right = struct.unpack("<2f", data)
    expected = (16384 / 32768) * 0.5 * 0.5 * 0.5
    assert math.isclose(left, expected, rel_tol=1e-5)
    assert math.isclose(right, expected, rel_tol=1e-5)


def test_audio_bus_limiter_runs_before_parent(tmp_path):
    player = create_audio_player()
    hot = player.mixer.create_bus("Hot", parent="Master")
    hot.add_effect(LimiterEffect(0.25))

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=32767,
    )
    player.play(AudioSource(sound, bus="Hot"))

    data = player.mix(1)
    left, right = struct.unpack("<2f", data)
    assert math.isclose(left, 0.25, rel_tol=1e-5)
    assert math.isclose(right, 0.25, rel_tol=1e-5)

# ============================================================
# Mixer controls: pan / solo / metering
# ============================================================


def test_audio_bus_pan_validation():
    bus = AudioBus("Music")
    bus.pan = -1.0
    assert bus.pan == -1.0
    bus.pan = 1.0
    assert bus.pan == 1.0

    with pytest.raises(ValueError):
        bus.pan = -1.01
    with pytest.raises(ValueError):
        bus.pan = 1.01


def test_audio_player_applies_bus_pan(tmp_path):
    player = create_audio_player()
    player.mixer.get_bus("SFX").pan = 1.0

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=16384,
    )
    player.play(AudioSource(sound, bus="SFX"))

    data = player.mix(1)
    left, right = struct.unpack("<2f", data)
    assert left == pytest.approx(0.0, abs=1e-7)
    assert right == pytest.approx(16384 / 32768, rel=1e-5)


def test_audio_mixer_solo_keeps_selected_branch_audible(tmp_path):
    player = create_audio_player()
    player.mixer.get_bus("SFX").solo = True

    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=8192,
    )
    player.play(AudioSource(sound, bus="SFX"))
    player.play(AudioSource(sound, bus="Music"))

    data = player.mix(1)
    left, right = struct.unpack("<2f", data)
    expected = 8192 / 32768
    assert left == pytest.approx(expected, rel=1e-5)
    assert right == pytest.approx(expected, rel=1e-5)


def test_audio_mixer_solo_parent_keeps_child_audible():
    mixer = AudioMixer()
    weapons = mixer.create_bus("Weapons", parent="SFX")
    mixer.get_bus("SFX").solo = True

    assert mixer.is_bus_audible(weapons) is True
    assert mixer.is_bus_audible(mixer.get_bus("SFX")) is True
    assert mixer.is_bus_audible(mixer.master) is True
    assert mixer.is_bus_audible(mixer.get_bus("Music")) is False


def test_audio_bus_peak_and_rms_metering(tmp_path):
    player = create_audio_player()
    sound = create_sound(
        tmp_path,
        channels=1,
        frames=4,
        value=16384,
    )
    player.play(AudioSource(sound, bus="SFX"))

    player.mix(2)
    bus = player.mixer.get_bus("SFX")
    expected = 16384 / 32768

    assert bus.peak[0] == pytest.approx(expected, rel=1e-5)
    assert bus.peak[1] == pytest.approx(expected, rel=1e-5)
    assert bus.rms[0] == pytest.approx(expected, rel=1e-5)
    assert bus.rms[1] == pytest.approx(expected, rel=1e-5)

    bus.mute()
    player.mix(1)
    assert bus.peak == (0.0, 0.0)
    assert bus.rms == (0.0, 0.0)


def test_audio_bus_ids_survive_rename():
    mixer = AudioMixer()
    bus = mixer.create_bus("Weapons", parent="SFX")
    bus_id = bus.id

    mixer.rename_bus("Weapons", "Guns")

    assert mixer.get_bus("Guns") is bus
    assert mixer.get_bus_by_id(bus_id) is bus
    assert bus.id == bus_id
    with pytest.raises(KeyError):
        mixer.get_bus("Weapons")


def test_audio_send_rejects_feedback_cycle():
    mixer = AudioMixer()
    mixer.create_bus("Weapons", parent="SFX")
    mixer.create_bus("Reverb", parent="Master")
    mixer.add_send("Weapons", "Reverb")

    with pytest.raises(ValueError, match="feedback cycles"):
        mixer.add_send("Reverb", "Weapons")


def test_audio_player_post_fader_send(tmp_path):
    player = create_audio_player()
    player.mixer.get_bus("SFX").volume = 0.5
    player.mixer.create_bus("Reverb", parent="Master", volume=0.5)
    player.mixer.add_send("SFX", "Reverb", amount=1.0, pre_fader=False)
    sound = create_sound(tmp_path, channels=1, frames=4, value=16384)
    player.play(AudioSource(sound, bus="SFX"))

    left, right = struct.unpack("<2f", player.mix(1))
    # source=.5; direct=.25; post send=.25 * return .5=.125
    assert left == pytest.approx(0.375, rel=1e-5)
    assert right == pytest.approx(0.375, rel=1e-5)


def test_audio_player_pre_fader_send(tmp_path):
    player = create_audio_player()
    player.mixer.get_bus("SFX").volume = 0.5
    player.mixer.create_bus("Reverb", parent="Master", volume=0.5)
    player.mixer.add_send("SFX", "Reverb", amount=1.0, pre_fader=True)
    sound = create_sound(tmp_path, channels=1, frames=4, value=16384)
    player.play(AudioSource(sound, bus="SFX"))

    left, right = struct.unpack("<2f", player.mix(1))
    # source=.5; direct=.25; pre send=.5 * return .5=.25
    assert left == pytest.approx(0.5, rel=1e-5)
    assert right == pytest.approx(0.5, rel=1e-5)


def test_audio_effect_wet_dry_and_bypass(tmp_path):
    player = create_audio_player()
    effect = GainEffect(0.0, wet=0.5)
    player.mixer.get_bus("SFX").add_effect(effect)

    # One frame keeps the two assertions isolated: after each mix the
    # one-shot source is naturally finished and pruned. Using a longer sound
    # here would intentionally overlap both sources on the second assertion,
    # because AudioPlayer supports additive polyphonic playback.
    sound = create_sound(tmp_path, channels=1, frames=1, value=16384)
    player.play(AudioSource(sound, bus="SFX"))

    left, _ = struct.unpack("<2f", player.mix(1))
    assert left == pytest.approx(0.25, rel=1e-5)

    effect.bypassed = True
    player.play(AudioSource(sound, bus="SFX"))
    left, _ = struct.unpack("<2f", player.mix(1))
    assert left == pytest.approx(0.5, rel=1e-5)


def test_audio_bus_effect_chain_bypass(tmp_path):
    player = create_audio_player()
    bus = player.mixer.get_bus("SFX")
    bus.add_effect(GainEffect(0.0))
    bus.effects_bypassed = True
    sound = create_sound(tmp_path, channels=1, frames=4, value=16384)
    player.play(AudioSource(sound, bus="SFX"))

    left, _ = struct.unpack("<2f", player.mix(1))
    assert left == pytest.approx(0.5, rel=1e-5)


def test_audio_effect_runtime_parameters():
    effect = GainEffect(1.0)
    effect.set_parameter("gain", 0.25)
    effect.set_parameter("wet", 0.75)

    assert effect.get_parameter("gain") == pytest.approx(0.25)
    assert effect.get_parameter("wet") == pytest.approx(0.75)
    with pytest.raises(KeyError):
        effect.set_parameter("does_not_exist", 1)


def test_audio_master_headroom_and_limiter(tmp_path):
    player = create_audio_player()
    player.mixer.headroom_db = -6.0
    player.mixer.enable_master_limiter(0.2)
    sound = create_sound(tmp_path, channels=1, frames=4, value=16384)
    player.play(AudioSource(sound, bus="Master"))

    left, right = struct.unpack("<2f", player.mix(1))
    assert left == pytest.approx(0.2, rel=1e-5)
    assert right == pytest.approx(0.2, rel=1e-5)


def test_audio_extended_metering_peak_hold_clip_and_dbfs():
    bus = AudioBus("Test")
    block = np.array([[0.5, -1.1], [-0.25, 0.25]], dtype=np.float32)
    bus.update_meter(block)

    assert bus.peak == pytest.approx((0.5, 1.1))
    assert bus.peak_hold == pytest.approx((0.5, 1.1))
    assert bus.clipped is True
    assert bus.peak_dbfs[0] == pytest.approx(20.0 * math.log10(0.5))

    bus.update_meter(np.array([[0.1, 0.1]], dtype=np.float32))
    assert bus.peak_hold == pytest.approx((0.5, 1.1))
    bus.clear_peak_hold()
    assert bus.peak_hold == (0.0, 0.0)
    assert bus.clipped is False


def test_audio_solo_keeps_send_return_audible():
    mixer = AudioMixer()
    mixer.create_bus("Weapons", parent="SFX")
    reverb = mixer.create_bus("Reverb", parent="Master")
    mixer.add_send("Weapons", "Reverb")
    mixer.get_bus("Weapons").solo = True

    assert mixer.is_bus_audible(reverb) is True
    assert mixer.is_bus_audible(mixer.get_bus("Music")) is False


def test_audio_mixer_snapshot_restores_topology_sends_and_effects():
    mixer = AudioMixer()
    weapons = mixer.create_bus("Weapons", parent="SFX", volume=0.7, pan=-0.2)
    weapons.add_effect(GainEffect(0.5, wet=0.4))
    mixer.create_bus("Reverb", parent="Master", volume=0.8)
    mixer.add_send("Weapons", "Reverb", amount=0.25, pre_fader=True)
    mixer.headroom_db = -3.0
    mixer.enable_master_limiter(0.9)
    snapshot = mixer.create_snapshot()

    mixer.rename_bus("Weapons", "Changed")
    mixer.get_bus("Changed").volume = 0.1
    mixer.headroom_db = 0.0
    mixer.restore_snapshot(snapshot)

    restored = mixer.get_bus("Weapons")
    assert restored.id == weapons.id
    assert restored.volume == pytest.approx(0.7)
    assert restored.pan == pytest.approx(-0.2)
    assert isinstance(restored.effects[0], GainEffect)
    assert restored.effects[0].gain == pytest.approx(0.5)
    assert restored.effects[0].wet == pytest.approx(0.4)
    assert len(mixer.sends) == 1
    assert mixer.sends[0].amount == pytest.approx(0.25)
    assert mixer.sends[0].pre_fader is True
    assert mixer.headroom_db == pytest.approx(-3.0)
    assert mixer.master_limiter is not None
    assert mixer.master_limiter.threshold == pytest.approx(0.9)


# ============================================================
# Built-in DSP effects
# ============================================================


def test_lowpass_filter_attenuates_high_frequency_signal():
    effect = LowPassFilterEffect(cutoff_hz=500.0)
    signal = np.ones((4096, 2), dtype=np.float32)
    signal[1::2] *= -1.0
    before = float(np.sqrt(np.mean(signal * signal)))
    effect.process(signal, sample_rate=48_000, channels=2)
    after = float(np.sqrt(np.mean(signal * signal)))
    assert after < before * 0.2


def test_highpass_filter_rejects_dc_after_settling():
    effect = HighPassFilterEffect(cutoff_hz=200.0)
    signal = np.ones((8192, 2), dtype=np.float32)
    effect.process(signal, sample_rate=48_000, channels=2)
    assert float(np.max(np.abs(signal[-1024:]))) < 0.01


def test_parametric_eq_zero_db_is_neutral():
    effect = ParametricEQEffect(frequency_hz=1_000.0, gain_db=0.0, q=1.0)
    source = np.linspace(-0.8, 0.8, 512, dtype=np.float32)
    signal = np.column_stack((source, source)).astype(np.float32)
    expected = signal.copy()
    effect.process(signal, sample_rate=48_000, channels=2)
    assert np.allclose(signal, expected, atol=1e-5)


def test_compressor_reduces_hot_signal():
    effect = CompressorEffect(
        threshold_db=-12.0,
        ratio=8.0,
        attack_ms=0.0,
        release_ms=100.0,
    )
    signal = np.full((256, 2), 0.9, dtype=np.float32)
    effect.process(signal, sample_rate=48_000, channels=2)
    assert float(np.max(np.abs(signal))) < 0.5
    assert effect.gain_reduction_db < 0.0


def test_delay_effect_keeps_state_between_blocks():
    effect = DelayEffect(delay_seconds=4 / 48_000, feedback=0.0, wet=1.0)
    first = np.zeros((4, 2), dtype=np.float32)
    first[0] = 1.0
    effect.process(first, sample_rate=48_000, channels=2)
    assert np.allclose(first, 0.0)

    second = np.zeros((4, 2), dtype=np.float32)
    effect.process(second, sample_rate=48_000, channels=2)
    assert np.allclose(second[0], 1.0)
    assert np.allclose(second[1:], 0.0)


def test_reverb_effect_produces_tail_after_impulse():
    effect = ReverbEffect(room_size=0.2, damping=0.2, decay=0.7, wet=1.0)
    impulse = np.zeros((1, 2), dtype=np.float32)
    impulse[0] = 1.0
    effect.process(impulse, sample_rate=48_000, channels=2)
    assert np.allclose(impulse, 0.0)

    tail = np.zeros((3000, 2), dtype=np.float32)
    effect.process(tail, sample_rate=48_000, channels=2)
    assert float(np.max(np.abs(tail))) > 0.0


def test_dsp_effect_state_roundtrip_through_snapshot():
    mixer = AudioMixer()
    bus = mixer.get_bus("SFX")
    bus.add_effect(LowPassFilterEffect(4500.0, q=0.8, wet=0.7))
    bus.add_effect(CompressorEffect(-18.0, 3.0, 5.0, 150.0, 2.0))
    bus.add_effect(DelayEffect(0.15, 0.4, wet=0.3))

    snapshot = mixer.create_snapshot()
    mixer.restore_snapshot(snapshot)

    effects = mixer.get_bus("SFX").effects
    assert isinstance(effects[0], LowPassFilterEffect)
    assert effects[0].cutoff_hz == pytest.approx(4500.0)
    assert effects[0].wet == pytest.approx(0.7)
    assert isinstance(effects[1], CompressorEffect)
    assert effects[1].ratio == pytest.approx(3.0)
    assert isinstance(effects[2], DelayEffect)
    assert effects[2].feedback == pytest.approx(0.4)


def test_distortion_soft_saturation_and_hard_clip():
    soft = DistortionEffect(drive=4.0, mode="soft")
    signal = np.array([[0.5, -0.5]], dtype=np.float32)
    soft.process(signal, sample_rate=48_000, channels=2)
    assert 0.5 < float(signal[0, 0]) < 1.0
    assert -1.0 < float(signal[0, 1]) < -0.5

    hard = DistortionEffect(drive=4.0, mode="hard")
    signal = np.array([[0.5, -0.5]], dtype=np.float32)
    hard.process(signal, sample_rate=48_000, channels=2)
    assert np.allclose(signal, [[1.0, -1.0]])


def test_noise_gate_closes_below_threshold_and_opens_above_it():
    gate = NoiseGateEffect(
        threshold_db=-20.0,
        attack_ms=0.0,
        hold_ms=0.0,
        release_ms=0.0,
    )
    quiet = np.full((8, 2), 0.01, dtype=np.float32)
    gate.process(quiet, sample_rate=48_000, channels=2)
    assert np.allclose(quiet, 0.0)

    loud = np.full((8, 2), 0.5, dtype=np.float32)
    gate.process(loud, sample_rate=48_000, channels=2)
    assert np.allclose(loud, 0.5)
    assert gate.gain == pytest.approx(1.0)


def test_noise_gate_hold_keeps_gate_open_across_samples():
    gate = NoiseGateEffect(
        threshold_db=-20.0,
        attack_ms=0.0,
        hold_ms=2.0,
        release_ms=0.0,
    )
    first = np.array([[0.5, 0.5]], dtype=np.float32)
    gate.process(first, sample_rate=1_000, channels=2)
    assert np.allclose(first, 0.5)

    # 2 ms at 1 kHz = two held samples after the trigger.
    held = np.full((2, 2), 0.01, dtype=np.float32)
    gate.process(held, sample_rate=1_000, channels=2)
    assert np.allclose(held, 0.01)

    closed = np.full((1, 2), 0.01, dtype=np.float32)
    gate.process(closed, sample_rate=1_000, channels=2)
    assert np.allclose(closed, 0.0)


def test_stereo_width_zero_collapses_to_mono_and_one_is_neutral():
    source = np.array([[1.0, 0.0], [0.25, -0.25]], dtype=np.float32)
    effect = StereoWidthEffect(width=0.0)
    signal = source.copy()
    effect.process(signal, sample_rate=48_000, channels=2)
    assert np.allclose(signal[:, 0], signal[:, 1])

    effect.width = 1.0
    signal = source.copy()
    effect.process(signal, sample_rate=48_000, channels=2)
    assert np.allclose(signal, source)


def test_new_dsp_effects_roundtrip_through_snapshot():
    mixer = AudioMixer()
    bus = mixer.get_bus("SFX")
    bus.add_effect(DistortionEffect(3.0, -2.0, "hard", wet=0.6))
    bus.add_effect(NoiseGateEffect(-35.0, 1.0, 20.0, 100.0))
    bus.add_effect(StereoWidthEffect(1.4, wet=0.8))

    snapshot = mixer.create_snapshot()
    mixer.restore_snapshot(snapshot)
    effects = mixer.get_bus("SFX").effects

    assert isinstance(effects[0], DistortionEffect)
    assert effects[0].drive == pytest.approx(3.0)
    assert effects[0].output_gain_db == pytest.approx(-2.0)
    assert effects[0].mode == "hard"
    assert effects[0].wet == pytest.approx(0.6)
    assert isinstance(effects[1], NoiseGateEffect)
    assert effects[1].threshold_db == pytest.approx(-35.0)
    assert effects[1].hold_ms == pytest.approx(20.0)
    assert isinstance(effects[2], StereoWidthEffect)
    assert effects[2].width == pytest.approx(1.4)
    assert effects[2].wet == pytest.approx(0.8)



# ============================================================
# DSP preset system
# ============================================================


def test_audio_preset_registry_contains_builtins():
    registry = AudioPresetRegistry()
    assert registry.has("Radio")
    assert registry.has("Telephone")
    assert registry.has("Underwater")
    assert registry.has("Cave")
    assert registry.has("Hall")
    assert registry.has("Distorted Speaker")
    assert registry.has("Wide Music")


def test_audio_preset_apply_creates_fresh_effect_instances():
    registry = AudioPresetRegistry(include_builtins=False)
    registry.register_effects(
        "Test",
        (LowPassFilterEffect(2500.0), DelayEffect(0.1, 0.2, wet=0.3)),
    )
    first = AudioBus("First")
    second = AudioBus("Second")

    first_effects = registry.apply("Test", first)
    second_effects = registry.apply("Test", second)

    assert len(first.effects) == 2
    assert len(second.effects) == 2
    assert first_effects[0] is not second_effects[0]
    assert first_effects[1] is not second_effects[1]


def test_audio_preset_apply_replace_and_append():
    registry = AudioPresetRegistry(include_builtins=False)
    registry.register_effects("Gain", (GainEffect(0.5),))
    bus = AudioBus("Bus")
    bus.add_effect(LimiterEffect(0.9))

    registry.apply("Gain", bus, replace=False)
    assert isinstance(bus.effects[0], LimiterEffect)
    assert isinstance(bus.effects[1], GainEffect)

    registry.apply("Gain", bus, replace=True)
    assert len(bus.effects) == 1
    assert isinstance(bus.effects[0], GainEffect)


def test_audio_preset_capture_bus_roundtrip():
    registry = AudioPresetRegistry(include_builtins=False)
    bus = AudioBus("Voice")
    bus.add_effect(HighPassFilterEffect(300.0, wet=0.8))
    bus.add_effect(CompressorEffect(-18.0, 4.0, 5.0, 100.0, 1.0))

    preset = registry.capture_bus("Voice FX", bus)
    target = AudioBus("Target")
    registry.apply("Voice FX", target)

    assert preset.name == "Voice FX"
    assert isinstance(target.effects[0], HighPassFilterEffect)
    assert target.effects[0].cutoff_hz == pytest.approx(300.0)
    assert target.effects[0].wet == pytest.approx(0.8)
    assert isinstance(target.effects[1], CompressorEffect)
    assert target.effects[1].ratio == pytest.approx(4.0)


def test_audio_preset_data_file_save_load(tmp_path):
    registry = AudioPresetRegistry(include_builtins=False)
    registry.register_effects(
        "My Preset",
        (DistortionEffect(2.5, -2.0, "soft", wet=0.4), StereoWidthEffect(1.2)),
        description="Custom test preset",
    )
    path = tmp_path / "my_preset.npreset"
    registry.save("My Preset", path)

    loaded_registry = AudioPresetRegistry(include_builtins=False)
    preset = loaded_registry.load(path)

    assert preset.name == "My Preset"
    assert preset.description == "Custom test preset"
    bus = AudioBus("Target")
    loaded_registry.apply("My Preset", bus)
    assert isinstance(bus.effects[0], DistortionEffect)
    assert bus.effects[0].drive == pytest.approx(2.5)
    assert bus.effects[0].wet == pytest.approx(0.4)
    assert isinstance(bus.effects[1], StereoWidthEffect)
    assert bus.effects[1].width == pytest.approx(1.2)


def test_audio_preset_registration_is_case_insensitive():
    registry = AudioPresetRegistry(include_builtins=False)
    registry.register(AudioPreset.from_effects("Radio FX", (GainEffect(0.8),)))
    assert registry.get("radio fx").name == "Radio FX"
    with pytest.raises(ValueError):
        registry.register(AudioPreset.from_effects("RADIO FX", (GainEffect(1.0),)))
>>>>>>> Stashed changes
