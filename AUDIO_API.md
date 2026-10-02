# Nexora Engine — Audio API

This document is the practical reference for Nexora's audio system. It is intended for game projects that use the engine as a library and covers the public audio workflow from loading a WAV file to advanced mixer routing, DSP chains, presets, metering, streaming, and runtime configuration.

> [!NOTE]
> Nexora is still in active development. The API documented here reflects the current audio implementation after the dynamic-bus, NumPy mixer, DSP, send/return, preset, snapshot, and audio-editor work.

## Contents

- [1. Requirements and architecture](#1-requirements-and-architecture)
- [2. Imports](#2-imports)
- [3. Accessing audio from a game](#3-accessing-audio-from-a-game)
- [4. Quick start](#4-quick-start)
- [5. Loading audio assets](#5-loading-audio-assets)
- [6. AudioSource — one playback instance](#6-audiosource--one-playback-instance)
- [7. AudioPlayer — active source playback](#7-audioplayer--active-source-playback)
- [8. MusicPlayer — music queue and repeat](#8-musicplayer--music-queue-and-repeat)
- [9. Mixer and buses](#9-mixer-and-buses)
- [10. Send/return routing](#10-sendreturn-routing)
- [11. DSP effect system](#11-dsp-effect-system)
- [12. Built-in DSP effects](#12-built-in-dsp-effects)
- [13. DSP presets](#13-dsp-presets)
- [14. Metering, clipping, headroom, and master limiter](#14-metering-clipping-headroom-and-master-limiter)
- [15. Mixer snapshots](#15-mixer-snapshots)
- [16. Audio settings and audio.toml](#16-audio-settings-and-audiotoml)
- [17. Spatial audio](#17-spatial-audio)
- [18. Cache and memory management](#18-cache-and-memory-management)
- [19. Buffering and streaming](#19-buffering-and-streaming)
- [20. Standalone mixer editor and debug overlay](#20-standalone-mixer-editor-and-debug-overlay)
- [21. Common recipes](#21-common-recipes)
- [22. Public API reference](#22-public-api-reference)
- [23. Error handling and important rules](#23-error-handling-and-important-rules)
- [24. README link](#24-readme-link)

---

## 1. Requirements and architecture

Nexora's current audio stack uses:

- Python **3.13+** according to the project package metadata
- NumPy **2.3+** for float32 PCM processing and block mixing
- SDL3 / PySDL3 for the output device
- stereo output (`channels=2`)
- WAV assets for the current built-in loader and streamer

The mixer is designed to work with free-threaded Python builds. Audio sample processing is block-oriented and uses NumPy arrays internally.

The normal signal path is:

```text
AudioSource
    ↓
Assigned AudioBus
    ↓
Bus DSP chain
    ├── Pre-fader sends ─────→ another bus
    ↓
Bus volume + pan
    ├── Post-fader sends ────→ another bus
    ↓
Parent bus
    ↓
...
    ↓
Master headroom
    ↓
Master DSP chain
    ↓
Master volume + pan
    ↓
Optional master limiter
    ↓
Metering
    ↓
SDL audio device
```

The default bus graph is:

```text
Master
├── Music
├── SFX
├── Ambient
└── Voice
```

`AudioSource` defaults to **Master** when no bus is specified.

---

## 2. Imports

The main audio types are exported from `nexora.audio`:

```python
from nexora.audio import (
    AudioSystem,
    AudioSource,
    AudioSourceState,
    AudioBus,
    AudioSend,
    AudioEffect,
    AudioMixer,
    AudioPlayer,
    MusicPlayer,
    RepeatMode,
    Sound,
    StreamedSound,
    AudioCache,
    GainEffect,
    LimiterEffect,
    LowPassFilterEffect,
    HighPassFilterEffect,
    ParametricEQEffect,
    CompressorEffect,
    DelayEffect,
    ReverbEffect,
    DistortionEffect,
    NoiseGateEffect,
    StereoWidthEffect,
    AudioPreset,
    AudioPresetRegistry,
)
```

For normal game code, prefer `self.audio` from `Game` rather than constructing a second `AudioSystem` yourself.

---

## 3. Accessing audio from a game

A running Nexora `Game` exposes the engine audio system through:

```python
audio = self.audio
```

The engine creates, configures, initializes, updates, and shuts down this audio system for you.

Useful runtime objects are available from it:

```python
self.audio.player   # source playback / mixer feeding
self.audio.mixer    # bus graph, routing, sends, snapshots
self.audio.music    # music queue helper
self.audio.cache    # loaded audio assets
self.audio.presets  # DSP preset registry
self.audio.device   # low-level SDL audio device
```

For a standalone tool or test, an `AudioSystem` can be constructed manually:

```python
from nexora.audio import AudioSystem

audio = AudioSystem(
    frequency=48_000,
    channels=2,
    target_queue_frames=2048,
    max_update_frames=2048,
)

audio.initialize()

try:
    # use audio
    ...
finally:
    audio.shutdown()
```

`channels` currently must be `2`.

---

## 4. Quick start

### Play one sound effect

```python
from nexora.audio import AudioSource

sound = self.audio.load("assets/audio/explosion.wav")
source = AudioSource(sound, bus="SFX")
self.audio.player.play(source)
```

### Change the source volume

```python
source = AudioSource(
    sound,
    volume=0.7,
    bus="SFX",
)
self.audio.player.play(source)
```

### Loop an ambience sound

```python
ambience = self.audio.load_stream("assets/audio/rain.wav")

source = AudioSource(
    ambience,
    loop=True,
    volume=0.6,
    bus="Ambient",
)

self.audio.player.play(source)
```

### Play music

```python
track = self.audio.load_stream("assets/audio/music/theme.wav")
self.audio.music.play(track)
```

### Stop a source

```python
self.audio.player.stop(source)
```

A stopped or naturally finished source is automatically pruned from the player's active source list.

---

## 5. Loading audio assets

### `AudioSystem.load(path)`

Loads and caches the complete WAV asset as a `Sound`.

```python
sound = self.audio.load("assets/audio/hit.wav")
```

Use this for:

- short SFX
- UI sounds
- footsteps
- weapon sounds
- short voice clips
- repeatedly played assets where full decoding is acceptable

The decoded PCM is cached as a contiguous NumPy `float32` array on first use and shared read-only between playback instances.

### `AudioSystem.load_stream(path)`

Loads WAV metadata and streams decoded chunks while playing.

```python
music = self.audio.load_stream("assets/audio/music/long_track.wav")
```

Use this for:

- music
- long ambience tracks
- long dialogue or radio files
- large WAV files that should not be fully decoded into memory

### Cache behavior

Both methods use the same `AudioCache`. A normalized path is loaded only once.

```python
self.audio.unload("assets/audio/hit.wav")
self.audio.clear_cache()
```

`unload()` removes one cached asset. `clear_cache()` removes all cached assets.

> [!IMPORTANT]
> Removing an asset from the cache does not magically stop a source that is already using that asset. Stop/remove live sources first when you need deterministic release behavior.

---

## 6. AudioSource — one playback instance

An `AudioSource` is a single playback instance. Multiple `AudioSource` objects can play the same `Sound` simultaneously.

```python
source = AudioSource(
    sound,
    volume=1.0,
    loop=False,
    position=(0.0, 0.0),
    min_distance=1.0,
    max_distance=1000.0,
    pitch=1.0,
    bus="Master",
)
```

### Constructor arguments

| Argument | Default | Meaning |
|---|---:|---|
| `sound` | required | Loaded sound asset |
| `volume` | `1.0` | Source gain, range `0.0..1.0` |
| `loop` | `False` | Restart automatically at end |
| `position` | `(0.0, 0.0)` | 2D world position |
| `min_distance` | `1.0` | Full-volume distance |
| `max_distance` | `1000.0` | Zero-volume distance |
| `pitch` | `1.0` | Playback-rate / pitch multiplier, must be `> 0` |
| `bus` | `"Master"` | Destination bus, bus object, name, ID, or `None` |

### Playback state

```python
source.state
source.playing
source.paused
source.stopped
```

States are defined by `AudioSourceState`:

```python
AudioSourceState.STOPPED
AudioSourceState.PLAYING
AudioSourceState.PAUSED
```

### Position and progress

```python
source.position          # current frame
source.position_seconds  # current time in seconds
source.duration          # total duration
source.remaining         # seconds remaining
source.progress          # 0.0 .. 1.0
```

### Seeking

```python
source.seek(48_000)      # seek by frame
source.seek_seconds(5.0)
```

Seeking below zero raises `ValueError`. Seeking past the end clamps to the final frame.

### Volume

```python
source.volume = 0.5
```

Valid range: `0.0 .. 1.0`.

### Pitch

```python
source.pitch = 0.8
source.pitch = 1.25
```

Pitch must be greater than zero.

### Looping

```python
source.loop = True
```

### Bus assignment

```python
source.bus = "SFX"
source.bus = self.audio.get_bus("Weapons")
```

The default is `Master`.

### Fades

```python
source.fade_in(1.0)
source.fade_out(0.5)
```

The duration is in seconds. A completed fade-out stops the source and closes an active stream reader.

### Direct source controls

```python
source.play()
source.pause()
source.resume()
source.stop()
```

For normal engine playback, prefer using `self.audio.player.play(source)` so the player owns and mixes the source.

### Volume helpers

```python
source.get_source_volume()
source.get_effective_volume(self.audio.mixer)
```

`get_source_volume()` is source/fade gain only. `get_effective_volume()` reports the effective source gain including bus routing volume/mute semantics.

---

## 7. AudioPlayer — active source playback

The central player is available as:

```python
player = self.audio.player
```

### Play

```python
player.play(source)
```

If the source is not already registered, it is added automatically and started.

### Pause and resume

```python
player.pause(source)
player.resume(source)
```

### Stop

```python
player.stop(source)
```

### Stop everything

```python
player.stop_all()
```

### Explicit source ownership

```python
player.add(source)
player.remove(source)
```

`remove()` also closes a stream reader held by the source.

### Active sources

```python
player.sources
player.has_playing_sources
```

`player.sources` returns a tuple snapshot.

### Cleanup

```python
removed_count = player.prune_stopped_sources()
```

Normally this cleanup already happens automatically after mixing. It exists as a public maintenance/debug helper.

### Listener position

The player owns the spatial listener:

```python
player.listener.position = (camera_x, camera_y)
# or
player.listener.set_position(camera_x, camera_y)
```

---

## 8. MusicPlayer — music queue and repeat

Nexora includes a convenience music player:

```python
music = self.audio.music
```

Music is routed to the `Music` bus.

### Play immediately

```python
track = self.audio.load_stream("assets/audio/music/title.wav")
music.play(track)
```

### Queue tracks

```python
music.enqueue(track_a)
music.enqueue(track_b)
music.play_next()
```

### Previous track

```python
music.previous()
```

### Shuffle

```python
music.set_shuffle(True)
```

### Repeat

```python
from nexora.audio import RepeatMode

music.set_repeat(RepeatMode.OFF)
music.set_repeat(RepeatMode.ONE)
music.set_repeat(RepeatMode.ALL)
```

### Playback control

```python
music.pause()
music.resume()
music.stop()
```

### Queue state

```python
music.current
music.source
music.queue
music.history
music.playing
music.paused
```

### Clear bookkeeping

```python
music.clear_queue()
music.clear_history()
```

The engine/game loop is expected to call the music update logic as part of normal runtime integration where required by the project.

---

## 9. Mixer and buses

The high-level API is available directly on `AudioSystem`:

```python
audio = self.audio
```

The lower-level mixer is:

```python
mixer = self.audio.mixer
```

### Default buses

The default graph contains:

```text
Master
Music -> Master
SFX -> Master
Ambient -> Master
Voice -> Master
```

These are normal `AudioBus` objects, not special channel types.

### Create a bus

```python
weapons = audio.create_bus(
    "Weapons",
    parent="SFX",
    volume=0.9,
    muted=False,
    pan=0.0,
    solo=False,
)
```

Buses can be nested arbitrarily as long as the graph stays acyclic:

```python
audio.create_bus("Weapons", parent="SFX")
audio.create_bus("Rifles", parent="Weapons")
audio.create_bus("Pistols", parent="Weapons")
```

### Check and retrieve buses

```python
audio.has_bus("Weapons")
bus = audio.get_bus("Weapons")
all_buses = audio.get_buses()
```

Names are resolved case-insensitively by the mixer.

### Stable bus IDs

Every bus has a stable ID:

```python
bus.id
same_bus = audio.get_bus_by_id(bus.id)
```

The ID survives a rename.

### Rename a bus

```python
audio.rename_bus("Weapons", "Combat")
```

Existing `AudioBus` object references remain valid. Legacy source routes stored as matching strings are migrated by the high-level `AudioSystem.rename_bus()` helper.

### Parent routing

```python
audio.set_bus_parent("Weapons", "SFX")
audio.set_bus_parent("Weapons", "Master")
```

A routing cycle is rejected.

### Remove a bus

```python
audio.remove_bus(
    "Weapons",
    reassign_to="SFX",
    reparent_children=True,
)
```

The high-level removal API safely reassigns active sources using that bus.

### Bus volume

```python
audio.set_bus_volume("SFX", 0.7)
value = audio.get_bus_volume("SFX")
```

Bus volume is linear gain. It must not be negative.

### Bus pan

```python
audio.set_bus_pan("Music", -0.25)
pan = audio.get_bus_pan("Music")
```

Range:

```text
-1.0 = left
 0.0 = unchanged stereo balance
+1.0 = right
```

Bus pan is a balance operation; `0.0` leaves the stereo signal unchanged.

### Mute

```python
audio.set_bus_muted("SFX", True)
audio.set_bus_muted("SFX", False)
```

Direct bus methods are also available:

```python
bus.mute()
bus.unmute()
bus.toggle_mute()
```

### Solo

```python
audio.set_bus_solo("SFX", True)
```

Solo is hierarchy-aware. Necessary ancestors remain audible so a soloed child can still reach `Master`; descendants of a soloed parent remain audible as part of that branch.

### Effective volume

```python
bus.effective_volume
```

This follows the parent chain and accounts for mute state.

---

## 10. Send/return routing

Sends duplicate part of a bus signal into another bus without replacing the normal parent route.

Typical use: shared reverb.

```text
Weapons ─────────→ SFX ─→ Master
    └─ 25% send ─→ Reverb ─→ Master
```

### Create a return bus

```python
audio.create_bus("Reverb", parent="Master")
```

### Add a send

```python
send = audio.add_send(
    "Weapons",
    "Reverb",
    amount=0.25,
    pre_fader=False,
    enabled=True,
)
```

`amount` must be non-negative.

### Pre-fader vs post-fader

```python
pre_fader=True
```

Pre-fader send point:

```text
Bus input -> DSP -> SEND -> volume/pan -> parent
```

Post-fader send point (`pre_fader=False`, default):

```text
Bus input -> DSP -> volume/pan -> SEND -> parent
```

Use pre-fader when the send level should remain independent of the source bus fader. Use post-fader for the common reverb/delay case where lowering the dry bus also lowers the send.

### Modify a send

```python
audio.set_send_amount(send.id, 0.5)
audio.set_send_enabled(send.id, False)
audio.set_send_pre_fader(send.id, True)
```

### List sends

```python
sends = audio.get_sends()
```

Lower-level mixer helpers:

```python
self.audio.mixer.get_send(send.id)
self.audio.mixer.get_sends_from("Weapons")
```

### Remove a send

```python
audio.remove_send(send.id)
```

### Routing safety

Parent routes and send routes form one acyclic routing graph. Nexora rejects enabled routes that would introduce a feedback cycle.

---

## 11. DSP effect system

Every `AudioBus` has an ordered DSP chain.

```python
bus = audio.get_bus("SFX")
bus.effects
```

Effects run in insertion order.

### Add an effect

```python
from nexora.audio import CompressorEffect

compressor = audio.add_bus_effect(
    "SFX",
    CompressorEffect(),
)
```

Insert at a specific position:

```python
audio.add_bus_effect("SFX", effect, index=0)
```

### Remove an effect

```python
audio.remove_bus_effect("SFX", compressor)
```

### Clear the chain

```python
audio.clear_bus_effects("SFX")
```

### Read the chain

```python
effects = audio.get_bus_effects("SFX")
```

### Wet/dry

Every built-in effect inherits `AudioEffect.wet`:

```python
effect.wet = 0.35
```

Range: `0.0 .. 1.0`.

- `0.0` = fully dry
- `1.0` = fully processed

The same can be changed through the high-level API by effect index:

```python
audio.set_bus_effect_wet("SFX", 0, 0.35)
```

### Bypass

Bypass one effect:

```python
effect.bypassed = True
```

or:

```python
audio.set_bus_effect_bypassed("SFX", 0, True)
```

Bypass the complete bus DSP chain:

```python
audio.set_bus_effects_bypassed("SFX", True)
```

### Runtime parameters

All built-in effects expose parameters through `set_parameter()` and `get_parameter()`:

```python
effect.set_parameter("threshold_db", -18.0)
value = effect.get_parameter("threshold_db")
```

Through a bus/index:

```python
audio.set_bus_effect_parameter(
    "SFX",
    0,
    "threshold_db",
    -18.0,
)

value = audio.get_bus_effect_parameter(
    "SFX",
    0,
    "threshold_db",
)
```

This is the preferred mechanism for editor-driven or animated DSP parameter changes.

### Resetting stateful DSP

Filters, compressor smoothing, delay lines, reverb lines, and gates keep state across mixer blocks.

Reset one effect:

```python
effect.reset()
```

Reset all bus effects:

```python
bus.reset_effects()
```

---

## 12. Built-in DSP effects

All effects accept:

```python
enabled=True
wet=1.0
```

unless a different `wet` default is listed below.

### `GainEffect`

```python
GainEffect(gain=1.0, wet=1.0)
```

Parameters:

- `gain`: linear multiplier

Example:

```python
bus.add_effect(GainEffect(0.8))
```

### `LimiterEffect`

```python
LimiterEffect(threshold=1.0, wet=1.0)
```

Parameters:

- `threshold`: linear absolute clipping threshold, must be `> 0`

This is a lightweight hard limiter/clipper.

### `LowPassFilterEffect`

```python
LowPassFilterEffect(
    cutoff_hz=12000.0,
    q=0.70710678,
)
```

Parameters:

- `cutoff_hz > 0`
- `q > 0`

The runtime coefficient calculation clamps the actual cutoff below Nyquist.

Use cases:

- underwater/muffled sound
- occlusion
- distant/behind-wall effects
- removing harsh highs

### `HighPassFilterEffect`

```python
HighPassFilterEffect(
    cutoff_hz=80.0,
    q=0.70710678,
)
```

Parameters:

- `cutoff_hz > 0`
- `q > 0`

Use cases:

- radio/telephone processing
- rumble removal
- thin/small-speaker character

### `ParametricEQEffect`

```python
ParametricEQEffect(
    frequency_hz=1000.0,
    gain_db=0.0,
    q=1.0,
)
```

Parameters:

- `frequency_hz > 0`
- `gain_db`: boost/cut in dB
- `q > 0`

Use several instances for several EQ bands:

```python
bus.add_effect(ParametricEQEffect(120.0, 3.0, 0.8))
bus.add_effect(ParametricEQEffect(1200.0, -2.0, 1.3))
bus.add_effect(ParametricEQEffect(7000.0, 2.0, 0.7))
```

### `CompressorEffect`

```python
CompressorEffect(
    threshold_db=-12.0,
    ratio=4.0,
    attack_ms=10.0,
    release_ms=100.0,
    makeup_gain_db=0.0,
)
```

Parameters:

- `threshold_db`: threshold in dBFS
- `ratio >= 1.0`
- `attack_ms >= 0`
- `release_ms >= 0`
- `makeup_gain_db`: output makeup gain

Read current gain reduction:

```python
compressor.gain_reduction_db
```

The compressor is stereo-linked: both channels use the same gain reduction.

### `DelayEffect`

```python
DelayEffect(
    delay_seconds=0.25,
    feedback=0.35,
    wet=0.25,
)
```

Parameters:

- `delay_seconds > 0`
- `feedback` range `-0.99 .. 0.99`

The internal delayed output is fully wet; the inherited `wet` property controls dry/wet blending.

### `ReverbEffect`

```python
ReverbEffect(
    room_size=0.5,
    damping=0.35,
    decay=0.65,
    wet=0.2,
)
```

Parameters:

- `room_size`: `0.0 .. 1.0`
- `damping`: `0.0 .. 1.0`
- `decay`: `0.0 <= decay < 1.0`

Use cases:

- caves
- halls
- rooms
- shared reverb return buses

### `DistortionEffect`

```python
DistortionEffect(
    drive=2.0,
    output_gain_db=0.0,
    mode="soft",
    wet=1.0,
)
```

Parameters:

- `drive > 0`
- `output_gain_db`: post-distortion gain in dB
- `mode`: `"soft"` or `"hard"`

`soft` uses smooth saturation; `hard` produces harder clipping.

### `NoiseGateEffect`

```python
NoiseGateEffect(
    threshold_db=-40.0,
    attack_ms=2.0,
    hold_ms=25.0,
    release_ms=80.0,
)
```

Parameters:

- `threshold_db`: gate threshold in dBFS
- `attack_ms >= 0`
- `hold_ms >= 0`
- `release_ms >= 0`

Current smoothed gate gain:

```python
gate.gain
```

### `StereoWidthEffect`

```python
StereoWidthEffect(width=1.0)
```

Range: `0.0 .. 2.0`.

```text
0.0 = mono
1.0 = original stereo width
2.0 = double side component
```

Mono buffers are intentionally left unchanged.

---

## 13. DSP presets

The audio system includes a thread-safe preset registry:

```python
self.audio.presets
```

Presets store effect configuration, not live effect instances. Applying a preset creates fresh effect instances, which is important for stateful filters, delay, and reverb.

### Built-in presets

Nexora currently includes:

| Preset | Intended use |
|---|---|
| `Radio` | Band-limited compressed radio/voice communication |
| `Telephone` | Narrow-band telephone sound |
| `Underwater` | Muffled underwater ambience |
| `Cave` | Large reflective cave space |
| `Hall` | Large hall reverb |
| `Distorted Speaker` | Overdriven small speaker / PA character |
| `Wide Music` | Stereo widening and gentle glue compression |

### Apply a preset

```python
audio.apply_audio_preset("Radio", "Voice")
```

By default this replaces the existing effect chain.

Append instead:

```python
audio.apply_audio_preset(
    "Cave",
    "Ambient",
    replace=False,
)
```

### Register a custom preset

```python
from nexora.audio import (
    HighPassFilterEffect,
    CompressorEffect,
    ReverbEffect,
)

audio.register_audio_preset(
    "Boss Voice",
    [
        HighPassFilterEffect(180.0),
        CompressorEffect(-18.0, 4.0),
        ReverbEffect(wet=0.15),
    ],
    description="Processed boss dialogue",
)
```

### Capture the current chain from a bus

```python
audio.capture_bus_preset(
    "My Weapon Chain",
    "Weapons",
)
```

### Query presets

```python
preset = audio.get_audio_preset("Radio")
all_presets = audio.get_audio_presets()
```

Preset names are case-insensitive in the registry.

### Remove a preset

```python
audio.remove_audio_preset("Boss Voice")
```

### Save a preset

```python
audio.save_audio_preset(
    "Boss Voice",
    "audio_presets/boss_voice.npreset",
)
```

### Load a preset

```python
preset = audio.load_audio_preset(
    "audio_presets/boss_voice.npreset",
)
```

Overwrite an existing preset:

```python
audio.load_audio_preset(
    "audio_presets/boss_voice.npreset",
    overwrite=True,
)
```

Override the name while loading:

```python
audio.load_audio_preset(
    "audio_presets/boss_voice.npreset",
    name="Boss Voice Variant",
)
```

Audio presets use the shared Nexora data container with `DataType.AudioPreset` and schema version `1`.

---

## 14. Metering, clipping, headroom, and master limiter

Metering is post-DSP/post-fader/post-pan for each bus.

### Linear peak

```python
left, right = audio.get_bus_peak("Master")
```

### Linear RMS

```python
left, right = audio.get_bus_rms("Master")
```

### dBFS peak

```python
left_db, right_db = audio.get_bus_peak_dbfs("Master")
```

### dBFS RMS

```python
left_db, right_db = audio.get_bus_rms_dbfs("Master")
```

### Peak hold

```python
left, right = audio.get_bus_peak_hold("Master")
left_db, right_db = audio.get_bus_peak_hold_dbfs("Master")
```

Clear hold:

```python
audio.clear_bus_peak_hold("Master")
```

### Clip indicator

```python
if audio.get_bus_clipped("Master"):
    print("Master clipped")
```

### Headroom

Reserve headroom before the master DSP chain:

```python
audio.set_headroom_db(-3.0)
```

Read it:

```python
audio.get_headroom_db()
```

This converts dB to a linear gain internally and is applied to the Master before its bus DSP chain.

### Dedicated master limiter

Enable:

```python
limiter = audio.enable_master_limiter(0.98)
```

Disable:

```python
audio.disable_master_limiter()
```

The dedicated master limiter runs as the final master safety stage after Master volume/pan and before metering/output.

A useful game default is:

```python
audio.set_headroom_db(-3.0)
audio.enable_master_limiter(0.98)
```

---

## 15. Mixer snapshots

Snapshots capture mixer state so it can be restored later.

```python
snapshot = audio.create_mixer_snapshot()
```

Restore:

```python
audio.restore_mixer_snapshot(snapshot)
```

The snapshot includes the mixer topology/state needed by the current implementation, including bus state, built-in DSP states, sends, headroom, and master-limiter configuration.

### Keep current topology

```python
audio.restore_mixer_snapshot(
    snapshot,
    restore_topology=False,
)
```

Use cases:

- temporarily change the whole mix for a cutscene
- switch between gameplay and pause-menu mixes
- save an editor mixer state
- restore a known debug state

Example:

```python
normal_mix = audio.create_mixer_snapshot()

audio.set_bus_volume("Music", 0.3)
audio.apply_audio_preset("Underwater", "Master", replace=False)

# later
audio.restore_mixer_snapshot(normal_mix)
```

---

## 16. Audio settings and audio.toml

Nexora's layered audio settings now describe the dynamic bus graph. The old separate `[volume]` section is not part of the current format.

Default structure:

```toml
[buses.master]
volume = 1.0
muted = false

[buses.music]
parent = "master"
volume = 1.0
muted = false

[buses.sfx]
parent = "master"
volume = 1.0
muted = false

[buses.ambient]
parent = "master"
volume = 1.0
muted = false

[buses.voice]
parent = "master"
volume = 1.0
muted = false
```

Custom buses can also be declared:

```toml
[buses.weapons]
parent = "sfx"
volume = 0.9
muted = false

[buses.footsteps]
parent = "sfx"
volume = 0.75
muted = false
```

The supported settings per bus in `audio.toml` are currently:

- `parent`
- `volume`
- `muted`

### Game settings facade

A running `Game` exposes:

```python
self.audio_settings
```

Read:

```python
value = self.audio_settings.get(
    "buses.music.volume",
    1.0,
)
```

Write:

```python
self.audio_settings.set(
    "buses.music.volume",
    0.5,
)
```

Attribute-style access is also supported:

```python
self.audio_settings.buses.music.volume = 0.5
self.audio_settings.buses.music.muted = False
```

After manually changing stored settings when needed:

```python
self.apply_audio_settings()
```

Reset user overrides:

```python
self.reset_audio_settings()
```

> [!IMPORTANT]
> Do not write keys such as `volume.master`. The current format is `buses.master.volume`.

---

## 17. Spatial audio

Nexora currently provides stereo 2D attenuation and panning.

### Set the listener

Usually track the player/camera position:

```python
self.audio.player.listener.position = (
    player_x,
    player_y,
)
```

or:

```python
self.audio.player.listener.set_position(
    player_x,
    player_y,
)
```

### Create a positioned source

```python
source = AudioSource(
    sound,
    bus="SFX",
    position=(enemy_x, enemy_y),
    min_distance=2.0,
    max_distance=40.0,
)

self.audio.player.play(source)
```

### Update a moving source

```python
source.position_2d = (enemy.x, enemy.y)
```

### Query spatial calculation

```python
volume = source.get_spatial_volume(
    self.audio.player.listener.position
)

attenuation, pan = source.get_spatial_parameters(
    self.audio.player.listener.position
)
```

`min_distance` is full level. The source attenuates toward zero by `max_distance`.

---

## 18. Cache and memory management

The current audio implementation is designed to avoid unbounded source retention.

### Finished sources

Naturally finished or explicitly stopped sources are pruned from `AudioPlayer`.

This means short one-shot sounds should normally be used like this:

```python
source = AudioSource(sound, bus="SFX")
self.audio.player.play(source)
```

You do not need to store the source unless you need to control it later.

### Long-lived sources

Keep a reference when you need to:

- stop/pause it later
- move it spatially
- fade it
- change pitch or volume

```python
self.ambience_source = AudioSource(
    ambience,
    loop=True,
    bus="Ambient",
)
self.audio.player.play(self.ambience_source)
```

Cleanup:

```python
self.audio.player.stop(self.ambience_source)
self.ambience_source = None
```

### Stream readers

Stopping/removing/finishing streamed sources closes their stream reader. This prevents streamed NumPy windows and file handles from being retained after playback ends.

### PCM cache

For a decoded `Sound`:

```python
sound.clear_pcm_cache()
```

This drops the decoded NumPy PCM cache while keeping the original `AudioBuffer` bytes in the `Sound`.

### Entire asset cache

```python
self.audio.clear_cache()
```

---

## 19. Buffering and streaming

`AudioPlayer` keeps the SDL audio queue near a target number of frames instead of filling it based directly on render-frame rate.

### Target queued frames

```python
audio.target_queue_frames = 2048
```

Must be greater than zero.

### Maximum frames mixed per update

```python
audio.max_update_frames = 2048
```

Must be greater than zero.

These values are also available directly on `audio.player`.

### Choosing values

Smaller buffers can reduce latency but increase the chance of underruns on a busy system. Larger buffers increase latency but provide more safety.

A useful starting point at 48 kHz is the engine default:

```text
target_queue_frames = 2048
max_update_frames    = 2048
```

### Streaming recommendation

Prefer:

```python
audio.load_stream(path)
```

for long audio assets. Prefer:

```python
audio.load(path)
```

for frequently reused short effects.

---

## 20. Standalone mixer editor and debug overlay

### Standalone mixer editor

Run:

```powershell
python -m nexora --audioedit
```

or with a project path:

```powershell
python -m nexora --audioedit MyGame
```

The editor is intended to manage:

- bus hierarchy
- volume/pan
- mute/solo
- meters
- DSP chains and effect parameters
- presets
- sends
- mixer state save/load

### Debug mixer overlay

The normal debug key is configurable and defaults to F3.

Current intended behavior:

```text
Debug key          -> normal debug overlay
Shift + debug key  -> audio/mixer debug overlay
```

The audio overlay displays live bus stereo meters and routing/debug information without acting as the full mixer editor.

---

## 21. Common recipes

### 21.1 One-shot UI sound

```python
click = self.audio.load("assets/audio/ui/click.wav")

self.audio.player.play(
    AudioSource(
        click,
        volume=0.7,
        bus="SFX",
    )
)
```

### 21.2 Footstep bus

Create once during initialization:

```python
self.audio.create_bus(
    "Footsteps",
    parent="SFX",
    volume=0.8,
)
```

Play:

```python
step = self.audio.load("assets/audio/steps/stone_01.wav")
self.audio.player.play(
    AudioSource(step, bus="Footsteps")
)
```

### 21.3 2D enemy sound

```python
source = AudioSource(
    self.audio.load("assets/audio/enemy/growl.wav"),
    bus="SFX",
    position=(enemy.x, enemy.y),
    min_distance=3.0,
    max_distance=30.0,
)
self.audio.player.play(source)
```

When the enemy moves:

```python
source.position_2d = (enemy.x, enemy.y)
```

### 21.4 Long ambience stream

```python
rain = self.audio.load_stream("assets/audio/ambience/rain.wav")

self.rain = AudioSource(
    rain,
    bus="Ambient",
    volume=0.5,
    loop=True,
)

self.audio.player.play(self.rain)
```

### 21.5 Music playlist

```python
from nexora.audio import RepeatMode

track_a = self.audio.load_stream("assets/music/a.wav")
track_b = self.audio.load_stream("assets/music/b.wav")
track_c = self.audio.load_stream("assets/music/c.wav")

self.audio.music.play(track_a)
self.audio.music.enqueue(track_b)
self.audio.music.enqueue(track_c)
self.audio.music.set_repeat(RepeatMode.ALL)
```

### 21.6 Shared reverb return

```python
from nexora.audio import ReverbEffect

self.audio.create_bus("Reverb", parent="Master")
self.audio.add_bus_effect(
    "Reverb",
    ReverbEffect(
        room_size=0.8,
        damping=0.35,
        decay=0.85,
        wet=1.0,
    ),
)

self.audio.add_send(
    "SFX",
    "Reverb",
    amount=0.18,
    pre_fader=False,
)

self.audio.add_send(
    "Voice",
    "Reverb",
    amount=0.10,
    pre_fader=False,
)
```

For a dedicated return bus, using a fully wet reverb is usually the cleanest setup because the dry signal already follows the normal route.

### 21.7 Radio voice

```python
self.audio.apply_audio_preset(
    "Radio",
    "Voice",
)
```

### 21.8 Underwater master effect

Save current mix:

```python
self.normal_mix = self.audio.create_mixer_snapshot()
```

Apply:

```python
self.audio.apply_audio_preset(
    "Underwater",
    "Master",
    replace=False,
)
```

Restore:

```python
self.audio.restore_mixer_snapshot(self.normal_mix)
```

### 21.9 Duck music manually during dialogue

```python
self.audio.set_bus_volume("Music", 0.35)
```

Restore:

```python
self.audio.set_bus_volume("Music", 1.0)
```

For a more advanced implementation, automate the bus volume or add a future side-chain/ducking system.

### 21.10 Master safety setup

```python
self.audio.set_headroom_db(-3.0)
self.audio.enable_master_limiter(0.98)
```

### 21.11 Runtime DSP editing

```python
from nexora.audio import LowPassFilterEffect

filter_fx = self.audio.add_bus_effect(
    "Music",
    LowPassFilterEffect(12000.0),
)

# Muffle dynamically
filter_fx.cutoff_hz = 1500.0

# or by index for generic/editor code
self.audio.set_bus_effect_parameter(
    "Music",
    0,
    "cutoff_hz",
    1500.0,
)
```

---

## 22. Public API reference

This section is a compact inventory of the public audio surface.

### `AudioSystem`

Constructor:

```python
AudioSystem(
    *,
    frequency=AudioDevice.DEFAULT_FREQUENCY,
    channels=AudioDevice.DEFAULT_CHANNELS,
    target_queue_frames=2048,
    max_update_frames=2048,
)
```

Properties / owned systems:

```python
audio.initialized
audio.frequency
audio.channels
audio.target_queue_frames
audio.max_update_frames

audio.mixer
audio.player
audio.music
audio.cache
audio.device
audio.presets
```

Lifecycle:

```python
audio.initialize()
audio.shutdown()
```

Assets/cache:

```python
audio.load(path)
audio.load_stream(path)
audio.unload(path)
audio.clear_cache()
```

Bus management:

```python
audio.create_bus(name, *, parent="Master", volume=1.0,
                 muted=False, pan=0.0, solo=False, bus_id=None)
audio.has_bus(name)
audio.get_buses()
audio.get_bus(name)
audio.get_bus_by_id(bus_id)
audio.set_bus_parent(name, parent)
audio.remove_bus(name, *, reassign_to="Master", reparent_children=True)
audio.rename_bus(name_or_id, new_name)
```

Bus controls:

```python
audio.set_bus_volume(name, volume)
audio.get_bus_volume(name)
audio.set_bus_pan(name, pan)
audio.get_bus_pan(name)
audio.set_bus_solo(name, solo)
audio.get_bus_solo(name)
audio.set_bus_muted(name, muted)
audio.get_bus_muted(name)
```

DSP chain:

```python
audio.add_bus_effect(name, effect, *, index=None)
audio.remove_bus_effect(name, effect)
audio.clear_bus_effects(name)
audio.get_bus_effects(name)
audio.set_bus_effects_bypassed(name, bypassed)
audio.set_bus_effect_bypassed(name, index, bypassed)
audio.set_bus_effect_wet(name, index, wet)
audio.set_bus_effect_parameter(name, index, parameter, value)
audio.get_bus_effect_parameter(name, index, parameter)
```

Sends:

```python
audio.add_send(source, target, *, amount=1.0,
               pre_fader=False, enabled=True)
audio.remove_send(send_or_id)
audio.get_sends()
audio.set_send_amount(send_id, amount)
audio.set_send_enabled(send_id, enabled)
audio.set_send_pre_fader(send_id, pre_fader)
```

Metering:

```python
audio.get_bus_peak(name)
audio.get_bus_rms(name)
audio.get_bus_peak_dbfs(name)
audio.get_bus_rms_dbfs(name)
audio.get_bus_peak_hold(name)
audio.get_bus_peak_hold_dbfs(name)
audio.get_bus_clipped(name)
audio.clear_bus_peak_hold(name)
```

Master safety:

```python
audio.set_headroom_db(value)
audio.get_headroom_db()
audio.enable_master_limiter(threshold=0.98)
audio.disable_master_limiter()
```

Presets:

```python
audio.register_audio_preset(name, effects, *, description="", overwrite=False)
audio.capture_bus_preset(name, bus, *, description="", overwrite=False)
audio.apply_audio_preset(preset, bus, *, replace=True)
audio.get_audio_preset(name)
audio.get_audio_presets()
audio.remove_audio_preset(name)
audio.save_audio_preset(name, path)
audio.load_audio_preset(path, *, overwrite=False, name=None)
```

Snapshots:

```python
audio.create_mixer_snapshot()
audio.restore_mixer_snapshot(snapshot, *, restore_topology=True)
```

Reset:

```python
audio.reset()
```

### `AudioSource`

Constructor:

```python
AudioSource(
    sound,
    *,
    volume=1.0,
    loop=False,
    position=(0.0, 0.0),
    min_distance=1.0,
    max_distance=1000.0,
    pitch=1.0,
    bus="Master",
)
```

Properties:

```python
source.position
source.duration
source.position_seconds
source.remaining
source.progress
source.state
source.playing
source.paused
source.stopped
source.volume
source.bus
source.pitch
source.loop
source.position_2d
source.min_distance
source.max_distance
source.fading
```

Methods:

```python
source.seek(frame)
source.seek_seconds(seconds)
source.fade_in(duration)
source.fade_out(duration)
source.play()
source.pause()
source.resume()
source.stop()
source.get_source_volume()
source.get_effective_volume(mixer)
source.get_spatial_volume(listener_position)
source.get_spatial_parameters(listener_position)
```

### `AudioPlayer`

Properties:

```python
player.output_channels
player.output_frequency
player.target_queue_frames
player.max_update_frames
player.sources
player.has_playing_sources
player.listener
```

Methods:

```python
player.add(source)
player.remove(source)
player.play(source)
player.pause(source)
player.resume(source)
player.stop(source)
player.stop_all()
player.prune_stopped_sources()
player.mix(frame_count)
player.update()
```

`mix()` and `update()` are normally engine/runtime responsibilities. Game code usually calls playback-control methods instead.

### `AudioBus`

Constructor:

```python
AudioBus(
    name,
    volume=1.0,
    muted=False,
    *,
    parent=None,
    pan=0.0,
    solo=False,
    bus_id=None,
)
```

Properties:

```python
bus.id
bus.name
bus.volume
bus.muted
bus.pan
bus.solo
bus.effects_bypassed
bus.parent
bus.effective_volume
bus.effects

bus.peak
bus.rms
bus.peak_hold
bus.clipped
bus.peak_dbfs
bus.rms_dbfs
bus.peak_hold_dbfs
```

Methods:

```python
bus.add_effect(effect, *, index=None)
bus.remove_effect(effect)
bus.clear_effects()
bus.reset_effects()
bus.process_effects(buffer, *, sample_rate, channels)
bus.update_meter(buffer)
bus.reset_meter(clear_hold=True)
bus.clear_peak_hold()
bus.mute()
bus.unmute()
bus.toggle_mute()
```

Game code normally does not call `process_effects()` or `update_meter()` directly; those are mixer-facing operations.

### `AudioSend`

Fields:

```python
send.id
send.source_bus_id
send.target_bus_id
send.amount
send.pre_fader
send.enabled
```

### `AudioMixer`

Most projects should use `AudioSystem` wrappers. Advanced/editor code can access `audio.mixer` directly.

Important methods:

```python
mixer.create_bus(...)
mixer.add_bus(bus)
mixer.has_bus(name_or_id)
mixer.get_bus(name_or_id)
mixer.get_bus_by_id(bus_id)
mixer.get_buses()
mixer.rename_bus(name_or_id, new_name)
mixer.set_bus_parent(name_or_id, parent)
mixer.remove_bus(name_or_id, *, reparent_children_to="Master")

mixer.add_send(...)
mixer.remove_send(...)
mixer.get_send(send_id)
mixer.get_sends_from(bus)
mixer.set_send_amount(send_id, amount)
mixer.set_send_enabled(send_id, enabled)
mixer.set_send_pre_fader(send_id, pre_fader)

mixer.processing_order()
mixer.buses_by_depth(deepest_first=False)
mixer.solo_active()
mixer.is_bus_audible(bus)

mixer.create_snapshot()
mixer.restore_snapshot(snapshot, restore_topology=True)
mixer.reset()
```

Properties:

```python
mixer.buses
mixer.sends
mixer.master
mixer.headroom_db
mixer.headroom_gain
mixer.master_limiter_enabled
mixer.master_limiter
```

### `MusicPlayer`

```python
music.set_shuffle(enabled)
music.set_repeat(mode)
music.play(sound)
music.enqueue(sound)
music.play_next()
music.previous()
music.update()
music.pause()
music.resume()
music.stop()
music.clear_queue()
music.clear_history()
```

Properties:

```python
music.shuffle
music.repeat
music.current
music.source
music.queue
music.history
music.playing
music.paused
```

### `Sound`

```python
Sound.load(path)
```

Properties:

```python
sound.buffer
sound.path
sound.duration
sound.frequency
sound.channels
sound.size
sound.pcm
```

Method:

```python
sound.clear_pcm_cache()
```

### `StreamedSound`

```python
StreamedSound.load(path)
```

Properties:

```python
stream.path
stream.buffer
stream.frequency
stream.channels
stream.bytes_per_sample
stream.sample_count
stream.duration
stream.size
```

Methods:

```python
reader = stream.open_reader()
stream.clear_pcm_cache()
```

`WavStreamReader` supports:

```python
reader.seek(frame)
reader.sample(frame, channel)
reader.close()
```

Normal game code should let `AudioSource` manage readers instead of reading samples manually.

### `AudioCache`

```python
cache.load(path)
cache.load_stream(path)
cache.get(path)
cache.contains(path)
cache.remove(path)
cache.clear()
```

Properties:

```python
cache.sounds
cache.count
```

### `AudioEffect`

Common properties:

```python
effect.enabled
effect.bypassed
effect.wet
```

Common methods:

```python
effect.process(buffer, *, sample_rate, channels)
effect.process_mixed(buffer, scratch, *, sample_rate, channels)
effect.set_parameter(name, value)
effect.get_parameter(name)
effect.reset()
effect.to_state()
```

Game code normally lets the mixer call `process()`/`process_mixed()`.

### `AudioPreset`

Create from effects:

```python
AudioPreset.from_effects(name, effects, description="")
```

Create from a bus:

```python
AudioPreset.from_bus(name, bus, description="")
```

Methods:

```python
preset.instantiate_effects()
preset.to_dict()
AudioPreset.from_dict(data)
```

Fields:

```python
preset.name
preset.description
preset.effects
```

### `AudioPresetRegistry`

```python
registry.register(preset, overwrite=False)
registry.register_effects(name, effects, description="", overwrite=False)
registry.capture_bus(name, bus, description="", overwrite=False)
registry.unregister(name)
registry.has(name)
registry.get(name)
registry.apply(name, bus, replace=True)
registry.save(name, path)
registry.load(path, overwrite=False, name=None)
```

Properties:

```python
registry.presets
registry.names
```

---

## 23. Error handling and important rules

### Stereo only

The current engine mixer requires:

```python
channels == 2
```

Trying to construct the audio system with another output-channel count raises `ValueError`.

### Source volume

```text
0.0 <= volume <= 1.0
```

### Source pitch

```text
pitch > 0
```

### Spatial distances

```text
min_distance > 0
max_distance > 0
min_distance <= max_distance
```

### Bus graph

Do not create parent cycles or enabled send feedback loops. The mixer validates routing and rejects cyclic graphs.

### Master bus

Treat `Master` as the final root bus. Custom root-style buses without a parent are still routed to Master by the player so the master safety/DSP stage cannot be skipped.

### Bus names vs IDs

Use names for readable gameplay code:

```python
source.bus = "Weapons"
```

Use stable bus IDs when building editor/serialization systems that must survive renames:

```python
bus_id = bus.id
```

### Effects and threads

Built-in effect parameters are protected by locks and can be changed at runtime. Avoid directly mutating internal DSP arrays/state from gameplay threads.

### Do not share stateful effect objects between unrelated buses

A live `DelayEffect`, `ReverbEffect`, filter, gate, or compressor contains processing state. Create separate instances for separate buses. Presets already do this correctly.

### Short effects vs streamed assets

Use full `Sound` loading for short/reused SFX and streamed loading for long assets. This avoids unnecessarily decoding a long music file into RAM while still keeping short sounds cheap to replay.

### Current file-format scope

The built-in asset path currently loads/streams WAV audio. Do not assume MP3/OGG support unless a separate decoder has been added to the project.

---



## Minimal complete example

```python
from nexora import Game
from nexora.audio import (
    AudioSource,
    CompressorEffect,
    ReverbEffect,
)


class MyGame(Game):
    def initialize(self) -> None:
        # Build project routing once.
        self.audio.create_bus("Weapons", parent="SFX", volume=0.9)
        self.audio.create_bus("Reverb", parent="Master")

        # Shared wet reverb return.
        self.audio.add_bus_effect(
            "Reverb",
            ReverbEffect(
                room_size=0.75,
                damping=0.35,
                decay=0.82,
                wet=1.0,
            ),
        )

        self.audio.add_send(
            "Weapons",
            "Reverb",
            amount=0.18,
        )

        # Control dynamics on the dry weapon bus.
        self.audio.add_bus_effect(
            "Weapons",
            CompressorEffect(
                threshold_db=-14.0,
                ratio=3.0,
                attack_ms=4.0,
                release_ms=90.0,
            ),
        )

        # Master safety.
        self.audio.set_headroom_db(-3.0)
        self.audio.enable_master_limiter(0.98)

        # Load once, replay many times.
        self.weapon_sound = self.audio.load(
            "assets/audio/weapons/shot.wav"
        )

    def fire_weapon(self, x: float, y: float) -> None:
        self.audio.player.play(
            AudioSource(
                self.weapon_sound,
                bus="Weapons",
                position=(x, y),
                min_distance=2.0,
                max_distance=45.0,
            )
        )

    def update(self, delta_time: float) -> None:
        del delta_time

        # Keep the listener at the player/camera position.
        self.audio.player.listener.set_position(
            self.player_x,
            self.player_y,
        )
```

This example uses the intended high-level model:

```text
load asset once
    ↓
create one AudioSource per playback
    ↓
route source into a named bus
    ↓
process bus DSP
    ↓
optional send/return
    ↓
Master safety
    ↓
output
```
