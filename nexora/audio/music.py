from __future__ import annotations

import random
from collections import deque
from enum import Enum
from typing import TYPE_CHECKING

from .channel import AudioChannel
from .sound import Sound
from .source import AudioSource, AudioSourceState

if TYPE_CHECKING:
    from .audio import AudioSystem


class RepeatMode(Enum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


class MusicPlayer:
    """Controls music playback and track queue management."""

    def __init__(
        self,
        audio: AudioSystem,
    ) -> None:
        self.audio = audio

        self._queue: deque[Sound] = deque()
        self._history: list[Sound] = []

        self._current: Sound | None = None
        self._source: AudioSource | None = None
        self._shuffle = False
        self._repeat = RepeatMode.OFF

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @property
    def current(self) -> Sound | None:
        return self._current

    @property
    def source(self) -> AudioSource | None:
        return self._source

    @property
    def queue(self) -> tuple[Sound, ...]:
        return tuple(self._queue)

    @property
    def history(self) -> tuple[Sound, ...]:
        return tuple(self._history)

    @property
    def playing(self) -> bool:
        return (
            self._source is not None
            and self._source.state
            == AudioSourceState.PLAYING
        )

    @property
    def paused(self) -> bool:
        return (
            self._source is not None
            and self._source.state
            == AudioSourceState.PAUSED
        )

    def set_shuffle(self, enabled: bool) -> None:
        self._shuffle = bool(enabled)

    def set_repeat(self, mode: RepeatMode) -> None:
        if not isinstance(mode, RepeatMode):
            raise TypeError(
                "Repeat mode must be a RepeatMode."
            )

        self._repeat = mode

    def play(self, sound: Sound) -> None:
        self._play(
            sound,
            add_history=True,
        )

    def _play(
        self,
        sound: Sound,
        *,
        add_history: bool,
    ) -> None:
        if self._source is not None:
            self._source.stop()

            if add_history and self._current is not None:
                self._history.append(
                    self._current
                )

        source = AudioSource(
            sound,
            channel=AudioChannel.MUSIC,
            bus=self.audio.mixer.get_bus("Music"),
        )

        self._current = sound
        self._source = source

        self.audio.player.play(source)

    def enqueue(self, sound: Sound) -> None:
        self._queue.append(sound)

    def play_next(self) -> bool:
        if not self._queue:
            return False

        if self._shuffle:
            index = random.randrange(
                len(self._queue)
            )

            sound = self._queue[index]
            del self._queue[index]
        else:
            sound = self._queue.popleft()

        self.play(sound)

        return True

    def previous(self) -> bool:
        if not self._history:
            return False

        if self._source is not None:
            self._source.stop()

        previous = self._history.pop()

        if self._current is not None:
            self._queue.appendleft(
                self._current
            )

        source = AudioSource(
            previous,
            channel=AudioChannel.MUSIC,
            bus=self.audio.mixer.get_bus("Music"),
        )

        self._current = previous
        self._source = source

        self.audio.player.play(source)

        return True

    def update(self) -> None:
        if self._source is None:
            return

        if self._source.state != AudioSourceState.STOPPED:
            return

        if self._current is None:
            return

        if self._repeat == RepeatMode.ONE:
            self._play(
                self._current,
                add_history=False,
            )
            return

        if self._queue:
            self.play_next()
            return

        if self._repeat == RepeatMode.ALL:
            if self._history:
                tracks = list(self._history)
                tracks.append(self._current)

                next_track = tracks.pop(0)
                self._history = tracks

                self._play(
                    next_track,
                    add_history=False,
                )

    def pause(self) -> None:
        if self._source is not None:
            self._source.pause()

    def resume(self) -> None:
        if self._source is not None:
            self._source.resume()

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()

    def clear_queue(self) -> None:
        self._queue.clear()

    def clear_history(self) -> None:
        self._history.clear()