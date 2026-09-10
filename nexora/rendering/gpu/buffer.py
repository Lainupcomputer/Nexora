from __future__ import annotations

import ctypes

import sdl3


class GPUBuffer:
    """
    GPU buffer abstraction.

    Supports:

        static:
            normal GPU buffer with synchronous upload()

        dynamic:
            ring-buffered GPU buffers intended for per-frame data.

    Dynamic buffers are designed for render-frame uploads:

        command_buffer
            -> upload_into()
            -> copy pass
            -> render pass
            -> single submit

    No SDL/GPU operation should be performed from worker threads.
    """

    DEFAULT_FRAMES_IN_FLIGHT = 3

    def __init__(
        self,
        device,
        size: int,
        usage: int,
        initial_data=None,
        *,
        dynamic: bool = False,
        frames_in_flight: int = DEFAULT_FRAMES_IN_FLIGHT,
    ):
        self.device = device
        self.size = int(size)
        self.usage = usage

        if self.size <= 0:
            raise ValueError(
                "GPUBuffer size must be greater than zero"
            )

        self.dynamic = bool(dynamic)

        self.frames_in_flight = max(
            2,
            min(
                3,
                int(frames_in_flight),
            ),
        )

        self.buffer = None

        self._dynamic_buffers: list = []
        self._dynamic_transfers: list = []

        self._dynamic_index = -1

        self._destroyed = False

        self._create()

        if initial_data is not None:
            self.upload(initial_data)

    # ==========================================================
    # ERROR HANDLING
    # ==========================================================

    @staticmethod
    def _decode_error(error) -> str:
        if isinstance(error, bytes):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        if error is None:
            return "<unknown SDL error>"

        return str(error)

    def _check(self, condition, message: str):
        if not condition:
            error = self._decode_error(
                sdl3.SDL_GetError()
            )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ==========================================================
    # CREATION
    # ==========================================================

    def _create_gpu_buffer(self):
        info = sdl3.SDL_GPUBufferCreateInfo()

        info.usage = self.usage
        info.size = self.size
        info.props = 0

        buffer = sdl3.SDL_CreateGPUBuffer(
            self.device,
            ctypes.byref(info),
        )

        self._check(
            buffer,
            "SDL_CreateGPUBuffer failed",
        )

        return buffer

    def _create_transfer_buffer(self):
        info = sdl3.SDL_GPUTransferBufferCreateInfo()

        info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )

        info.size = self.size
        info.props = 0

        transfer = sdl3.SDL_CreateGPUTransferBuffer(
            self.device,
            ctypes.byref(info),
        )

        self._check(
            transfer,
            "SDL_CreateGPUTransferBuffer failed",
        )

        return transfer

    def _create(self):
        if self.dynamic:
            for _ in range(
                self.frames_in_flight
            ):
                gpu_buffer = (
                    self._create_gpu_buffer()
                )

                transfer = (
                    self._create_transfer_buffer()
                )

                self._dynamic_buffers.append(
                    gpu_buffer
                )

                self._dynamic_transfers.append(
                    transfer
                )

            self.buffer = (
                self._dynamic_buffers[0]
            )

            self._dynamic_index = 0

            return

        self.buffer = (
            self._create_gpu_buffer()
        )

    # ==========================================================
    # STATIC UPLOAD
    # ==========================================================

    def upload(self, data):
        """
        Synchronous upload.

        Intended for static resources.

        Dynamic buffers may also use this during initialization,
        but per-frame rendering should use upload_into().
        """

        if self._destroyed:
            raise RuntimeError(
                "GPUBuffer has been destroyed"
            )

        if data is None:
            raise ValueError(
                "data cannot be None"
            )

        view = memoryview(data)

        if view.nbytes > self.size:
            raise ValueError(
                f"Upload size {view.nbytes} exceeds "
                f"buffer size {self.size}"
            )

        transfer = (
            self._create_transfer_buffer()
        )

        try:
            mapped = (
                sdl3.SDL_MapGPUTransferBuffer(
                    self.device,
                    transfer,
                    False,
                )
            )

            self._check(
                mapped,
                "SDL_MapGPUTransferBuffer failed",
            )

            ctypes.memmove(
                mapped,
                view.tobytes(),
                view.nbytes,
            )

            sdl3.SDL_UnmapGPUTransferBuffer(
                self.device,
                transfer,
            )

            command_buffer = (
                sdl3.SDL_AcquireGPUCommandBuffer(
                    self.device
                )
            )

            self._check(
                command_buffer,
                "SDL_AcquireGPUCommandBuffer failed",
            )

            copy_pass = (
                sdl3.SDL_BeginGPUCopyPass(
                    command_buffer
                )
            )

            self._check(
                copy_pass,
                "SDL_BeginGPUCopyPass failed",
            )

            source = (
                sdl3.SDL_GPUTransferBufferLocation()
            )

            source.transfer_buffer = transfer
            source.offset = 0

            destination = (
                sdl3.SDL_GPUBufferRegion()
            )

            destination.buffer = self.buffer
            destination.offset = 0
            destination.size = view.nbytes

            sdl3.SDL_UploadToGPUBuffer(
                copy_pass,
                ctypes.byref(source),
                ctypes.byref(destination),
                False,
            )

            sdl3.SDL_EndGPUCopyPass(
                copy_pass
            )

            submitted = (
                sdl3.SDL_SubmitGPUCommandBuffer(
                    command_buffer
                )
            )

            self._check(
                submitted,
                "SDL_SubmitGPUCommandBuffer failed",
            )

            sdl3.SDL_WaitForGPUIdle(
                self.device
            )

        finally:
            sdl3.SDL_ReleaseGPUTransferBuffer(
                self.device,
                transfer,
            )

    # ==========================================================
    # DYNAMIC UPLOAD INTO EXISTING COMMAND BUFFER
    # ==========================================================

    def upload_into(
        self,
        command_buffer,
        data,
        *,
        offset: int = 0,
    ):
        """
        Upload data into the current command buffer.

        IMPORTANT:

        This function does NOT acquire or submit a command buffer.

        It records:

            transfer upload

        into the supplied command buffer.

        The caller can then record a render pass into the same
        command buffer.

        This is the preferred path for per-frame instance data.
        """

        if not self.dynamic:
            raise RuntimeError(
                "upload_into() requires dynamic=True"
            )

        if self._destroyed:
            raise RuntimeError(
                "GPUBuffer has been destroyed"
            )

        if not command_buffer:
            raise ValueError(
                "command_buffer cannot be None"
            )

        if data is None:
            raise ValueError(
                "data cannot be None"
            )

        view = memoryview(data)

        upload_size = view.nbytes

        offset = int(offset)

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        if offset + upload_size > self.size:
            raise ValueError(
                f"Upload range "
                f"{offset}:{offset + upload_size} "
                f"exceeds buffer size {self.size}"
            )

        # ------------------------------------------------------
        # Advance ring
        # ------------------------------------------------------

        self._dynamic_index = (
            self._dynamic_index + 1
        ) % self.frames_in_flight

        index = self._dynamic_index

        gpu_buffer = (
            self._dynamic_buffers[index]
        )

        transfer = (
            self._dynamic_transfers[index]
        )

        self.buffer = gpu_buffer

        # ------------------------------------------------------
        # Map transfer buffer
        # ------------------------------------------------------

        mapped = (
            sdl3.SDL_MapGPUTransferBuffer(
                self.device,
                transfer,
                False,
            )
        )

        self._check(
            mapped,
            "SDL_MapGPUTransferBuffer failed",
        )

        try:
            ctypes.memmove(
                ctypes.addressof(mapped.contents)
                if hasattr(mapped, "contents")
                else mapped,
                view.tobytes(),
                upload_size,
            )
        finally:
            sdl3.SDL_UnmapGPUTransferBuffer(
                self.device,
                transfer,
            )

        # ------------------------------------------------------
        # Copy pass
        # ------------------------------------------------------

        copy_pass = (
            sdl3.SDL_BeginGPUCopyPass(
                command_buffer
            )
        )

        self._check(
            copy_pass,
            "SDL_BeginGPUCopyPass failed",
        )

        source = (
            sdl3.SDL_GPUTransferBufferLocation()
        )

        source.transfer_buffer = transfer
        source.offset = 0

        destination = (
            sdl3.SDL_GPUBufferRegion()
        )

        destination.buffer = gpu_buffer
        destination.offset = offset
        destination.size = upload_size

        sdl3.SDL_UploadToGPUBuffer(
            copy_pass,
            ctypes.byref(source),
            ctypes.byref(destination),
            False,
        )

        sdl3.SDL_EndGPUCopyPass(
            copy_pass
        )

        return gpu_buffer

    # ==========================================================
    # BINDING
    # ==========================================================

    def binding(
        self,
        offset: int = 0,
        size: int | None = None,
    ):
        """
        Return SDL_GPUBufferBinding for the currently active
        buffer.

        For dynamic buffers this is the current ring slot.
        """

        if not self.buffer:
            raise RuntimeError(
                "GPUBuffer is not initialized"
            )

        offset = int(offset)

        if size is None:
            size = self.size - offset

        size = int(size)

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        if size <= 0:
            raise ValueError(
                "size must be greater than zero"
            )

        if offset + size > self.size:
            raise ValueError(
                "Buffer binding exceeds buffer size"
            )

        binding = (
            sdl3.SDL_GPUBufferBinding()
        )

        binding.buffer = self.buffer
        binding.offset = offset
        binding.size = size

        return binding

    # ==========================================================
    # CURRENT BUFFER
    # ==========================================================

    @property
    def current_buffer(self):
        return self.buffer

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(self):
        if self._destroyed:
            return

        self._destroyed = True

        # ------------------------------------------------------
        # Wait until all recorded GPU work is finished.
        # ------------------------------------------------------

        if self.device:
            try:
                sdl3.SDL_WaitForGPUIdle(
                    self.device
                )
            except Exception:
                pass

        # ------------------------------------------------------
        # Dynamic resources
        # ------------------------------------------------------

        if self.dynamic:
            for transfer in self._dynamic_transfers:
                if transfer:
                    try:
                        sdl3.SDL_ReleaseGPUTransferBuffer(
                            self.device,
                            transfer,
                        )
                    except Exception:
                        pass

            for buffer in self._dynamic_buffers:
                if buffer:
                    try:
                        sdl3.SDL_ReleaseGPUBuffer(
                            self.device,
                            buffer,
                        )
                    except Exception:
                        pass

            self._dynamic_transfers.clear()
            self._dynamic_buffers.clear()

            self.buffer = None

            return

        # ------------------------------------------------------
        # Static resource
        # ------------------------------------------------------

        if self.buffer:
            try:
                sdl3.SDL_ReleaseGPUBuffer(
                    self.device,
                    self.buffer,
                )
            except Exception:
                pass

        self.buffer = None

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()