from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from pathlib import Path
import struct


STREAM_CHUNK_FRAMES = 8192


@dataclass(frozen=True, slots=True)
class WavStreamInfo:
    """Metadata and byte range for a streamable WAV data chunk."""

    path: Path
    format_tag: int
    frequency: int
    channels: int
    bytes_per_sample: int
    sample_count: int
    data_offset: int
    data_size: int

    @property
    def frame_size(self) -> int:
        return self.channels * self.bytes_per_sample


def _read_wav_stream_info(path: Path) -> WavStreamInfo:
    """Read WAV metadata without loading the audio data into memory."""

    with path.open("rb") as wav_file:
        header = wav_file.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError(f"Invalid WAV header: {path}")

        format_tag: int | None = None
        frequency = 0
        channels = 0
        bits_per_sample = 0
        data_offset: int | None = None
        data_size = 0

        while True:
            chunk_header = wav_file.read(8)
            if not chunk_header:
                break
            if len(chunk_header) != 8:
                raise ValueError(f"Invalid WAV chunk header: {path}")

            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack("<I", chunk_header[4:])[0]
            chunk_start = wav_file.tell()

            if chunk_id == b"fmt ":
                if chunk_size < 16:
                    raise ValueError(f"Invalid WAV format chunk: {path}")

                fmt = wav_file.read(16)
                if len(fmt) != 16:
                    raise ValueError(f"Invalid WAV format chunk: {path}")

                (
                    format_tag,
                    channels,
                    frequency,
                    _average_bytes_per_second,
                    _block_align,
                    bits_per_sample,
                ) = struct.unpack("<HHIIHH", fmt)

            elif chunk_id == b"data":
                data_offset = chunk_start
                data_size = chunk_size

            wav_file.seek(chunk_start + chunk_size + (chunk_size & 1))

    if format_tag not in (1, 3):
        raise ValueError(
            f"Unsupported WAV format: {format_tag!r}. "
            "Streaming supports PCM and 32-bit float WAV files."
        )

    if channels <= 0 or frequency <= 0:
        raise ValueError(f"Invalid WAV format information: {path}")

    if format_tag == 3 and bits_per_sample != 32:
        raise ValueError(f"Only 32-bit float WAV files can be streamed: {path}")

    if bits_per_sample not in (8, 16, 24, 32):
        raise ValueError(f"Unsupported WAV sample width: {bits_per_sample}")

    if data_offset is None:
        raise ValueError(f"WAV data chunk not found: {path}")

    bytes_per_sample = bits_per_sample // 8
    frame_size = channels * bytes_per_sample
    if frame_size <= 0 or data_size % frame_size:
        raise ValueError(f"Invalid WAV data size: {path}")

    return WavStreamInfo(
        path=path,
        format_tag=format_tag,
        frequency=frequency,
        channels=channels,
        bytes_per_sample=bytes_per_sample,
        sample_count=data_size // frame_size,
        data_offset=data_offset,
        data_size=data_size,
    )


def _decode_24bit(data: bytes):
    for offset in range(0, len(data), 3):
        value = int.from_bytes(
            data[offset:offset + 3],
            byteorder="little",
            signed=True,
        )
        yield value / 8388608.0


def _decode_samples(
    data: bytes,
    *,
    format_tag: int,
    bytes_per_sample: int,
) -> array:
    """Decode one bounded stream chunk into packed float samples."""

    if not data:
        return array("f")

    if format_tag == 3:
        values = array(
            "f",
            (
                sample
                if math.isfinite(sample)
                else 0.0
                for (sample,) in struct.iter_unpack("<f", data)
            ),
        )
        for index, sample in enumerate(values):
            values[index] = max(-1.0, min(1.0, sample))
        return values

    if bytes_per_sample == 1:
        return array("f", ((sample - 128) / 128.0 for sample in data))

    if bytes_per_sample == 2:
        return array(
            "f",
            (
                sample / 32768.0
                for (sample,) in struct.iter_unpack("<h", data)
            ),
        )

    if bytes_per_sample == 3:
        return array("f", _decode_24bit(data))

    if bytes_per_sample == 4:
        return array(
            "f",
            (
                sample / 2147483648.0
                for (sample,) in struct.iter_unpack("<i", data)
            ),
        )

    raise ValueError(f"Unsupported WAV sample width: {bytes_per_sample}")


class WavStreamReader:
    """Read a WAV file in small decoded windows."""

    def __init__(self, info: WavStreamInfo) -> None:
        self.info = info
        self._file = info.path.open("rb")
        self._cache_start = -1
        self._cache_frames = 0
        self._cache = array("f")

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def seek(self, frame: int) -> None:
        frame = max(0, min(int(frame), self.info.sample_count))
        self._cache_start = -1
        self._cache_frames = 0
        self._cache = array("f")

    def _fill(self, frame: int) -> None:
        frame = max(0, min(int(frame), self.info.sample_count))
        if frame >= self.info.sample_count:
            self._cache_start = frame
            self._cache_frames = 0
            self._cache = array("f")
            return

        frames_to_read = min(
            STREAM_CHUNK_FRAMES,
            self.info.sample_count - frame,
        )
        byte_count = frames_to_read * self.info.frame_size
        byte_offset = self.info.data_offset + frame * self.info.frame_size

        self._file.seek(byte_offset)
        data = self._file.read(byte_count)
        if len(data) != byte_count:
            raise ValueError(f"Unexpected end of WAV stream: {self.info.path}")

        self._cache = _decode_samples(
            data,
            format_tag=self.info.format_tag,
            bytes_per_sample=self.info.bytes_per_sample,
        )
        self._cache_start = frame
        self._cache_frames = len(self._cache) // self.info.channels

    def sample(self, frame: int, channel: int) -> float:
        if frame < 0 or frame >= self.info.sample_count:
            return 0.0

        channel = max(0, min(int(channel), self.info.channels - 1))
        if not (
            self._cache_start <= frame < self._cache_start + self._cache_frames
        ):
            self._fill(frame)

        index = (frame - self._cache_start) * self.info.channels + channel
        return float(self._cache[index])

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


@dataclass(slots=True)
class StreamedSound:
    """Audio metadata backed by a WAV file instead of a full PCM cache."""

    info: WavStreamInfo

    streaming = True

    @classmethod
    def load(cls, path: str | Path) -> "StreamedSound":
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"WAV file not found: {resolved}")
        return cls(_read_wav_stream_info(resolved))

    @property
    def path(self) -> Path:
        return self.info.path

    @property
    def buffer(self):
        """Compatibility access for code that only needs sample_count."""

        return self

    @property
    def frequency(self) -> int:
        return self.info.frequency

    @property
    def channels(self) -> int:
        return self.info.channels

    @property
    def bytes_per_sample(self) -> int:
        return self.info.bytes_per_sample

    @property
    def sample_count(self) -> int:
        return self.info.sample_count

    @property
    def duration(self) -> float:
        if self.frequency <= 0:
            return 0.0
        return self.sample_count / self.frequency

    @property
    def size(self) -> int:
        return self.info.data_size

    def open_reader(self) -> WavStreamReader:
        return WavStreamReader(self.info)

    def clear_pcm_cache(self) -> None:
        """Keep the Sound cleanup API compatible; streams have no PCM cache."""

        return
