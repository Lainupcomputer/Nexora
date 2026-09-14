from __future__ import annotations

import ctypes
from enum import Enum

import sdl3


class WindowMode(str, Enum):
    """
    Nexora window modes.
    """

    WINDOWED = "windowed"
    BORDERLESS = "borderless"
    FULLSCREEN = "fullscreen"


class GPUContext:
    """
    SDL_GPU rendering context.

    Owns:
        - SDL video/events subsystem
        - SDL window
        - GPU device
        - swapchain
        - per-frame command buffer
        - window mode
        - VSync configuration

    All SDL/GPU operations are expected to happen on the
    thread that created the context.
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
        resizable=False,
        window_mode=WindowMode.WINDOWED,
    ):
        self.width = int(width)
        self.height = int(height)
        self.title = str(title)

        if self.width <= 0:
            raise ValueError(
                "Window width must be greater than 0."
            )

        if self.height <= 0:
            raise ValueError(
                "Window height must be greater than 0."
            )

        self.debug = bool(debug)

        self.frames_in_flight = max(
            1,
            min(3, int(frames_in_flight)),
        )

        self.vsync = bool(vsync)
        self.resizable = bool(resizable)

        self.window_mode = WindowMode(
            window_mode
        )

        self.window = None
        self.device = None

        self.command_buffer = None
        self.swapchain_texture = None

        self.swapchain_width = 0
        self.swapchain_height = 0

        self.frame_active = False
        self.initialized = False

        self._initialize()

    # ==============================================================
    # Helpers
    # ==============================================================

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
        message,
    ):
        if condition:
            return

        error = self._decode_error(
            sdl3.SDL_GetError()
        )

        raise RuntimeError(
            f"{message}: {error}"
        )

    # ==============================================================
    # Initialization
    # ==============================================================

    def _initialize(
        self,
    ):
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

    def _create_window(
        self,
    ):
        flags = 0

        if self.resizable:
            flags |= (
                sdl3.SDL_WINDOW_RESIZABLE
            )

        if (
            self.window_mode
            == WindowMode.BORDERLESS
        ):
            flags |= (
                sdl3.SDL_WINDOW_BORDERLESS
            )

        elif (
            self.window_mode
            == WindowMode.FULLSCREEN
        ):
            flags |= (
                sdl3.SDL_WINDOW_FULLSCREEN
            )

        self.window = (
            sdl3.SDL_CreateWindow(
                self.title.encode(
                    "utf-8"
                ),
                self.width,
                self.height,
                flags,
            )
        )

        self._check(
            self.window,
            "SDL_CreateWindow failed",
        )

    def _create_device(
        self,
    ):
        shader_formats = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            | sdl3.SDL_GPU_SHADERFORMAT_DXIL
            | sdl3.SDL_GPU_SHADERFORMAT_MSL
        )

        self.device = (
            sdl3.SDL_CreateGPUDevice(
                shader_formats,
                self.debug,
                None,
            )
        )

        self._check(
            self.device,
            "SDL_CreateGPUDevice failed",
        )

    def _claim_window(
        self,
    ):
        self._check(
            sdl3.SDL_ClaimWindowForGPUDevice(
                self.device,
                self.window,
            ),
            "SDL_ClaimWindowForGPUDevice failed",
        )

    def _configure_swapchain(
        self,
    ):
        if self.vsync:
            present_mode = (
                sdl3.SDL_GPU_PRESENTMODE_VSYNC
            )

        else:
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
                    "GPU present mode IMMEDIATE is not "
                    "supported. Falling back to VSYNC."
                )

                self.vsync = True

                present_mode = (
                    sdl3.SDL_GPU_PRESENTMODE_VSYNC
                )

        self._check(
            sdl3.SDL_SetGPUSwapchainParameters(
                self.device,
                self.window,
                sdl3.SDL_GPU_SWAPCHAINCOMPOSITION_SDR,
                present_mode,
            ),
            "SDL_SetGPUSwapchainParameters failed",
        )

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def driver(
        self,
    ) -> str:
        if not self.device:
            return "<unknown>"

        driver = (
            sdl3.SDL_GetGPUDeviceDriver(
                self.device
            )
        )

        if not driver:
            return "<unknown>"

        if isinstance(
            driver,
            bytes,
        ):
            return driver.decode(
                "utf-8",
                errors="replace",
            )

        return str(
            driver
        )

    @property
    def swapchain_format(
        self,
    ):
        if (
            not self.device
            or not self.window
        ):
            return 0

        return (
            sdl3.SDL_GetGPUSwapchainTextureFormat(
                self.device,
                self.window,
            )
        )

    @property
    def size(
        self,
    ):
        return (
            self.swapchain_width,
            self.swapchain_height,
        )

    @property
    def is_fullscreen(
        self,
    ) -> bool:
        return (
            self.window_mode
            == WindowMode.FULLSCREEN
        )

    @property
    def is_borderless(
        self,
    ) -> bool:
        return (
            self.window_mode
            == WindowMode.BORDERLESS
        )

    @property
    def is_windowed(
        self,
    ) -> bool:
        return (
            self.window_mode
            == WindowMode.WINDOWED
        )

    # ==============================================================
    # Frame handling
    # ==============================================================

    def begin_frame(
        self,
    ) -> bool:
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

        texture = ctypes.POINTER(
            sdl3.SDL_GPUTexture
        )()

        width = ctypes.c_uint32()
        height = ctypes.c_uint32()

        acquired = (
            sdl3.SDL_WaitAndAcquireGPUSwapchainTexture(
                self.command_buffer,
                self.window,
                ctypes.byref(
                    texture
                ),
                ctypes.byref(
                    width
                ),
                ctypes.byref(
                    height
                ),
            )
        )

        if not acquired:
            sdl3.SDL_CancelGPUCommandBuffer(
                self.command_buffer
            )

            self.command_buffer = None

            return False

        self.swapchain_texture = (
            texture
        )

        self.swapchain_width = (
            width.value
        )

        self.swapchain_height = (
            height.value
        )

        # SDL can return no texture when the window is
        # minimized or temporarily unavailable.
        if not texture:
            sdl3.SDL_SubmitGPUCommandBuffer(
                self.command_buffer
            )

            self.command_buffer = None
            self.swapchain_texture = None

            return False

        self.frame_active = True

        return True

    def begin_render_pass(
        self,
        clear_color,
        *,
        target_texture=None,
    ):
        """
        Begin a GPU render pass.

        If target_texture is None, the current swapchain
        texture is used.

        Otherwise target_texture must be a valid SDL_GPUTexture
        created with SDL_GPU_TEXTUREUSAGE_COLOR_TARGET.

        This allows rendering into offscreen textures for
        post-processing before drawing the final result into
        the swapchain.
        """

        if not self.frame_active:
            raise RuntimeError(
                "No active GPU frame"
            )

        # ------------------------------------------------------
        # Resolve render target
        # ------------------------------------------------------

        if target_texture is None:
            render_target = (
                self.swapchain_texture
            )

        else:
            render_target = (
                target_texture
            )

        if not render_target:
            raise RuntimeError(
                "Render target texture is not available"
            )

        # ------------------------------------------------------
        # Color target
        # ------------------------------------------------------

        target = (
            sdl3.SDL_GPUColorTargetInfo()
        )

        target.texture = (
            render_target
        )

        target.mip_level = 0

        target.layer_or_depth_plane = 0

        target.clear_color = (
            sdl3.SDL_FColor(
                float(
                    clear_color[0]
                ),
                float(
                    clear_color[1]
                ),
                float(
                    clear_color[2]
                ),
                float(
                    clear_color[3]
                ),
            )
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

        target.cycle_resolve_texture = (
            False
        )

        # ------------------------------------------------------
        # Begin render pass
        # ------------------------------------------------------

        render_pass = (
            sdl3.SDL_BeginGPURenderPass(
                self.command_buffer,
                ctypes.byref(
                    target
                ),
                1,
                None,
            )
        )

        self._check(
            render_pass,
            "SDL_BeginGPURenderPass failed",
        )

        return render_pass

    def end_render_pass(
        self,
        render_pass,
    ):
        if render_pass:
            sdl3.SDL_EndGPURenderPass(
                render_pass
            )

    def end_frame(
        self,
    ):
        if not self.frame_active:
            return

        command_buffer = (
            self.command_buffer
        )

        self.command_buffer = None

        self.swapchain_texture = None

        self.frame_active = False

        if not sdl3.SDL_SubmitGPUCommandBuffer(
            command_buffer
        ):
            error = (
                self._decode_error(
                    sdl3.SDL_GetError()
                )
            )

            raise RuntimeError(
                "SDL_SubmitGPUCommandBuffer failed: "
                + error
            )

    def cancel_frame(
        self,
    ):
        if self.command_buffer:
            sdl3.SDL_CancelGPUCommandBuffer(
                self.command_buffer
            )

        self.command_buffer = None

        self.swapchain_texture = None

        self.frame_active = False

    def wait_idle(
        self,
    ):
        if self.device:
            self._check(
                sdl3.SDL_WaitForGPUIdle(
                    self.device
                ),
                "SDL_WaitForGPUIdle failed",
            )

    # ==============================================================
    # SDL3 Events
    # ==============================================================

    def poll_events(
        self,
    ):
        """
        Poll all pending SDL3 events.

        A fresh SDL_Event structure is created for every
        event. This prevents the yielded event from being
        overwritten by a subsequent SDL_PollEvent call.
        """

        while True:
            event = (
                sdl3.SDL_Event()
            )

            if not sdl3.SDL_PollEvent(
                ctypes.byref(
                    event
                )
            ):
                break

            yield event

    # ==============================================================
    # Window Size
    # ==============================================================

    def resize(
        self,
        width: int,
        height: int,
    ):
        """
        Request a new window size.

        SDL3 treats this as an asynchronous request. The
        actual size is updated when SDL reports the resulting
        resize and when the swapchain is acquired.
        """

        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        if width <= 0:
            raise ValueError(
                "Window width must be greater than 0."
            )

        if height <= 0:
            raise ValueError(
                "Window height must be greater than 0."
            )

        self._check(
            sdl3.SDL_SetWindowSize(
                self.window,
                int(
                    width
                ),
                int(
                    height
                ),
            ),
            "SDL_SetWindowSize failed",
        )

    # ==============================================================
    # Window Modes
    # ==============================================================

    def set_windowed(
        self,
    ):
        """
        Switch to normal decorated window mode.
        """

        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        self._check(
            sdl3.SDL_SetWindowFullscreen(
                self.window,
                False,
            ),
            "SDL_SetWindowFullscreen(false) failed",
        )

        self._check(
            sdl3.SDL_SetWindowBordered(
                self.window,
                True,
            ),
            "SDL_SetWindowBordered(true) failed",
        )

        self.window_mode = (
            WindowMode.WINDOWED
        )

    def set_borderless(
        self,
    ):
        """
        Switch to a borderless window.

        The current window size is preserved. This is a
        borderless window, not fullscreen.
        """

        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        self._check(
            sdl3.SDL_SetWindowFullscreen(
                self.window,
                False,
            ),
            "SDL_SetWindowFullscreen(false) failed",
        )

        self._check(
            sdl3.SDL_SetWindowBordered(
                self.window,
                False,
            ),
            "SDL_SetWindowBordered(false) failed",
        )

        self.window_mode = (
            WindowMode.BORDERLESS
        )

    def set_fullscreen(
        self,
    ):
        """
        Switch to SDL3 fullscreen.

        SDL3 uses borderless fullscreen desktop mode when
        no explicit fullscreen display mode is selected.
        """

        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        self._check(
            sdl3.SDL_SetWindowFullscreen(
                self.window,
                True,
            ),
            "SDL_SetWindowFullscreen(true) failed",
        )

        self.window_mode = (
            WindowMode.FULLSCREEN
        )

    def set_window_mode(
        self,
        mode: WindowMode | str,
    ):
        """
        Set the current window mode.
        """

        mode = WindowMode(
            mode
        )

        if (
            mode
            == WindowMode.WINDOWED
        ):
            self.set_windowed()

        elif (
            mode
            == WindowMode.BORDERLESS
        ):
            self.set_borderless()

        elif (
            mode
            == WindowMode.FULLSCREEN
        ):
            self.set_fullscreen()

    def toggle_fullscreen(
        self,
    ):
        """
        Toggle between fullscreen and windowed mode.
        """

        if (
            self.window_mode
            == WindowMode.FULLSCREEN
        ):
            self.set_windowed()

        else:
            self.set_fullscreen()

    # ==============================================================
    # VSync
    # ==============================================================

    def set_vsync(
        self,
        enabled: bool,
    ):
        """
        Enable or disable GPU presentation VSync.

        If IMMEDIATE presentation is unsupported, SDL falls
        back to VSYNC automatically.
        """

        if not self.initialized:
            raise RuntimeError(
                "GPUContext is not initialized"
            )

        enabled = bool(
            enabled
        )

        if enabled:
            present_mode = (
                sdl3.SDL_GPU_PRESENTMODE_VSYNC
            )

        else:
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
                    "GPU present mode IMMEDIATE is not "
                    "supported. Keeping VSYNC enabled."
                )

                self.vsync = True

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

        self.vsync = enabled

    # ==============================================================
    # Shutdown
    # ==============================================================

    def destroy(
        self,
    ):
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

        if (
            self.device
            and self.window
        ):
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

    # ==============================================================
    # Context Manager
    # ==============================================================

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