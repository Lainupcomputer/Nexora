from __future__ import annotations

import ctypes

import sdl3


class GPUSampler:
    """
    GPU sampler state.

    Controls how textures are sampled by shaders.
    """

    def __init__(
        self,
        device,
        *,
        min_filter=None,
        mag_filter=None,
        mipmap_mode=None,
        address_mode_u=None,
        address_mode_v=None,
        address_mode_w=None,
    ):
        self.device = device
        self.sampler = None

        if min_filter is None:
            min_filter = sdl3.SDL_GPU_FILTER_NEAREST

        if mag_filter is None:
            mag_filter = sdl3.SDL_GPU_FILTER_NEAREST

        if mipmap_mode is None:
            mipmap_mode = sdl3.SDL_GPU_SAMPLERMIPMAPMODE_NEAREST

        if address_mode_u is None:
            address_mode_u = sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE

        if address_mode_v is None:
            address_mode_v = sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE

        if address_mode_w is None:
            address_mode_w = sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE

        info = sdl3.SDL_GPUSamplerCreateInfo()

        info.min_filter = min_filter
        info.mag_filter = mag_filter
        info.mipmap_mode = mipmap_mode

        info.address_mode_u = address_mode_u
        info.address_mode_v = address_mode_v
        info.address_mode_w = address_mode_w

        info.mip_lod_bias = 0.0
        info.max_anisotropy = 1.0

        info.compare_op = sdl3.SDL_GPU_COMPAREOP_ALWAYS

        info.min_lod = 0.0
        info.max_lod = 0.0

        info.enable_anisotropy = False
        info.enable_compare = False

        info.props = 0

        self.sampler = sdl3.SDL_CreateGPUSampler(
            self.device,
            ctypes.byref(info),
        )

        if not self.sampler:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_CreateGPUSampler failed: {error}"
            )

    def destroy(self):
        if self.sampler:
            sdl3.SDL_ReleaseGPUSampler(
                self.device,
                self.sampler,
            )

            self.sampler = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()