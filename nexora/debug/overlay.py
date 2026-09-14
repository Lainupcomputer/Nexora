from __future__ import annotations

import platform
import sys
import sysconfig

from nexora.debug.metrics import DebugMetrics


class DebugOverlay:
    """
    Global Nexora F3 debug overlay.

    The overlay belongs directly to the Engine instead of a Scene
    or UIRoot.

    It is intended to be rendered as the final engine overlay.
    """

    def __init__(
        self,
        engine,
    ) -> None:
        self.engine = engine

        self.visible = False

        self.metrics = (
            DebugMetrics()
        )

        # ======================================================
        # Appearance
        # ======================================================
        #
        # Larger than the previous debug overlay.
        # ======================================================

        self.text_scale = 1.05

        self.margin = 16.0
        self.line_spacing = 5.0

    # ==========================================================
    # VISIBILITY
    # ==========================================================

    def toggle(
        self,
    ) -> bool:
        self.visible = (
            not self.visible
        )

        return self.visible

    def show(
        self,
    ) -> None:
        self.visible = True

    def hide(
        self,
    ) -> None:
        self.visible = False

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.visible:
            return

        self.metrics.update(
            delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        left_lines = (
            self._build_left_lines()
        )

        right_lines = (
            self._build_right_lines(
                renderer
            )
        )

        self._draw_left(
            renderer,
            left_lines,
        )

        self._draw_right(
            renderer,
            right_lines,
        )

    # ==========================================================
    # LEFT SIDE
    # ==========================================================

    def _build_left_lines(
        self,
    ) -> list[str]:
        data = (
            self.metrics.snapshot
        )

        # ------------------------------------------------------
        # Time
        # ------------------------------------------------------

        time_system = (
            self.engine.time
        )

        fixed_delta = float(
            time_system.fixed_delta_time
        )

        fixed_fps = (
            1.0 / fixed_delta
            if fixed_delta > 0.0
            else 0.0
        )

        target_fps = int(
            self.engine.loop.target_fps
        )

        # ------------------------------------------------------
        # RAM
        # ------------------------------------------------------

        if (
            data.ram_used_mb
            >= 1024.0
        ):
            ram_text = (
                f"{data.ram_used_mb / 1024.0:.2f} GB"
            )

        else:
            ram_text = (
                f"{data.ram_used_mb:.0f} MB"
            )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = getattr(
            self.engine.game,
            "scene",
            None,
        )

        scene_name = (
            scene.name
            if scene is not None
            else "<none>"
        )

        return [
            (
                "FPS: "
                f"{data.fps:.0f} / "
                f"{target_fps}"
            ),

            (
                "Frame time: "
                f"{data.frame_time_ms:.2f} ms"
            ),

            (
                "Delta: "
                f"{data.delta_time:.4f} s"
            ),

            (
                "Tickrate: "
                f"{fixed_fps:.0f}"
            ),

            "",

            (
                "CPU: "
                f"{data.cpu_percent:.1f} %"
            ),

            (
                "RAM: "
                f"{ram_text}"
            ),

            "",

            (
                "Scene: "
                f"{scene_name}"
            ),
        ]

    # ==========================================================
    # RIGHT SIDE
    # ==========================================================

    def _build_right_lines(
        self,
        renderer,
    ) -> list[str]:
        data = (
            self.metrics.snapshot
        )

        context = (
            self.engine.gpu_context
        )

        # ------------------------------------------------------
        # Python / GIL
        # ------------------------------------------------------

        gil_function = getattr(
            sys,
            "_is_gil_enabled",
            None,
        )

        if gil_function is None:
            gil_enabled = True

        else:
            try:
                gil_enabled = bool(
                    gil_function()
                )

            except Exception:
                gil_enabled = True

        free_threaded = bool(
            sysconfig.get_config_var(
                "Py_GIL_DISABLED"
            )
        )

        python_mode = (
            "free-threaded"
            if free_threaded
            else "standard"
        )

        gil_text = (
            "enabled"
            if gil_enabled
            else "disabled"
        )

        # ------------------------------------------------------
        # Window
        # ------------------------------------------------------

        window_mode = getattr(
            context.window_mode,
            "value",
            str(
                context.window_mode
            ),
        )

        vsync = (
            "on"
            if context.vsync
            else "off"
        )

        # ------------------------------------------------------
        # GPU device
        # ------------------------------------------------------

        gpu_device = (
            data.gpu_device_name
            if data.gpu_device_name
            else "N/A"
        )

        # ------------------------------------------------------
        # Process GPU load
        # ------------------------------------------------------

        if (
            data.gpu_process_load_percent
            is None
        ):
            gpu_load = "N/A"

        else:
            gpu_load = (
                f"{data.gpu_process_load_percent:.1f} %"
            )

        # ------------------------------------------------------
        # Process GPU memory
        # ------------------------------------------------------

        if (
            data.gpu_process_memory_mb
            is None
        ):
            gpu_memory = "N/A"

        elif (
            data.gpu_process_memory_mb
            >= 1024.0
        ):
            gpu_memory = (
                f"{data.gpu_process_memory_mb / 1024.0:.2f} GB"
            )

        else:
            gpu_memory = (
                f"{data.gpu_process_memory_mb:.0f} MB"
            )

        # ------------------------------------------------------
        # Output
        # ------------------------------------------------------

        return [
            "Renderer",
            "------------------------",

            (
                "Python: "
                f"{platform.python_version()} "
                f"{python_mode}"
            ),

            (
                "GIL: "
                f"{gil_text}"
            ),

            (
                "Time scale: "
                f"{self.engine.time.time_scale:.2f}"
            ),

            "",

            (
                "Resolution: "
                f"{renderer.width}x"
                f"{renderer.height}"
            ),

            (
                "GPU Backend: "
                f"{context.driver}"
            ),

            (
                "GPU Device: "
                f"{gpu_device}"
            ),

            (
                "VSync: "
                f"{vsync}"
            ),

            (
                "Window: "
                f"{window_mode}"
            ),

            "",

            (
                "Game GPU Load: "
                f"{gpu_load}"
            ),

            (
                "Game GPU VRAM: "
                f"{gpu_memory}"
            ),
        ]

    # ==========================================================
    # TEXT LAYOUT
    # ==========================================================

    def _line_height(
        self,
        renderer,
    ) -> float:
        _, height = (
            renderer.text_measure(
                "Ag",
                scale=self.text_scale,
            )
        )

        return (
            height
            + self.line_spacing
        )

    # ==========================================================
    # LEFT DRAW
    # ==========================================================

    def _draw_left(
        self,
        renderer,
        lines: list[str],
    ) -> None:
        half_width = (
            renderer.width
            * 0.5
        )

        half_height = (
            renderer.height
            * 0.5
        )

        x = (
            -half_width
            + self.margin
        )

        y = (
            -half_height
            + self.margin
            + renderer.text_baseline(
                scale=self.text_scale
            )
        )

        line_height = (
            self._line_height(
                renderer
            )
        )

        for line in lines:
            if line:
                renderer.text(
                    line,
                    x,
                    y,
                    scale=self.text_scale,
                )

            y += (
                line_height
            )

    # ==========================================================
    # RIGHT DRAW
    # ==========================================================

    def _draw_right(
        self,
        renderer,
        lines: list[str],
    ) -> None:
        half_width = (
            renderer.width
            * 0.5
        )

        half_height = (
            renderer.height
            * 0.5
        )

        right = (
            half_width
            - self.margin
        )

        y = (
            -half_height
            + self.margin
            + renderer.text_baseline(
                scale=self.text_scale
            )
        )

        line_height = (
            self._line_height(
                renderer
            )
        )

        for line in lines:
            if line:
                width, _ = (
                    renderer.text_measure(
                        line,
                        scale=self.text_scale,
                    )
                )

                renderer.text(
                    line,
                    right - width,
                    y,
                    scale=self.text_scale,
                )

            y += (
                line_height
            )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        self.metrics.shutdown()