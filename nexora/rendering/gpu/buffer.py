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

    Dynamic uploads attempt to copy directly from the source
    Python buffer without creating an intermediate bytes object.
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

        self.dynamic = bool(
            dynamic
        )

        self.frames_in_flight = max(
            2,
            min(
                3,
                int(
                    frames_in_flight
                ),
            ),
        )

        self.buffer = None

        self._dynamic_buffers: list = []
        self._dynamic_transfers: list = []

        self._dynamic_index = -1

        self._destroyed = False

        self._create()

        if initial_data is not None:
            self.upload(
                initial_data
            )

    # ==========================================================
    # ERROR HANDLING
    # ==========================================================

    @staticmethod
    def _decode_error(
        error,
    ) -> str:
        if isinstance(
            error,
            bytes,
        ):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        if error is None:
            return "<unknown SDL error>"

        return str(
            error
        )

    def _check(
        self,
        condition,
        message: str,
    ):
        if not condition:
            error = self._decode_error(
                sdl3.SDL_GetError()
            )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ==========================================================
    # MEMORY HELPERS
    # ==========================================================

    @staticmethod
    def _mapped_address(
        mapped,
    ) -> int:
        """
        Return a raw integer address for a mapped SDL transfer
        buffer pointer.
        """

        if mapped is None:
            raise ValueError(
                "mapped pointer cannot be None"
            )

        # ctypes pointer with .contents
        if hasattr(
            mapped,
            "contents",
        ):
            return ctypes.addressof(
                mapped.contents
            )

        # c_void_p
        if isinstance(
            mapped,
            ctypes.c_void_p,
        ):
            if mapped.value is None:
                raise ValueError(
                    "mapped pointer is NULL"
                )

            return int(
                mapped.value
            )

        # Raw integer pointer or ctypes-compatible pointer.
        try:
            return int(
                ctypes.cast(
                    mapped,
                    ctypes.c_void_p,
                ).value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TypeError(
                "Could not obtain mapped transfer "
                "buffer address"
            ) from exc

    @staticmethod
    def _byte_view(
        data,
    ) -> memoryview:
        """
        Return a contiguous one-dimensional byte view.

        No copy is performed when the input already exposes a
        compatible contiguous buffer.
        """

        view = memoryview(
            data
        )

        if not view.contiguous:
            raise ValueError(
                "GPU upload data must be contiguous"
            )

        # Normalize to bytes while keeping the same underlying
        # storage whenever possible.
        if (
            view.format != "B"
            or view.ndim != 1
        ):
            try:
                view = view.cast(
                    "B"
                )

            except (
                TypeError,
                ValueError,
            ) as exc:
                raise ValueError(
                    "GPU upload data could not be "
                    "viewed as contiguous bytes"
                ) from exc

        return view

    @classmethod
    def _copy_to_mapped(
        cls,
        mapped,
        data,
        size: int,
    ) -> None:
        """
        Copy Python buffer data into an SDL mapped transfer buffer.

        Fast path:
            bytearray / writable memoryview
                -> direct pointer
                -> no intermediate bytes allocation

        Fallback:
            readonly buffers such as bytes
                -> temporary bytes representation

        Per-frame Nexora buffers use writable bytearray-backed
        memoryviews, so the normal dynamic rendering path uses the
        zero-intermediate-copy fast path.
        """

        size = int(
            size
        )

        if size <= 0:
            return

        view = cls._byte_view(
            data
        )

        if view.nbytes < size:
            raise ValueError(
                f"Source buffer contains only "
                f"{view.nbytes} bytes, "
                f"but {size} bytes were requested"
            )

        destination_address = (
            cls._mapped_address(
                mapped
            )
        )

        # ------------------------------------------------------
        # Fast path
        #
        # Writable buffers can be exposed directly to ctypes.
        #
        # This is the important path for:
        #
        #     bytearray
        #     memoryview(bytearray)
        #
        # used by Nexora's per-frame instance buffers.
        # ------------------------------------------------------

        if not view.readonly:
            source_buffer = (
                ctypes.c_ubyte
                * size
            ).from_buffer(
                view
            )

            ctypes.memmove(
                destination_address,
                ctypes.addressof(
                    source_buffer
                ),
                size,
            )

            return

        # ------------------------------------------------------
        # Read-only fallback
        #
        # Static resources are commonly bytes objects. They cannot
        # be exposed via ctypes.from_buffer(), so a copy is required.
        #
        # This path should not normally be used for Nexora's
        # per-frame dynamic instance buffers.
        # ------------------------------------------------------

        temporary = view[
            :size
        ].tobytes()

        ctypes.memmove(
            destination_address,
            temporary,
            size,
        )

    # ==========================================================
    # CREATION
    # ==========================================================

    def _create_gpu_buffer(
        self,
    ):
        info = (
            sdl3.SDL_GPUBufferCreateInfo()
        )

        info.usage = (
            self.usage
        )

        info.size = (
            self.size
        )

        info.props = 0

        buffer = (
            sdl3.SDL_CreateGPUBuffer(
                self.device,
                ctypes.byref(
                    info
                ),
            )
        )

        self._check(
            buffer,
            "SDL_CreateGPUBuffer failed",
        )

        return buffer

    def _create_transfer_buffer(
        self,
    ):
        info = (
            sdl3.SDL_GPUTransferBufferCreateInfo()
        )

        info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )

        info.size = (
            self.size
        )

        info.props = 0

        transfer = (
            sdl3.SDL_CreateGPUTransferBuffer(
                self.device,
                ctypes.byref(
                    info
                ),
            )
        )

        self._check(
            transfer,
            "SDL_CreateGPUTransferBuffer failed",
        )

        return transfer

    def _create(
        self,
    ):
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
                self._dynamic_buffers[
                    0
                ]
            )

            self._dynamic_index = 0

            return

        self.buffer = (
            self._create_gpu_buffer()
        )

    # ==========================================================
    # STATIC UPLOAD
    # ==========================================================

    def upload(
        self,
        data,
    ):
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

        view = self._byte_view(
            data
        )

        upload_size = (
            view.nbytes
        )

        if upload_size > self.size:
            raise ValueError(
                f"Upload size {upload_size} exceeds "
                f"buffer size {self.size}"
            )

        if upload_size <= 0:
            return

        transfer = (
            self._create_transfer_buffer()
        )

        mapped = None
        mapped_active = False

        try:
            # --------------------------------------------------
            # Map
            # --------------------------------------------------

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

            mapped_active = True

            self._copy_to_mapped(
                mapped,
                view,
                upload_size,
            )

            sdl3.SDL_UnmapGPUTransferBuffer(
                self.device,
                transfer,
            )

            mapped_active = False

            # --------------------------------------------------
            # Command buffer
            # --------------------------------------------------

            command_buffer = (
                sdl3.SDL_AcquireGPUCommandBuffer(
                    self.device
                )
            )

            self._check(
                command_buffer,
                "SDL_AcquireGPUCommandBuffer failed",
            )

            # --------------------------------------------------
            # Copy pass
            # --------------------------------------------------

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

            source.transfer_buffer = (
                transfer
            )

            source.offset = 0

            destination = (
                sdl3.SDL_GPUBufferRegion()
            )

            destination.buffer = (
                self.buffer
            )

            destination.offset = 0

            destination.size = (
                upload_size
            )

            sdl3.SDL_UploadToGPUBuffer(
                copy_pass,
                ctypes.byref(
                    source
                ),
                ctypes.byref(
                    destination
                ),
                False,
            )

            sdl3.SDL_EndGPUCopyPass(
                copy_pass
            )

            # --------------------------------------------------
            # Submit
            # --------------------------------------------------

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
            if mapped_active:
                try:
                    sdl3.SDL_UnmapGPUTransferBuffer(
                        self.device,
                        transfer,
                    )

                except Exception:
                    pass

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

        Writable source buffers are copied directly without creating
        an intermediate Python bytes object.
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

        view = self._byte_view(
            data
        )

        upload_size = (
            view.nbytes
        )

        offset = int(
            offset
        )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        if (
            offset
            + upload_size
            > self.size
        ):
            raise ValueError(
                f"Upload range "
                f"{offset}:{offset + upload_size} "
                f"exceeds buffer size {self.size}"
            )

        if upload_size <= 0:
            return self.buffer

        # ------------------------------------------------------
        # Advance ring
        # ------------------------------------------------------

        self._dynamic_index = (
            self._dynamic_index
            + 1
        ) % self.frames_in_flight

        index = (
            self._dynamic_index
        )

        gpu_buffer = (
            self._dynamic_buffers[
                index
            ]
        )

        transfer = (
            self._dynamic_transfers[
                index
            ]
        )

        self.buffer = (
            gpu_buffer
        )

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

        mapped_active = True

        try:
            # --------------------------------------------------
            # IMPORTANT
            #
            # No view.tobytes() in the normal dynamic path.
            #
            # The renderer passes memoryviews backed by bytearray,
            # allowing ctypes to copy directly from their memory.
            # --------------------------------------------------

            self._copy_to_mapped(
                mapped,
                view,
                upload_size,
            )

        finally:
            if mapped_active:
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

        source.transfer_buffer = (
            transfer
        )

        source.offset = 0

        destination = (
            sdl3.SDL_GPUBufferRegion()
        )

        destination.buffer = (
            gpu_buffer
        )

        destination.offset = (
            offset
        )

        destination.size = (
            upload_size
        )

        try:
            sdl3.SDL_UploadToGPUBuffer(
                copy_pass,
                ctypes.byref(
                    source
                ),
                ctypes.byref(
                    destination
                ),
                False,
            )

        finally:
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
        Return SDL_GPUBufferBinding for the currently active buffer.

        For dynamic buffers this is the current ring slot.
        """

        if not self.buffer:
            raise RuntimeError(
                "GPUBuffer is not initialized"
            )

        offset = int(
            offset
        )

        if size is None:
            size = (
                self.size
                - offset
            )

        size = int(
            size
        )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        if size <= 0:
            raise ValueError(
                "size must be greater than zero"
            )

        if (
            offset
            + size
            > self.size
        ):
            raise ValueError(
                "Buffer binding exceeds buffer size"
            )

        binding = (
            sdl3.SDL_GPUBufferBinding()
        )

        binding.buffer = (
            self.buffer
        )

        binding.offset = (
            offset
        )

        binding.size = (
            size
        )

        return binding

    # ==========================================================
    # CURRENT BUFFER
    # ==========================================================

    @property
    def current_buffer(
        self,
    ):
        return self.buffer

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(
        self,
    ):
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
            for transfer in (
                self._dynamic_transfers
            ):
                if transfer:
                    try:
                        sdl3.SDL_ReleaseGPUTransferBuffer(
                            self.device,
                            transfer,
                        )

                    except Exception:
                        pass

            for buffer in (
                self._dynamic_buffers
            ):
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

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()