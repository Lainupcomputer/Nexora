from __future__ import annotations

import ctypes


class RenderSnapshot:
    """
    High-throughput render snapshot.

    Stores GPU sprite instance data directly in a contiguous
    32-bit float buffer.

    Layout per sprite:
        0  x
        1  y
        2  width
        3  height
        4  rotation
        5  origin_x
        6  origin_y
        7  alpha
        8  flip_x
        9  flip_y
        10 uv_x
        11 uv_y
        12 uv_width
        13 uv_height
    """

    FLOATS_PER_SPRITE = 14
    BYTES_PER_SPRITE = 56

    def __init__(self, capacity: int):
        capacity = int(capacity)

        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self.capacity = capacity
        self.count = 0

        self._data = bytearray(
            capacity * self.BYTES_PER_SPRITE
        )

    def clear(self) -> None:
        self.count = 0

    def reserve(self, capacity: int) -> None:
        capacity = int(capacity)

        if capacity <= self.capacity:
            return

        new_data = bytearray(
            capacity * self.BYTES_PER_SPRITE
        )

        used = self.count * self.BYTES_PER_SPRITE

        if used:
            new_data[:used] = self._data[:used]

        self._data = new_data
        self.capacity = capacity

    def resize(self, count: int) -> None:
        count = int(count)

        if count < 0:
            raise ValueError("count must be >= 0")

        if count > self.capacity:
            self.reserve(count)

        self.count = count

    def add(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float = 0.0,
        origin_x: float = 0.5,
        origin_y: float = 0.5,
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv_x: float = 0.0,
        uv_y: float = 0.0,
        uv_width: float = 1.0,
        uv_height: float = 1.0,
    ) -> None:

        if self.count >= self.capacity:
            raise OverflowError(
                "RenderSnapshot capacity exceeded"
            )

        offset = self.count * self.BYTES_PER_SPRITE

        view = memoryview(self._data).cast("f")

        index = self.count * self.FLOATS_PER_SPRITE

        view[index + 0] = float(x)
        view[index + 1] = float(y)
        view[index + 2] = float(width)
        view[index + 3] = float(height)
        view[index + 4] = float(rotation)
        view[index + 5] = float(origin_x)
        view[index + 6] = float(origin_y)
        view[index + 7] = float(alpha)
        view[index + 8] = 1.0 if flip_x else 0.0
        view[index + 9] = 1.0 if flip_y else 0.0
        view[index + 10] = float(uv_x)
        view[index + 11] = float(uv_y)
        view[index + 12] = float(uv_width)
        view[index + 13] = float(uv_height)

        self.count += 1

    def write(
        self,
        index: int,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float = 0.0,
        origin_x: float = 0.5,
        origin_y: float = 0.5,
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv_x: float = 0.0,
        uv_y: float = 0.0,
        uv_width: float = 1.0,
        uv_height: float = 1.0,
    ) -> None:

        index = int(index)

        if index < 0 or index >= self.capacity:
            raise IndexError(
                f"sprite index out of range: {index}"
            )

        view = memoryview(self._data).cast("f")

        base = index * self.FLOATS_PER_SPRITE

        view[base + 0] = float(x)
        view[base + 1] = float(y)
        view[base + 2] = float(width)
        view[base + 3] = float(height)
        view[base + 4] = float(rotation)
        view[base + 5] = float(origin_x)
        view[base + 6] = float(origin_y)
        view[base + 7] = float(alpha)
        view[base + 8] = 1.0 if flip_x else 0.0
        view[base + 9] = 1.0 if flip_y else 0.0
        view[base + 10] = float(uv_x)
        view[base + 11] = float(uv_y)
        view[base + 12] = float(uv_width)
        view[base + 13] = float(uv_height)

        if index >= self.count:
            self.count = index + 1

    def write_range(
        self,
        start: int,
        end: int,
        x,
        y,
        width,
        height,
        rotation=None,
        origin_x=None,
        origin_y=None,
        alpha=None,
        flip_x=None,
        flip_y=None,
        uv_x=None,
        uv_y=None,
        uv_width=None,
        uv_height=None,
    ) -> None:
        """
        Write a range directly from columnar data.

        This is the preferred path for parallel render preparation.
        """

        start = int(start)
        end = int(end)

        if start < 0 or end < start or end > self.capacity:
            raise ValueError(
                f"invalid range: {start}:{end}"
            )

        view = memoryview(self._data).cast("f")

        for i in range(start, end):
            base = i * self.FLOATS_PER_SPRITE

            view[base + 0] = float(x[i])
            view[base + 1] = float(y[i])
            view[base + 2] = float(width[i])
            view[base + 3] = float(height[i])

            view[base + 4] = (
                float(rotation[i])
                if rotation is not None
                else 0.0
            )

            view[base + 5] = (
                float(origin_x[i])
                if origin_x is not None
                else 0.5
            )

            view[base + 6] = (
                float(origin_y[i])
                if origin_y is not None
                else 0.5
            )

            view[base + 7] = (
                float(alpha[i])
                if alpha is not None
                else 1.0
            )

            view[base + 8] = (
                1.0 if flip_x[i] else 0.0
                if flip_x is not None
                else 0.0
            )

            view[base + 9] = (
                1.0 if flip_y[i] else 0.0
                if flip_y is not None
                else 0.0
            )

            view[base + 10] = (
                float(uv_x[i])
                if uv_x is not None
                else 0.0
            )

            view[base + 11] = (
                float(uv_y[i])
                if uv_y is not None
                else 0.0
            )

            view[base + 12] = (
                float(uv_width[i])
                if uv_width is not None
                else 1.0
            )

            view[base + 13] = (
                float(uv_height[i])
                if uv_height is not None
                else 1.0
            )

        if end > self.count:
            self.count = end

    def extend_raw(self, data, count: int) -> None:
        count = int(count)

        if count < 0:
            raise ValueError("count must be >= 0")

        if count > self.capacity:
            raise OverflowError(
                "RenderSnapshot capacity exceeded"
            )

        size = count * self.BYTES_PER_SPRITE

        source = memoryview(data)

        if source.nbytes < size:
            raise ValueError(
                f"source contains {source.nbytes} bytes, "
                f"but {size} are required"
            )

        self._data[:size] = source.cast("B")[:size]
        self.count = count

    copy_from = extend_raw

    @property
    def data(self):
        return memoryview(self._data)[
            :self.count * self.BYTES_PER_SPRITE
        ]

    @property
    def raw(self):
        return self._data

    @property
    def byte_size(self) -> int:
        return self.count * self.BYTES_PER_SPRITE

    @property
    def float_count(self) -> int:
        return self.count * self.FLOATS_PER_SPRITE

    def __len__(self) -> int:
        return self.count