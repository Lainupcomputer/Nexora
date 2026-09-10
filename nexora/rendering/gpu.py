from __future__ import annotations

import ctypes

import sdl3

from nexora.threading.context import ThreadContext


class GPUError(RuntimeError):
    """Raised when an SDL GPU operation fails."""


class GPUContext:
    """
    Native SDL3 GPU backend for Nexora.

    Owns:
        - SDL3 window
        - SDL_GPU device
        - GPU swapchain
        - per-frame command buffer

    All GPU operations are main-thread-only.
    """

    def __init__(
        self,
        width: int,
        height: int,
        title: str = "Nexora GPU",
        *,
        resizable: bool = True,
        debug: bool = False,
        allowed_frames_in_flight: int = 2,
    ) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.__init__"
        )

        if width <= 0 or height <= 0:
            raise ValueError(
                "GPU window dimensions must be greater than 0."
            )

        if not 1 <= allowed_frames_in_flight <= 3:
            raise ValueError(
                "allowed_frames_in_flight must be between 1 and 3."
            )

        self.width = width
        self.height = height
        self.title = title
        self.debug = debug
        self.allowed_frames_in_flight = (
            allowed_frames_in_flight
        )

        self.window = None
        self.device = None

        self._claimed = False
        self._destroyed = False

        self._command_buffer = None
        self._swapchain_texture = None

        self._swapchain_width = 0
        self._swapchain_height = 0

        self._frame_active = False
        self._render_pass_active = False

        self._initialize_sdl()
        self._create_window(resizable)
        self._create_device()
        self._claim_window()
        self._configure_device()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_sdl(self) -> None:
        if not sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO):
            raise GPUError(
                "SDL_Init failed: "
                f"{self._get_error()}"
            )

    def _create_window(
        self,
        resizable: bool,
    ) -> None:
        flags = 0

        if resizable:
            flags |= sdl3.SDL_WINDOW_RESIZABLE

        self.window = sdl3.SDL_CreateWindow(
            self.title.encode("utf-8"),
            self.width,
            self.height,
            flags,
        )

        if not self.window:
            sdl3.SDL_Quit()

            raise GPUError(
                "SDL_CreateWindow failed: "
                f"{self._get_error()}"
            )

    def _create_device(self) -> None:
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

        if not self.device:
            self._destroy_window()

            raise GPUError(
                "SDL_CreateGPUDevice failed: "
                f"{self._get_error()}"
            )

    def _claim_window(self) -> None:
        if not sdl3.SDL_ClaimWindowForGPUDevice(
            self.device,
            self.window,
        ):
            self._destroy_device()
            self._destroy_window()

            raise GPUError(
                "SDL_ClaimWindowForGPUDevice failed: "
                f"{self._get_error()}"
            )

        self._claimed = True

    def _configure_device(self) -> None:
        if not sdl3.SDL_SetGPUAllowedFramesInFlight(
            self.device,
            self.allowed_frames_in_flight,
        ):
            self.destroy()

            raise GPUError(
                "SDL_SetGPUAllowedFramesInFlight failed: "
                f"{self._get_error()}"
            )

    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------

    @property
    def driver(self) -> str:
        ThreadContext.assert_main_thread(
            "GPUContext.driver"
        )

        if self.device is None:
            return ""

        value = sdl3.SDL_GetGPUDeviceDriver(
            self.device
        )

        if not value:
            return ""

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="replace",
            )

        return str(value)

    @property
    def swapchain_format(self):
        ThreadContext.assert_main_thread(
            "GPUContext.swapchain_format"
        )

        if not self.device or not self.window:
            return None

        return sdl3.SDL_GetGPUSwapchainTextureFormat(
            self.device,
            self.window,
        )

    @property
    def swapchain_size(self) -> tuple[int, int]:
        return (
            self._swapchain_width,
            self._swapchain_height,
        )

    @property
    def command_buffer(self):
        return self._command_buffer

    @property
    def swapchain_texture(self):
        return self._swapchain_texture

    @property
    def active(self) -> bool:
        return (
            self.device is not None
            and self.window is not None
            and self._claimed
            and not self._destroyed
        )

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------

    def begin_frame(self):
        ThreadContext.assert_main_thread(
            "GPUContext.begin_frame"
        )

        if not self.active:
            raise GPUError(
                "GPUContext is not active."
            )

        if self._frame_active:
            raise GPUError(
                "A GPU frame is already active."
            )

        command_buffer = (
            sdl3.SDL_AcquireGPUCommandBuffer(
                self.device
            )
        )

        if not command_buffer:
            raise GPUError(
                "SDL_AcquireGPUCommandBuffer failed: "
                f"{self._get_error()}"
            )

        self._command_buffer = command_buffer

        texture = sdl3.LP_SDL_GPUTexture()

        width = ctypes.c_uint32()
        height = ctypes.c_uint32()

        success = (
            sdl3.SDL_WaitAndAcquireGPUSwapchainTexture(
                command_buffer,
                self.window,
                ctypes.byref(texture),
                ctypes.byref(width),
                ctypes.byref(height),
            )
        )

        if not success:
            self._cancel_frame()

            raise GPUError(
                "SDL_WaitAndAcquireGPUSwapchainTexture failed: "
                f"{self._get_error()}"
            )

        self._swapchain_texture = texture
        self._swapchain_width = width.value
        self._swapchain_height = height.value

        self._frame_active = True

        # A NULL texture is valid when the window is minimized.
        if not self._swapchain_texture:
            return None

        return self._command_buffer

    def begin_render_pass(
        self,
        clear_color: tuple[
            float,
            float,
            float,
            float,
        ] = (0.03, 0.05, 0.08, 1.0),
    ):
        ThreadContext.assert_main_thread(
            "GPUContext.begin_render_pass"
        )

        if not self._frame_active:
            raise GPUError(
                "No active GPU frame."
            )

        if self._render_pass_active:
            raise GPUError(
                "A GPU render pass is already active."
            )

        if self._swapchain_texture is None:
            return None

        if len(clear_color) != 4:
            raise ValueError(
                "clear_color must contain 4 values."
            )

        color_target = (
            sdl3.SDL_GPUColorTargetInfo()
        )

        color_target.texture = (
            self._swapchain_texture
        )

        color_target.clear_color = (
            sdl3.SDL_FColor(
                float(clear_color[0]),
                float(clear_color[1]),
                float(clear_color[2]),
                float(clear_color[3]),
            )
        )

        color_target.load_op = (
            sdl3.SDL_GPU_LOADOP_CLEAR
        )

        color_target.store_op = (
            sdl3.SDL_GPU_STOREOP_STORE
        )

        render_pass = (
            sdl3.SDL_BeginGPURenderPass(
                self._command_buffer,
                ctypes.byref(color_target),
                1,
                None,
            )
        )

        if not render_pass:
            raise GPUError(
                "SDL_BeginGPURenderPass failed: "
                f"{self._get_error()}"
            )

        self._render_pass_active = True

        return render_pass

    def end_render_pass(
        self,
        render_pass,
    ) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.end_render_pass"
        )

        if render_pass is None:
            return

        if not self._render_pass_active:
            raise GPUError(
                "No active GPU render pass."
            )

        sdl3.SDL_EndGPURenderPass(
            render_pass
        )

        self._render_pass_active = False

    def end_frame(self) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.end_frame"
        )

        if not self._frame_active:
            raise GPUError(
                "No active GPU frame."
            )

        if self._render_pass_active:
            raise GPUError(
                "Cannot end GPU frame while a render pass "
                "is still active."
            )

        command_buffer = self._command_buffer

        self._command_buffer = None
        self._swapchain_texture = None
        self._swapchain_width = 0
        self._swapchain_height = 0
        self._frame_active = False

        if not sdl3.SDL_SubmitGPUCommandBuffer(
            command_buffer
        ):
            raise GPUError(
                "SDL_SubmitGPUCommandBuffer failed: "
                f"{self._get_error()}"
            )

    def cancel_frame(self) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.cancel_frame"
        )

        if not self._frame_active:
            return

        self._cancel_frame()

    def _cancel_frame(self) -> None:
        if self._command_buffer is not None:
            sdl3.SDL_CancelGPUCommandBuffer(
                self._command_buffer
            )

        self._command_buffer = None
        self._swapchain_texture = None
        self._swapchain_width = 0
        self._swapchain_height = 0
        self._frame_active = False
        self._render_pass_active = False

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def wait_idle(self) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.wait_idle"
        )

        if self.device is None:
            return

        if not sdl3.SDL_WaitForGPUIdle(
            self.device
        ):
            raise GPUError(
                "SDL_WaitForGPUIdle failed: "
                f"{self._get_error()}"
            )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _destroy_device(self) -> None:
        if self.device is None:
            return

        if self._claimed and self.window is not None:
            sdl3.SDL_ReleaseWindowFromGPUDevice(
                self.device,
                self.window,
            )

        self._claimed = False

        sdl3.SDL_DestroyGPUDevice(
            self.device
        )

        self.device = None

    def _destroy_window(self) -> None:
        if self.window is None:
            return

        sdl3.SDL_DestroyWindow(
            self.window
        )

        self.window = None

    def destroy(self) -> None:
        ThreadContext.assert_main_thread(
            "GPUContext.destroy"
        )

        if self._destroyed:
            return

        if self._frame_active:
            self._cancel_frame()

        if self.device is not None:
            self.wait_idle()

        self._destroy_device()
        self._destroy_window()

        sdl3.SDL_Quit()

        self._destroyed = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_error() -> str:
        error = sdl3.SDL_GetError()

        if not error:
            return "unknown SDL error"

        if isinstance(error, bytes):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        return str(error)