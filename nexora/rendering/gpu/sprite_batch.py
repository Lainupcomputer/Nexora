from __future__ import annotations

import ctypes
import math
import os
import struct
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nexora.rendering.gpu.render_snapshot import RenderSnapshot

import sdl3

from nexora.rendering.gpu.buffer import GPUBuffer
from nexora.rendering.gpu.sampler import GPUSampler
from nexora.rendering.gpu.shader import GPUShader


class GPUSpriteBatch:
    """
    GPU-instanced sprite renderer.

    Supports both:

        batch.add(...)

    and high-performance bulk preparation:

        batch.add_many(sprites)

    Bulk preparation uses real worker threads when running on
    Python's free-threaded build.

    Worker threads only prepare CPU-side instance data.

    SDL / GPU operations remain on the rendering thread.
    """

    MAX_SPRITES = 50000

    INSTANCE_FLOATS = 14
    INSTANCE_STRIDE = 56

    CAMERA_UNIFORM_FLOATS = 8
    CAMERA_UNIFORM_SIZE = 32

    DEFAULT_WORKERS = 4

    PARALLEL_THRESHOLD = 2048

    def __init__(
        self,
        context,
        *,
        max_sprites: int = 10000,
        vertex_shader_path,
        fragment_shader_path,
        camera=None,
        workers: int = DEFAULT_WORKERS,
    ):
        self.context = context
        self.device = context.device

        self.max_sprites = int(
            max_sprites
        )

        if self.max_sprites <= 0:
            raise ValueError(
                "max_sprites must be greater than zero"
            )

        if self.max_sprites > self.MAX_SPRITES:
            raise ValueError(
                f"max_sprites cannot exceed "
                f"{self.MAX_SPRITES}"
            )

        self.camera = camera

        self.vertex_shader_path = Path(
            vertex_shader_path
        )

        self.fragment_shader_path = Path(
            fragment_shader_path
        )

        # ======================================================
        # Workers
        # ======================================================

        cpu_count = (
            os.cpu_count()
            or 1
        )

        self.worker_count = max(
            1,
            min(
                int(
                    workers
                ),
                cpu_count,
            ),
        )

        self._executor = (
            ThreadPoolExecutor(
                max_workers=self.worker_count,
                thread_name_prefix="nexora-sprite",
            )
        )

        # ======================================================
        # GPU resources
        # ======================================================

        self.vertex_shader = None
        self.fragment_shader = None

        self.quad_buffer = None
        self.instance_buffer = None

        self.sampler = None
        self.pipeline = None

        # ======================================================
        # CPU instance data
        # ======================================================

        self._instance_data = bytearray(
            self.max_sprites
            * self.INSTANCE_STRIDE
        )

        self._sprite_count = 0

        self._clip_rects: list[
            tuple[
                float,
                float,
                float,
                float,
            ] | None
        ] = []

        self._texture = None

        self._camera_data = bytearray(
            self.CAMERA_UNIFORM_SIZE
        )

        self._destroyed = False

        self._create_resources()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def submit_snapshot(
        self,
        snapshot: RenderSnapshot,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        count = len(
            snapshot
        )

        if count == 0:
            self._sprite_count = 0

            self._clip_rects.clear()

            return 0

        if count > self.max_sprites:
            raise RuntimeError(
                "RenderSnapshot exceeds SpriteBatch capacity "
                f"({count} > {self.max_sprites})"
            )

        snapshot_size = (
            count
            * self.INSTANCE_STRIDE
        )

        self._instance_data[
            :snapshot_size
        ] = snapshot.data[
            :snapshot_size
        ]

        self._sprite_count = count

        # Snapshots currently carry no clipping information.
        self._clip_rects = (
            [None] * count
        )

        return count

    # ==========================================================
    # ERROR
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
            return (
                "<unknown SDL error>"
            )

        return str(
            error
        )

    def _check(
        self,
        condition,
        message,
    ):
        if not condition:
            error = (
                self._decode_error(
                    sdl3.SDL_GetError()
                )
            )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ==========================================================
    # RESOURCE CREATION
    # ==========================================================

    def _create_resources(
        self,
    ):
        self._create_shaders()
        self._create_quad()
        self._create_instance_buffer()
        self._create_sampler()
        self._create_pipeline()

    # ==========================================================
    # SHADERS
    # ==========================================================

    def _create_shaders(
        self,
    ):
        self.vertex_shader = GPUShader(
            self.device,
            self.vertex_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
            num_uniform_buffers=1,
        )

        self.fragment_shader = GPUShader(
            self.device,
            self.fragment_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
            num_samplers=1,
        )

    # ==========================================================
    # QUAD
    # ==========================================================

    def _create_quad(
        self,
    ):
        """
        Quad vertices:

            position.xy
            uv.xy

        Six vertices = two triangles.
        """

        vertices = struct.pack(
            "<24f",

            # Triangle 1
            -0.5,
            -0.5,
            0.0,
            0.0,

            0.5,
            -0.5,
            1.0,
            0.0,

            0.5,
            0.5,
            1.0,
            1.0,

            # Triangle 2
            -0.5,
            -0.5,
            0.0,
            0.0,

            0.5,
            0.5,
            1.0,
            1.0,

            -0.5,
            0.5,
            0.0,
            1.0,
        )

        self.quad_buffer = GPUBuffer(
            self.device,
            len(
                vertices
            ),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
        )

    # ==========================================================
    # INSTANCE BUFFER
    # ==========================================================

    def _create_instance_buffer(
        self,
    ):
        self.instance_buffer = GPUBuffer(
            self.device,
            len(
                self._instance_data
            ),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=3,
        )

    # ==========================================================
    # SAMPLER
    # ==========================================================

    def _create_sampler(
        self,
    ):
        self.sampler = GPUSampler(
            self.device,
            min_filter=(
                sdl3.SDL_GPU_FILTER_NEAREST
            ),
            mag_filter=(
                sdl3.SDL_GPU_FILTER_NEAREST
            ),
            mipmap_mode=(
                sdl3.SDL_GPU_SAMPLERMIPMAPMODE_NEAREST
            ),
            address_mode_u=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
            address_mode_v=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
            address_mode_w=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
        )

    # ==========================================================
    # PIPELINE
    # ==========================================================

    def _create_pipeline(
        self,
    ):
        vertex_buffer_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription
            * 2
        )()

        vertex_buffer_descriptions[
            0
        ].slot = 0

        vertex_buffer_descriptions[
            0
        ].pitch = 16

        vertex_buffer_descriptions[
            0
        ].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )

        vertex_buffer_descriptions[
            0
        ].instance_step_rate = 0

        vertex_buffer_descriptions[
            1
        ].slot = 1

        vertex_buffer_descriptions[
            1
        ].pitch = (
            self.INSTANCE_STRIDE
        )

        vertex_buffer_descriptions[
            1
        ].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_INSTANCE
        )

        vertex_buffer_descriptions[
            1
        ].instance_step_rate = 0

        # ======================================================
        # Attributes
        # ======================================================

        attributes = (
            sdl3.SDL_GPUVertexAttribute
            * 11
        )()

        # Vertex position
        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        # Vertex UV
        attributes[1].location = 1
        attributes[1].buffer_slot = 0
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[1].offset = 8

        # Instance position
        attributes[2].location = 2
        attributes[2].buffer_slot = 1
        attributes[2].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[2].offset = 0

        # Instance size
        attributes[3].location = 3
        attributes[3].buffer_slot = 1
        attributes[3].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[3].offset = 8

        # Rotation
        attributes[4].location = 4
        attributes[4].buffer_slot = 1
        attributes[4].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[4].offset = 16

        # Origin
        attributes[5].location = 5
        attributes[5].buffer_slot = 1
        attributes[5].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[5].offset = 20

        # Alpha
        attributes[6].location = 6
        attributes[6].buffer_slot = 1
        attributes[6].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[6].offset = 28

        # Flip
        attributes[7].location = 7
        attributes[7].buffer_slot = 1
        attributes[7].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[7].offset = 32

        # UV origin
        attributes[8].location = 8
        attributes[8].buffer_slot = 1
        attributes[8].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[8].offset = 40

        # UV size
        attributes[9].location = 9
        attributes[9].buffer_slot = 1
        attributes[9].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[9].offset = 48

        # Padding / reserved
        attributes[10].location = 10
        attributes[10].buffer_slot = 1
        attributes[10].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[10].offset = 52

        # ======================================================
        # Rasterizer
        # ======================================================

        rasterizer = (
            sdl3.SDL_GPURasterizerState()
        )

        rasterizer.fill_mode = (
            sdl3.SDL_GPU_FILLMODE_FILL
        )

        rasterizer.cull_mode = (
            sdl3.SDL_GPU_CULLMODE_NONE
        )

        rasterizer.front_face = (
            sdl3.SDL_GPU_FRONTFACE_COUNTER_CLOCKWISE
        )

        rasterizer.enable_depth_bias = False
        rasterizer.enable_depth_clip = True

        # ======================================================
        # Multisample
        # ======================================================

        multisample = (
            sdl3.SDL_GPUMultisampleState()
        )

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False

        multisample.enable_alpha_to_coverage = (
            False
        )

        # ======================================================
        # Depth
        # ======================================================

        depth = (
            sdl3.SDL_GPUDepthStencilState()
        )

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # ======================================================
        # Color target
        # ======================================================

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        color_target.blend_state.enable_blend = (
            True
        )

        color_target.blend_state.src_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_SRC_ALPHA
        )

        color_target.blend_state.dst_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        color_target.blend_state.color_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        color_target.blend_state.src_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE
        )

        color_target.blend_state.dst_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        color_target.blend_state.alpha_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        color_target.blend_state.enable_color_write_mask = (
            True
        )

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription
            * 1
        )()

        color_targets[
            0
        ] = color_target

        # ======================================================
        # Target info
        # ======================================================

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1

        target_info.depth_stencil_format = 0

        target_info.has_depth_stencil_target = (
            False
        )

        # ======================================================
        # Vertex input
        # ======================================================

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = (
            vertex_buffer_descriptions
        )

        vertex_input.num_vertex_buffers = 2

        vertex_input.vertex_attributes = (
            attributes
        )

        vertex_input.num_vertex_attributes = 11

        # ======================================================
        # Pipeline
        # ======================================================

        info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        info.vertex_shader = (
            self.vertex_shader.shader
        )

        info.fragment_shader = (
            self.fragment_shader.shader
        )

        info.vertex_input_state = (
            vertex_input
        )

        info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        info.rasterizer_state = (
            rasterizer
        )

        info.multisample_state = (
            multisample
        )

        info.depth_stencil_state = (
            depth
        )

        info.target_info = (
            target_info
        )

        info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(
                    info
                ),
            )
        )

        self._check(
            self.pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )

    # ==========================================================
    # BEGIN
    # ==========================================================

    def begin(
        self,
        texture,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        self._texture = texture
        self._sprite_count = 0

        self._clip_rects.clear()

    # ==========================================================
    # ADD - SINGLE SPRITE
    # ==========================================================

    def add(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv=(
            0.0,
            0.0,
            1.0,
            1.0,
        ),
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
    ):
        if (
            self._sprite_count
            >= self.max_sprites
        ):
            raise RuntimeError(
                "GPUSpriteBatch capacity exceeded "
                f"({self.max_sprites} sprites)"
            )

        self._write_instance(
            self._sprite_count,
            x,
            y,
            width,
            height,
            rotation,
            origin,
            alpha,
            flip_x,
            flip_y,
            uv,
        )

        self._clip_rects.append(
            self._normalize_clip_rect(
                clip_rect
            )
        )

        self._sprite_count += 1

    # ==========================================================
    # WRITE INSTANCE
    # ==========================================================

    def _write_instance(
        self,
        index: int,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float,
        origin,
        alpha: float,
        flip_x: bool,
        flip_y: bool,
        uv,
    ):
        ox, oy = origin

        (
            uv_x,
            uv_y,
            uv_w,
            uv_h,
        ) = uv

        offset = (
            index
            * self.INSTANCE_STRIDE
        )

        struct.pack_into(
            "<14f",
            self._instance_data,
            offset,

            float(
                x
            ),
            float(
                y
            ),

            float(
                width
            ),
            float(
                height
            ),

            float(
                rotation
            ),

            float(
                ox
            ),
            float(
                oy
            ),

            float(
                alpha
            ),

            (
                1.0
                if flip_x
                else 0.0
            ),
            (
                1.0
                if flip_y
                else 0.0
            ),

            float(
                uv_x
            ),
            float(
                uv_y
            ),

            float(
                uv_w
            ),
            float(
                uv_h
            ),
        )

    # ==========================================================
    # BULK / PARALLEL PREPARATION
    # ==========================================================

    def add_many(
        self,
        sprites,
        *,
        workers: int | None = None,
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        if not hasattr(
            sprites,
            "__len__",
        ):
            sprites = list(
                sprites
            )

        count = len(
            sprites
        )

        if count == 0:
            return 0

        if (
            self._sprite_count
            + count
            > self.max_sprites
        ):
            raise RuntimeError(
                "GPUSpriteBatch capacity exceeded "
                f"({self.max_sprites} sprites)"
            )

        start_index = (
            self._sprite_count
        )

        normalized_clip = (
            self._normalize_clip_rect(
                clip_rect
            )
        )

        # ------------------------------------------------------
        # Small batch
        # ------------------------------------------------------

        if (
            count
            < self.PARALLEL_THRESHOLD
        ):
            self._write_range(
                sprites,
                0,
                count,
                start_index,
            )

            self._clip_rects.extend(
                [normalized_clip]
                * count
            )

            self._sprite_count += (
                count
            )

            return count

        # ------------------------------------------------------
        # Worker count
        # ------------------------------------------------------

        worker_count = (
            self.worker_count
            if workers is None
            else max(
                1,
                int(
                    workers
                ),
            )
        )

        worker_count = min(
            worker_count,
            count,
        )

        # ------------------------------------------------------
        # Chunks
        # ------------------------------------------------------

        chunk_size = (
            count
            + worker_count
            - 1
        ) // worker_count

        futures = []

        for worker_index in range(
            worker_count
        ):
            local_start = (
                worker_index
                * chunk_size
            )

            local_end = min(
                local_start
                + chunk_size,
                count,
            )

            if (
                local_start
                >= local_end
            ):
                break

            futures.append(
                self._executor.submit(
                    self._write_range,
                    sprites,
                    local_start,
                    local_end,
                    start_index
                    + local_start,
                )
            )

        for future in futures:
            future.result()

        self._clip_rects.extend(
            [normalized_clip]
            * count
        )

        self._sprite_count += (
            count
        )

        return count

    def _write_range(
        self,
        sprites,
        start: int,
        end: int,
        destination_start: int,
    ):
        for local_index in range(
            start,
            end,
        ):
            sprite = sprites[
                local_index
            ]

            (
                x,
                y,
                width,
                height,
                rotation,
                ox,
                oy,
                alpha,
                flip_x,
                flip_y,
                uv_x,
                uv_y,
                uv_w,
                uv_h,
            ) = sprite

            destination_index = (
                destination_start
                + (
                    local_index
                    - start
                )
            )

            offset = (
                destination_index
                * self.INSTANCE_STRIDE
            )

            struct.pack_into(
                "<14f",
                self._instance_data,
                offset,

                float(
                    x
                ),
                float(
                    y
                ),

                float(
                    width
                ),
                float(
                    height
                ),

                float(
                    rotation
                ),

                float(
                    ox
                ),
                float(
                    oy
                ),

                float(
                    alpha
                ),

                (
                    1.0
                    if flip_x
                    else 0.0
                ),
                (
                    1.0
                    if flip_y
                    else 0.0
                ),

                float(
                    uv_x
                ),
                float(
                    uv_y
                ),

                float(
                    uv_w
                ),
                float(
                    uv_h
                ),
            )

    # ==========================================================
    # CLIPPING
    # ==========================================================

    @staticmethod
    def _normalize_clip_rect(
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        if clip_rect is None:
            return None

        (
            x,
            y,
            width,
            height,
        ) = clip_rect

        return (
            float(
                x
            ),
            float(
                y
            ),
            max(
                float(
                    width
                ),
                0.0,
            ),
            max(
                float(
                    height
                ),
                0.0,
            ),
        )

    def _make_scissor_rect(
        self,
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None,
    ) -> sdl3.SDL_Rect:
        viewport_width = max(
            int(
                self.context.swapchain_width
            ),
            0,
        )

        viewport_height = max(
            int(
                self.context.swapchain_height
            ),
            0,
        )

        if clip_rect is None:
            left = 0
            top = 0

            right = (
                viewport_width
            )

            bottom = (
                viewport_height
            )

        else:
            (
                x,
                y,
                width,
                height,
            ) = clip_rect

            half_width = (
                viewport_width
                * 0.5
            )

            half_height = (
                viewport_height
                * 0.5
            )

            left = math.floor(
                x
                + half_width
            )

            top = math.floor(
                y
                + half_height
            )

            right = math.ceil(
                x
                + width
                + half_width
            )

            bottom = math.ceil(
                y
                + height
                + half_height
            )

            left = max(
                0,
                min(
                    left,
                    viewport_width,
                ),
            )

            top = max(
                0,
                min(
                    top,
                    viewport_height,
                ),
            )

            right = max(
                left,
                min(
                    right,
                    viewport_width,
                ),
            )

            bottom = max(
                top,
                min(
                    bottom,
                    viewport_height,
                ),
            )

        rect = (
            sdl3.SDL_Rect()
        )

        rect.x = int(
            left
        )

        rect.y = int(
            top
        )

        rect.w = int(
            right
            - left
        )

        rect.h = int(
            bottom
            - top
        )

        return rect

    # ==========================================================
    # CAMERA
    # ==========================================================

    def _update_camera_uniform(
        self,
    ):
        if self.camera is None:
            camera_x = 0.0
            camera_y = 0.0
            camera_zoom = 1.0

            shake_x = 0.0
            shake_y = 0.0

        else:
            camera_x = float(
                self.camera.x
            )

            camera_y = float(
                self.camera.y
            )

            camera_zoom = float(
                self.camera.zoom
            )

            shake_x = float(
                self.camera.shake_x
            )

            shake_y = float(
                self.camera.shake_y
            )

        viewport_width = float(
            self.context.swapchain_width
        )

        viewport_height = float(
            self.context.swapchain_height
        )

        struct.pack_into(
            "<8f",
            self._camera_data,
            0,

            camera_x,
            camera_y,

            viewport_width,
            viewport_height,

            camera_zoom,

            shake_x,
            shake_y,

            0.0,
        )

    # ==========================================================
    # RENDER INTO ACTIVE FRAME
    # ==========================================================

    def render_into(
        self,
        command_buffer,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        if self._texture is None:
            raise RuntimeError(
                "GPUSpriteBatch.begin(texture) "
                "must be called before rendering"
            )

        if (
            self._sprite_count
            == 0
        ):
            return 0

        instance_size = (
            self._sprite_count
            * self.INSTANCE_STRIDE
        )

        self.instance_buffer.upload_into(
            command_buffer,
            memoryview(
                self._instance_data
            )[
                :instance_size
            ],
        )

        self._update_camera_uniform()

        camera_buffer = (
            (
                ctypes.c_ubyte
                * self.CAMERA_UNIFORM_SIZE
            ).from_buffer(
                self._camera_data
            )
        )

        sdl3.SDL_PushGPUVertexUniformData(
            command_buffer,
            0,
            ctypes.cast(
                camera_buffer,
                ctypes.c_void_p,
            ),
            self.CAMERA_UNIFORM_SIZE,
        )

        return self._sprite_count

    # ==========================================================
    # DRAW INTO ACTIVE RENDER PASS
    # ==========================================================

    def draw_into(
        self,
        render_pass,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        if self._texture is None:
            raise RuntimeError(
                "GPUSpriteBatch.begin(texture) "
                "must be called before drawing"
            )

        if (
            self._sprite_count
            == 0
        ):
            return 0

        # ------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

        # ------------------------------------------------------
        # Vertex buffers
        # ------------------------------------------------------

        instance_size = (
            self._sprite_count
            * self.INSTANCE_STRIDE
        )

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding
            * 2
        )()

        vertex_bindings[
            0
        ] = (
            self.quad_buffer.binding(
                0,
                self.quad_buffer.size,
            )
        )

        vertex_bindings[
            1
        ] = (
            self.instance_buffer.binding(
                0,
                instance_size,
            )
        )

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            vertex_bindings,
            2,
        )

        # ------------------------------------------------------
        # Texture
        # ------------------------------------------------------

        texture_binding = (
            sdl3.SDL_GPUTextureSamplerBinding()
        )

        texture_binding.texture = (
            self._texture.texture
        )

        texture_binding.sampler = (
            self.sampler.sampler
        )

        sdl3.SDL_BindGPUFragmentSamplers(
            render_pass,
            0,
            ctypes.byref(
                texture_binding
            ),
            1,
        )

        # ------------------------------------------------------
        # Clip runs
        # ------------------------------------------------------

        drawn = 0

        run_start = 0

        while (
            run_start
            < self._sprite_count
        ):
            clip_rect = (
                self._clip_rects[
                    run_start
                ]
            )

            run_end = (
                run_start
                + 1
            )

            while (
                run_end
                < self._sprite_count
                and self._clip_rects[
                    run_end
                ]
                == clip_rect
            ):
                run_end += 1

            scissor = (
                self._make_scissor_rect(
                    clip_rect
                )
            )

            if (
                scissor.w > 0
                and scissor.h > 0
            ):
                sdl3.SDL_SetGPUScissor(
                    render_pass,
                    ctypes.byref(
                        scissor
                    ),
                )

                run_count = (
                    run_end
                    - run_start
                )

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    6,
                    run_count,
                    0,
                    run_start,
                )

                drawn += (
                    run_count
                )

            run_start = (
                run_end
            )

        # ------------------------------------------------------
        # Restore full viewport
        # ------------------------------------------------------

        full_scissor = (
            self._make_scissor_rect(
                None
            )
        )

        sdl3.SDL_SetGPUScissor(
            render_pass,
            ctypes.byref(
                full_scissor
            ),
        )

        return drawn

    # ==========================================================
    # END
    # ==========================================================

    def end(
        self,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        if self._texture is None:
            raise RuntimeError(
                "GPUSpriteBatch.begin(texture) "
                "must be called before end()"
            )

        if (
            self._sprite_count
            == 0
        ):
            self._texture = None
            return

        if not self.context.begin_frame():
            self._texture = None
            return

        try:
            command_buffer = (
                self.context.command_buffer
            )

            instance_size = (
                self._sprite_count
                * self.INSTANCE_STRIDE
            )

            self.instance_buffer.upload_into(
                command_buffer,
                memoryview(
                    self._instance_data
                )[
                    :instance_size
                ],
            )

            self._update_camera_uniform()

            render_pass = (
                self.context.begin_render_pass(
                    (
                        0.05,
                        0.05,
                        0.08,
                        1.0,
                    )
                )
            )

            try:
                camera_buffer = (
                    (
                        ctypes.c_ubyte
                        * self.CAMERA_UNIFORM_SIZE
                    ).from_buffer(
                        self._camera_data
                    )
                )

                sdl3.SDL_PushGPUVertexUniformData(
                    command_buffer,
                    0,
                    ctypes.cast(
                        camera_buffer,
                        ctypes.c_void_p,
                    ),
                    self.CAMERA_UNIFORM_SIZE,
                )

                # Reuse the same draw path so clipping works
                # in standalone batch usage too.
                self.draw_into(
                    render_pass
                )

            finally:
                self.context.end_render_pass(
                    render_pass
                )

            self.context.end_frame()

        except Exception:
            if self.context.frame_active:
                try:
                    self.context.end_frame()

                except Exception:
                    pass

            raise

        finally:
            self._texture = None

    # ==========================================================
    # FLUSH
    # ==========================================================

    def flush(
        self,
    ) -> None:
        """
        Render the currently prepared sprite instances into the
        already active GPU frame.

        This method does NOT begin or end a GPU frame.
        """

        if self._destroyed:
            raise RuntimeError(
                "GPUSpriteBatch has been destroyed"
            )

        if (
            self._sprite_count
            <= 0
        ):
            return

        if not self.context.frame_active:
            raise RuntimeError(
                "GPUSpriteBatch.flush() requires "
                "an active GPU frame."
            )

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
        # Worker threads
        # ------------------------------------------------------

        if self._executor:
            try:
                self._executor.shutdown(
                    wait=True
                )

            except Exception:
                pass

            self._executor = None

        # ------------------------------------------------------
        # GPU idle
        # ------------------------------------------------------

        try:
            self.context.wait_idle()

        except Exception:
            pass

        # ------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------

        if self.pipeline:
            try:
                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.device,
                    self.pipeline,
                )

            except Exception:
                pass

            self.pipeline = None

        # ------------------------------------------------------
        # Sampler
        # ------------------------------------------------------

        if self.sampler:
            try:
                self.sampler.destroy()

            except Exception:
                pass

            self.sampler = None

        # ------------------------------------------------------
        # Instance buffer
        # ------------------------------------------------------

        if self.instance_buffer:
            try:
                self.instance_buffer.destroy()

            except Exception:
                pass

            self.instance_buffer = None

        # ------------------------------------------------------
        # Quad buffer
        # ------------------------------------------------------

        if self.quad_buffer:
            try:
                self.quad_buffer.destroy()

            except Exception:
                pass

            self.quad_buffer = None

        # ------------------------------------------------------
        # Shaders
        # ------------------------------------------------------

        if self.vertex_shader:
            try:
                self.vertex_shader.destroy()

            except Exception:
                pass

            self.vertex_shader = None

        if self.fragment_shader:
            try:
                self.fragment_shader.destroy()

            except Exception:
                pass

            self.fragment_shader = None

        self._texture = None

        self._instance_data = (
            bytearray()
        )

        self._clip_rects.clear()

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