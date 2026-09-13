from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.rendering.postprocessing.post_process import (
        PostProcess,
    )


class PostProcessEffects:
    """
    Convenience wrapper around PostProcess effect values.

    This provides a cleaner public API while PostProcess remains
    responsible for GPU resources and shader uniform uploads.
    """

    def __init__(
        self,
        post_process: PostProcess,
    ) -> None:
        self._post = post_process

    # ==========================================================
    # Grayscale
    # ==========================================================

    def grayscale(
        self,
        amount: float = 1.0,
    ) -> None:
        self._post.grayscale = self._post._clamp(
            amount,
            0.0,
            1.0,
        )

    def disable_grayscale(
        self,
    ) -> None:
        self._post.grayscale = 0.0

    # ==========================================================
    # Vignette
    # ==========================================================

    def vignette(
        self,
        amount: float = 0.5,
    ) -> None:
        self._post.vignette = self._post._clamp(
            amount,
            0.0,
            1.0,
        )

    def disable_vignette(
        self,
    ) -> None:
        self._post.vignette = 0.0

    # ==========================================================
    # Brightness
    # ==========================================================

    def brightness(
        self,
        amount: float = 1.0,
    ) -> None:
        self._post.brightness = max(
            0.0,
            float(amount),
        )

    # ==========================================================
    # Contrast
    # ==========================================================

    def contrast(
        self,
        amount: float = 1.0,
    ) -> None:
        self._post.contrast = max(
            0.0,
            float(amount),
        )

    # ==========================================================
    # Saturation
    # ==========================================================

    def saturation(
        self,
        amount: float = 1.0,
    ) -> None:
        self._post.saturation = max(
            0.0,
            float(amount),
        )

    # ==========================================================
    # Tint
    # ==========================================================

    def tint(
        self,
        red: float = 1.0,
        green: float = 1.0,
        blue: float = 1.0,
    ) -> None:
        self._post.tint = (
            float(red),
            float(green),
            float(blue),
        )

    def cold_tint(
        self,
        strength: float = 1.0,
    ) -> None:
        strength = self._post._clamp(
            strength,
            0.0,
            1.0,
        )

        self._post.tint = (
            1.0 - 0.28 * strength,
            1.0 - 0.13 * strength,
            1.0,
        )

    def warm_tint(
        self,
        strength: float = 1.0,
    ) -> None:
        strength = self._post._clamp(
            strength,
            0.0,
            1.0,
        )

        self._post.tint = (
            1.0,
            1.0 - 0.10 * strength,
            1.0 - 0.25 * strength,
        )

    def clear_tint(
        self,
    ) -> None:
        self._post.tint = (
            1.0,
            1.0,
            1.0,
        )

    # ==========================================================
    # Chromatic aberration
    # ==========================================================

    def chromatic_aberration(
        self,
        amount: float = 4.0,
    ) -> None:
        self._post.chromatic_aberration = max(
            0.0,
            float(amount),
        )

    def disable_chromatic_aberration(
        self,
    ) -> None:
        self._post.chromatic_aberration = 0.0

    # ==========================================================
    # Film grain
    # ==========================================================

    def film_grain(
        self,
        amount: float = 0.35,
    ) -> None:
        self._post.film_grain = self._post._clamp(
            amount,
            0.0,
            1.0,
        )

    def disable_film_grain(
        self,
    ) -> None:
        self._post.film_grain = 0.0

    # ==========================================================
    # Scanlines
    # ==========================================================

    def scanlines(
        self,
        amount: float = 0.4,
        *,
        frequency: float = 1.0,
    ) -> None:
        self._post.scanlines = self._post._clamp(
            amount,
            0.0,
            1.0,
        )

        self._post.scanline_frequency = max(
            0.01,
            float(frequency),
        )

    def disable_scanlines(
        self,
    ) -> None:
        self._post.scanlines = 0.0

    # ==========================================================
    # Pixelation
    # ==========================================================

    def pixelation(
        self,
        size: float = 8.0,
    ) -> None:
        self._post.set_pixel_size(
            size
        )

    def disable_pixelation(
        self,
    ) -> None:
        self._post.pixel_size = 1.0

    # ==========================================================
    # Distortion
    # ==========================================================

    def distortion(
        self,
        amount: float = 0.5,
        *,
        speed: float = 1.0,
    ) -> None:
        self._post.distortion = max(
            0.0,
            float(amount),
        )

        self._post.distortion_speed = max(
            0.0,
            float(speed),
        )

    def disable_distortion(
        self,
    ) -> None:
        self._post.distortion = 0.0

    # ==========================================================
    # Low health / damage
    # ==========================================================

    def low_health(
        self,
        health: float,
        *,
        strength: float = 1.0,
    ) -> None:
        self._post.set_health(
            health
        )

        self._post.damage_pulse = self._post._clamp(
            strength,
            0.0,
            1.0,
        )

    def disable_low_health(
        self,
    ) -> None:
        self._post.health = 1.0
        self._post.damage_pulse = 0.0

    # ==========================================================
    # Presets
    # ==========================================================

    def cinematic(
        self,
    ) -> None:
        self._post.vignette = 0.35
        self._post.contrast = 1.1
        self._post.saturation = 0.9
        self._post.film_grain = 0.12

    def horror(
        self,
    ) -> None:
        self._post.vignette = 0.65
        self._post.saturation = 0.55
        self._post.contrast = 1.2
        self._post.film_grain = 0.35

        self._post.tint = (
            0.82,
            0.92,
            0.88,
        )

    def damaged(
        self,
    ) -> None:
        self._post.set_health(
            0.2
        )

        self._post.damage_pulse = 1.0

        self._post.chromatic_aberration = 3.0

        self._post.vignette = 0.45

    def retro(
        self,
    ) -> None:
        self._post.pixel_size = 4.0
        self._post.scanlines = 0.5
        self._post.scanline_frequency = 1.0
        self._post.saturation = 0.85
        self._post.contrast = 1.15

    # ==========================================================
    # Reset
    # ==========================================================

    def reset(
        self,
    ) -> None:
        self._post.reset()