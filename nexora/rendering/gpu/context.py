from __future__ import annotations

import ctypes

import sdl3


class GPUContext:
    """
    SDL_GPU rendering context.

    Owns:
        - SDL video/events subsystem
        - SDL window
        - GPU device
        - swapchain
        - per-frame command buffer

    All SDL/GPU operations are expected to happen on the thread
    that created the context.
    """

    def __init__(
        self,
        width,
        height,
        title="Nexora",
        *,
        debug=True,
        frames_in_flight=2,
        vsync=True,
    ):
        self.width = int(width)
        self.height = int(height)
        self.title = str(title)

        self.debug = bool(debug)
        self.frames_in_flight = max(
            1,
            min(3, int(frames_in_flight)),
        )
        self.vsync = bool(vsync)

        self.window = None
        self.device = None

        self.command_buffer = None
        self.swapchain_texture = None

        self.swapchain_width = 0
        self.swapchain_height = 0

        self.frame_active = False
        self.initialized = False

        self._initialize()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

    def _check(self, condition, message):
        if not condition:
            error = self._decode_error(
                sdl3.SDL_GetError()
            )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize(self):
        self._check(
            sdl3.SDL_Init(
                sdl3.SDL_INIT_VIDEO
                | sdl3.SDL_INIT_EVENTS
            ),
            "SDL_Init failed",
        )

        try:
            self._create_window()
            self._create_device()
            self._claim_window()
            self._configure_swapchain()

            self._check(
                sdl3.SDL_SetGPUAllowedFramesInFlight(
                    self.device,
                    self.frames_in_flight,
                ),
                "SDL_SetGPUAllowedFramesInFlight failed",
            )

            self.initialized = True

        except Exception:
            self.destroy()
            raise

    def _create_window(self):
        self.window = sdl3.SDL_CreateWindow(
            self.title.encode("utf-8"),
            self.width,
            self.height,
            0,
        )

        self._check(
            self.window,
            "SDL_CreateWindow failed",
        )

    def _create_device(self):
        shader_formats = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            | sdl3.SDL_GPU_SHADERFORMAT_DXIL
            | sdl3.SDL_GPU_SHADERFORMAT_MSL
        )

        self.device = sdl3.SDL_CreateGPUDevice(
            shader_formats,
            self.debug,
            None,
        )

        self._check(
            self.device,
            "SDL_CreateGPUDevice failed",
        )

    def _claim_window(self):
        self._check(
            sdl3.SDL_ClaimWindowForGPUDevice(
                self.device,
                self.window,
            ),
            "SDL_ClaimWindowForGPUDevice failed",
        )

    def _configure_swapchain(self):
        # VSYNC is SDL_GPU's default presentation mode.
        if self.vsync:
            return

        present_mode = (
            sdl3.SDL_GPU_PRESENTMODE_IMMEDIATE
        )

        supported = (
            sdl3.SDL_WindowSupportsGPUPresentMode(
                self.device,
                self.window,
                present_mode,
            )
        )

        if not supported:
            print(
                "GPU present mode IMMEDIATE is not supported. "
                "Falling back to VSYNC."
            )
            return

        self._check(
            sdl3.SDL_SetGPUSwapchainParameters(
                self.device,
                self.window,
                sdl3.SDL_GPU_SWAPCHAINCOMPOSITION_SDR,
                present_mode,
            ),
            "SDL_SetGPUSwapchainParameters failed",
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def driver(self) -> str:
        if not self.device:
            return "<unknown>"

        driver = sdl3.SDL_GetGPUDeviceDriver(
            self.device
        )

        if not driver:
            return "<unknown>"

        if isinstance(driver, bytes):
            return driver.decode(
                "utf-8",
                errors="replace",
            )

        return str(driver)

    @property
    def swapchain_format(self):
        if not self.device or not self.window:
            return 0

        return sdl3.SDL_GetGPUSwapchainTextureFormat(
            self.device,
            self.window,
        )

    @property
    def size(self):
        return (
            self.swapchain_width,
            self.swapchain_height,
        )

    # ------------------------------------------------------------------
    # Frame handling
    # ------------------------------------------------------------------

    def begin_frame(self) -> bool:
        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        if self.frame_active:
            raise RuntimeError(
                "GPU frame already active"
            )

        self.command_buffer = (
            sdl3.SDL_AcquireGPUCommandBuffer(
                self.device
            )
        )

        if not self.command_buffer:
            return False

        texture = sdl3.LP_SDL_GPUTexture()

        width = ctypes.c_uint32()
        height = ctypes.c_uint32()

        acquired = (
            sdl3.SDL_WaitAndAcquireGPUSwapchainTexture(
                self.command_buffer,
                self.window,
                ctypes.byref(texture),
                ctypes.byref(width),
                ctypes.byref(height),
            )
        )

        if not acquired:
            sdl3.SDL_CancelGPUCommandBuffer(
                self.command_buffer
            )

            self.command_buffer = None

            return False

        self.swapchain_texture = texture

        self.swapchain_width = width.value
        self.swapchain_height = height.value

        # SDL can return no texture when the window is minimized
        # or otherwise temporarily unavailable.
        if not texture:
            sdl3.SDL_SubmitGPUCommandBuffer(
                self.command_buffer
            )

            self.command_buffer = None
            self.swapchain_texture = None

            return False

        self.frame_active = True

        return True

    def begin_render_pass(self, clear_color):
        if not self.frame_active:
            raise RuntimeError(
                "No active GPU frame"
            )

        target = sdl3.SDL_GPUColorTargetInfo()

        target.texture = self.swapchain_texture
        target.mip_level = 0
        target.layer_or_depth_plane = 0

        target.clear_color = sdl3.SDL_FColor(
            float(clear_color[0]),
            float(clear_color[1]),
            float(clear_color[2]),
            float(clear_color[3]),
        )

        target.load_op = (
            sdl3.SDL_GPU_LOADOP_CLEAR
        )

        target.store_op = (
            sdl3.SDL_GPU_STOREOP_STORE
        )

        target.resolve_texture = None
        target.resolve_mip_level = 0
        target.resolve_layer = 0

        target.cycle = False
        target.cycle_resolve_texture = False

        render_pass = (
            sdl3.SDL_BeginGPURenderPass(
                self.command_buffer,
                ctypes.byref(target),
                1,
                None,
            )
        )

        self._check(
            render_pass,
            "SDL_BeginGPURenderPass failed",
        )

        return render_pass

    def end_render_pass(self, render_pass):
        if render_pass:
            sdl3.SDL_EndGPURenderPass(
                render_pass
            )

    def end_frame(self):
        if not self.frame_active:
            return

        command_buffer = self.command_buffer

        self.command_buffer = None
        self.swapchain_texture = None
        self.frame_active = False

        if not sdl3.SDL_SubmitGPUCommandBuffer(
            command_buffer
        ):
            error = self._decode_error(
                sdl3.SDL_GetError()
            )

            raise RuntimeError(
                "SDL_SubmitGPUCommandBuffer failed: "
                + error
            )

    def cancel_frame(self):
        if self.command_buffer:
            sdl3.SDL_CancelGPUCommandBuffer(
                self.command_buffer
            )

        self.command_buffer = None
        self.swapchain_texture = None
        self.frame_active = False

    def wait_idle(self):
        if self.device:
            self._check(
                sdl3.SDL_WaitForGPUIdle(
                    self.device
                ),
                "SDL_WaitForGPUIdle failed",
            )

    # ------------------------------------------------------------------
    # SDL3 Events
    # ------------------------------------------------------------------

    def poll_events(self):
        """
        Poll all pending SDL3 events.

        A fresh SDL_Event structure is created for every
        event. This prevents the yielded event from being
        overwritten by a subsequent SDL_PollEvent call.
        """

        while True:
            event = sdl3.SDL_Event()

            if not sdl3.SDL_PollEvent(
                ctypes.byref(event)
            ):
                break

            yield event

    # ------------------------------------------------------------------
    # Window
    # ------------------------------------------------------------------

    def resize(self, width, height):
        self.width = int(width)
        self.height = int(height)

        if self.window:
            sdl3.SDL_SetWindowSize(
                self.window,
                self.width,
                self.height,
            )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def destroy(self):
        if self.frame_active:
            try:
                self.cancel_frame()
            except Exception:
                pass

        if self.device:
            try:
                sdl3.SDL_WaitForGPUIdle(
                    self.device
                )
            except Exception:
                pass

        if self.device and self.window:
            try:
                sdl3.SDL_ReleaseWindowFromGPUDevice(
                    self.device,
                    self.window,
                )
            except Exception:
                pass

        if self.device:
            try:
                sdl3.SDL_DestroyGPUDevice(
                    self.device
                )
            except Exception:
                pass

        if self.window:
            try:
                sdl3.SDL_DestroyWindow(
                    self.window
                )
            except Exception:
                pass

        self.device = None
        self.window = None

        self.command_buffer = None
        self.swapchain_texture = None

        self.frame_active = False
        self.initialized = False

        self.swapchain_width = 0
        self.swapchain_height = 0

        try:
            sdl3.SDL_Quit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()