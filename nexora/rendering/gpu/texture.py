from __future__ import annotations

import ctypes

import sdl3


class GPUTexture:
    """
    GPU-resident 2D texture.

    Texture creation and uploads must happen on the main thread.

    The usage flags can be configured explicitly so a texture
    can be used as:

        - sampled texture
        - render target
        - post-processing target
    """

    def __init__(
        self,
        device,
        width: int,
        height: int,
        *,
        format=None,
        usage=None,
        data: bytes | bytearray | memoryview | None = None,
        bytes_per_pixel: int = 4,
    ):
        self.device = device

        self.width = int(
            width
        )

        self.height = int(
            height
        )

        if (
            self.width <= 0
            or self.height <= 0
        ):
            raise ValueError(
                "Texture dimensions must be greater than zero"
            )

        # ======================================================
        # Format
        # ======================================================

        if format is None:
            format = (
                sdl3.SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM
            )

        self.format = format

        # ======================================================
        # Usage
        # ======================================================

        if usage is None:
            usage = (
                sdl3.SDL_GPU_TEXTUREUSAGE_SAMPLER
            )

        self.usage = usage

        # ======================================================
        # Pixel information
        # ======================================================

        self.bytes_per_pixel = int(
            bytes_per_pixel
        )

        if self.bytes_per_pixel <= 0:
            raise ValueError(
                "bytes_per_pixel must be greater than zero"
            )

        # ======================================================
        # GPU handle
        # ======================================================

        self.texture = None

        # ======================================================
        # Create
        # ======================================================

        self._create()

        # ======================================================
        # Optional initial upload
        # ======================================================

        if data is not None:
            self.upload(
                data
            )

    # ==========================================================
    # Error handling
    # ==========================================================

    def _check(
        self,
        condition,
        message: str,
    ):
        if condition:
            return

        error = (
            sdl3.SDL_GetError()
        )

        if isinstance(
            error,
            bytes,
        ):
            error = error.decode(
                "utf-8",
                errors="replace",
            )

        raise RuntimeError(
            f"{message}: {error}"
        )

    # ==========================================================
    # Create texture
    # ==========================================================

    def _create(
        self,
    ):
        info = (
            sdl3.SDL_GPUTextureCreateInfo()
        )

        info.type = (
            sdl3.SDL_GPU_TEXTURETYPE_2D
        )

        info.format = (
            self.format
        )

        info.usage = (
            self.usage
        )

        info.width = (
            self.width
        )

        info.height = (
            self.height
        )

        info.layer_count_or_depth = 1

        info.num_levels = 1

        info.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        info.props = 0

        self.texture = (
            sdl3.SDL_CreateGPUTexture(
                self.device,
                ctypes.byref(
                    info
                ),
            )
        )

        self._check(
            self.texture,
            "SDL_CreateGPUTexture failed",
        )

    # ==========================================================
    # Upload
    # ==========================================================

    def upload(
        self,
        data: bytes
        | bytearray
        | memoryview,
    ):
        """
        Upload pixel data into the texture.

        The byte size must exactly match:

            width
            * height
            * bytes_per_pixel
        """

        data = bytes(
            data
        )

        expected_size = (
            self.width
            * self.height
            * self.bytes_per_pixel
        )

        if (
            len(data)
            != expected_size
        ):
            raise ValueError(
                f"Texture data has wrong size: "
                f"expected {expected_size} bytes, "
                f"got {len(data)}"
            )

        # ------------------------------------------------------
        # Transfer buffer
        # ------------------------------------------------------

        transfer_info = (
            sdl3.SDL_GPUTransferBufferCreateInfo()
        )

        transfer_info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )

        transfer_info.size = (
            len(data)
        )

        transfer_info.props = 0

        transfer_buffer = (
            sdl3.SDL_CreateGPUTransferBuffer(
                self.device,
                ctypes.byref(
                    transfer_info
                ),
            )
        )

        self._check(
            transfer_buffer,
            "SDL_CreateGPUTransferBuffer failed",
        )

        try:
            # --------------------------------------------------
            # Map transfer buffer
            # --------------------------------------------------

            mapped = (
                sdl3.SDL_MapGPUTransferBuffer(
                    self.device,
                    transfer_buffer,
                    False,
                )
            )

            self._check(
                mapped,
                "SDL_MapGPUTransferBuffer failed",
            )

            # --------------------------------------------------
            # Copy data into mapped buffer
            # --------------------------------------------------

            ctypes.memmove(
                mapped,
                data,
                len(data),
            )

            # --------------------------------------------------
            # Unmap
            # --------------------------------------------------

            sdl3.SDL_UnmapGPUTransferBuffer(
                self.device,
                transfer_buffer,
            )

            # --------------------------------------------------
            # Acquire command buffer
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

            try:
                # ----------------------------------------------
                # Begin copy pass
                # ----------------------------------------------

                copy_pass = (
                    sdl3.SDL_BeginGPUCopyPass(
                        command_buffer
                    )
                )

                self._check(
                    copy_pass,
                    "SDL_BeginGPUCopyPass failed",
                )

                # ----------------------------------------------
                # Source transfer info
                # ----------------------------------------------

                source = (
                    sdl3.SDL_GPUTextureTransferInfo()
                )

                source.transfer_buffer = (
                    transfer_buffer
                )

                source.offset = 0

                source.pixels_per_row = (
                    self.width
                )

                source.rows_per_layer = (
                    self.height
                )

                # ----------------------------------------------
                # Destination region
                # ----------------------------------------------

                destination = (
                    sdl3.SDL_GPUTextureRegion()
                )

                destination.texture = (
                    self.texture
                )

                destination.mip_level = 0

                destination.layer = 0

                destination.x = 0
                destination.y = 0
                destination.z = 0

                destination.w = (
                    self.width
                )

                destination.h = (
                    self.height
                )

                destination.d = 1

                # ----------------------------------------------
                # Upload
                # ----------------------------------------------

                sdl3.SDL_UploadToGPUTexture(
                    copy_pass,
                    source,
                    destination,
                    False,
                )

                # ----------------------------------------------
                # End copy pass
                # ----------------------------------------------

                sdl3.SDL_EndGPUCopyPass(
                    copy_pass
                )

                # ----------------------------------------------
                # Submit command buffer
                # ----------------------------------------------

                submitted = (
                    sdl3.SDL_SubmitGPUCommandBuffer(
                        command_buffer
                    )
                )

                self._check(
                    submitted,
                    "Texture upload submit failed",
                )

                # ----------------------------------------------
                # Wait until upload is finished
                # ----------------------------------------------

                sdl3.SDL_WaitForGPUIdle(
                    self.device
                )

            except Exception:
                try:
                    sdl3.SDL_CancelGPUCommandBuffer(
                        command_buffer
                    )

                except Exception:
                    pass

                raise

        finally:
            sdl3.SDL_ReleaseGPUTransferBuffer(
                self.device,
                transfer_buffer,
            )

    # ==========================================================
    # Destroy
    # ==========================================================

    def destroy(
        self,
    ):
        if self.texture is None:
            return

        sdl3.SDL_ReleaseGPUTexture(
            self.device,
            self.texture,
        )

        self.texture = None

    # ==========================================================
    # Context manager
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