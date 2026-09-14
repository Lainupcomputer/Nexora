from __future__ import annotations

import ctypes
import math
import struct
from pathlib import Path

import sdl3

from nexora.rendering.gpu.buffer import GPUBuffer
from nexora.rendering.gpu.shader import GPUShader


class GPUShapeBatch:
    """
    GPU shape renderer.

    Current shapes:
        - rect
        - circle
        - ellipse
        - triangle
        - polygon

    Rectangles, circles and ellipses use an instanced quad.

    Triangles and polygons use a dynamic geometry buffer.

    GPU / SDL operations must happen on the rendering thread.
    """

    MAX_SHAPES = 50000
    MAX_POLYGON_POINTS = 256

    # Geometry is a separate capacity from quad-based shapes.
    #
    # The previous implementation allocated:
    #
    #   max_shapes * MAX_POLYGON_POINTS * 3
    #
    # vertices up front. With 10,000 shapes that produced a
    # ~175.8 MB geometry buffer, and because GPUBuffer uses three
    # frames in flight, three equally large transfer buffers were
    # allocated as well (~527 MB of process RAM).
    #
    # 65,536 vertices = 1.5 MiB of geometry data and is enough for
    # more than 21,000 standalone triangles per frame.
    DEFAULT_MAX_GEOMETRY_VERTICES = 65_536
    MAX_GEOMETRY_VERTICES = 1_000_000

    INSTANCE_FLOATS = 11
    INSTANCE_STRIDE = 44

    CAMERA_UNIFORM_SIZE = 32

    GEOMETRY_FLOATS_PER_VERTEX = 6
    GEOMETRY_STRIDE = 24

    def __init__(
        self,
        context,
        *,
        max_shapes=10000,
        vertex_shader_path,
        fragment_shader_path,
        geometry_vertex_shader_path=None,
        geometry_fragment_shader_path=None,
        camera=None,
        max_geometry_vertices: int = DEFAULT_MAX_GEOMETRY_VERTICES,
    ):
        self.context = context
        self.device = context.device
        self.camera = camera

        self.max_shapes = int(max_shapes)

        if self.max_shapes <= 0:
            raise ValueError(
                "max_shapes must be greater than zero"
            )

        if self.max_shapes > self.MAX_SHAPES:
            raise ValueError(
                f"max_shapes cannot exceed "
                f"{self.MAX_SHAPES}"
            )

        self.max_geometry_vertices = int(
            max_geometry_vertices
        )

        if self.max_geometry_vertices <= 0:
            raise ValueError(
                "max_geometry_vertices must be greater than zero"
            )

        if (
            self.max_geometry_vertices
            > self.MAX_GEOMETRY_VERTICES
        ):
            raise ValueError(
                "max_geometry_vertices cannot exceed "
                f"{self.MAX_GEOMETRY_VERTICES}"
            )

        self.vertex_shader_path = Path(
            vertex_shader_path
        )

        self.fragment_shader_path = Path(
            fragment_shader_path
        )

        if geometry_vertex_shader_path is None:
            geometry_vertex_shader_path = (
                self.vertex_shader_path.parent
                / "geometry.vert.spv"
            )

        if geometry_fragment_shader_path is None:
            geometry_fragment_shader_path = (
                self.fragment_shader_path.parent
                / "geometry.frag.spv"
            )

        self.geometry_vertex_shader_path = Path(
            geometry_vertex_shader_path
        )

        self.geometry_fragment_shader_path = Path(
            geometry_fragment_shader_path
        )

        self.vertex_shader = None
        self.fragment_shader = None

        self.geometry_vertex_shader = None
        self.geometry_fragment_shader = None

        self.quad_buffer = None
        self.instance_buffer = None
        self.geometry_buffer = None

        self.pipeline = None
        self.geometry_pipeline = None

        self._instance_data = bytearray(
            self.max_shapes
            * self.INSTANCE_STRIDE
        )

        self._shape_count = 0

        self._geometry_data = bytearray()
        self._geometry_vertex_count = 0

        self._camera_data = bytearray(
            self.CAMERA_UNIFORM_SIZE
        )

        self._destroyed = False

        self._create_resources()

    # ----------------------------------------------------------
    # Utility
    # ----------------------------------------------------------

    @staticmethod
    def _decode_error(error):
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

    # ----------------------------------------------------------
    # Resource creation
    # ----------------------------------------------------------

    def _create_resources(self):
        self._create_shaders()
        self._create_quad()
        self._create_instance_buffer()
        self._create_geometry_buffer()
        self._create_pipeline()
        self._create_geometry_pipeline()

    def _create_shaders(self):
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
        )

        self.geometry_vertex_shader = GPUShader(
            self.device,
            self.geometry_vertex_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
            num_uniform_buffers=1,
        )

        self.geometry_fragment_shader = GPUShader(
            self.device,
            self.geometry_fragment_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
        )

    def _create_quad(self):
        vertices = struct.pack(
            "<12f",

            # Triangle 1
            -0.5, -0.5,
             0.5, -0.5,
             0.5,  0.5,

            # Triangle 2
            -0.5, -0.5,
             0.5,  0.5,
            -0.5,  0.5,
        )

        self.quad_buffer = GPUBuffer(
            self.device,
            len(vertices),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
        )

    def _create_instance_buffer(self):
        self.instance_buffer = GPUBuffer(
            self.device,
            len(self._instance_data),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=3,
        )

    def _create_geometry_buffer(self):
        size = (
            self.max_geometry_vertices
            * self.GEOMETRY_STRIDE
        )

        self.geometry_buffer = GPUBuffer(
            self.device,
            size,
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=3,
        )

    def _create_pipeline(self):
        vertex_buffer_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 2
        )()

        vertex_buffer_descriptions[0].slot = 0
        vertex_buffer_descriptions[0].pitch = 8
        vertex_buffer_descriptions[0].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )
        vertex_buffer_descriptions[0].instance_step_rate = 0

        vertex_buffer_descriptions[1].slot = 1
        vertex_buffer_descriptions[1].pitch = (
            self.INSTANCE_STRIDE
        )
        vertex_buffer_descriptions[1].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_INSTANCE
        )
        vertex_buffer_descriptions[1].instance_step_rate = 0

        attributes = (
            sdl3.SDL_GPUVertexAttribute * 5
        )()

        # Quad position
        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        # Instance position
        attributes[1].location = 1
        attributes[1].buffer_slot = 1
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[1].offset = 0

        # Instance size
        attributes[2].location = 2
        attributes[2].buffer_slot = 1
        attributes[2].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[2].offset = 8

        # Instance rotation
        attributes[3].location = 3
        attributes[3].buffer_slot = 1
        attributes[3].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[3].offset = 16

        # Instance origin
        attributes[4].location = 4
        attributes[4].buffer_slot = 1
        attributes[4].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[4].offset = 20

        # Color needs location 5.
        #
        # SDL GPU vertex attributes are independent of
        # the shader declaration order, so add it below
        # by using a 6-element attribute array.
        #
        # Recreate the array with the correct count.
        attributes = (
            sdl3.SDL_GPUVertexAttribute * 6
        )()

        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        attributes[1].location = 1
        attributes[1].buffer_slot = 1
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[1].offset = 0

        attributes[2].location = 2
        attributes[2].buffer_slot = 1
        attributes[2].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[2].offset = 8

        attributes[3].location = 3
        attributes[3].buffer_slot = 1
        attributes[3].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[3].offset = 16

        attributes[4].location = 4
        attributes[4].buffer_slot = 1
        attributes[4].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[4].offset = 20

        attributes[5].location = 5
        attributes[5].buffer_slot = 1
        attributes[5].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        attributes[5].offset = 28

        rasterizer = sdl3.SDL_GPURasterizerState()

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

        multisample = sdl3.SDL_GPUMultisampleState()

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        depth = sdl3.SDL_GPUDepthStencilState()

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        color_target.blend_state.enable_blend = True

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

        color_target.blend_state.enable_color_write_mask = True

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        color_targets[0] = color_target

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1
        target_info.depth_stencil_format = 0
        target_info.has_depth_stencil_target = False

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = (
            vertex_buffer_descriptions
        )

        vertex_input.num_vertex_buffers = 2

        vertex_input.vertex_attributes = attributes
        vertex_input.num_vertex_attributes = 6

        info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        info.vertex_shader = (
            self.vertex_shader.shader
        )

        info.fragment_shader = (
            self.fragment_shader.shader
        )

        info.vertex_input_state = vertex_input

        info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        info.rasterizer_state = rasterizer
        info.multisample_state = multisample
        info.depth_stencil_state = depth
        info.target_info = target_info
        info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(info),
            )
        )

        self._check(
            self.pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )

    def _create_geometry_pipeline(self):
        vertex_buffer_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 1
        )()

        vertex_buffer_descriptions[0].slot = 0
        vertex_buffer_descriptions[0].pitch = (
            self.GEOMETRY_STRIDE
        )
        vertex_buffer_descriptions[0].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )
        vertex_buffer_descriptions[0].instance_step_rate = 0

        attributes = (
            sdl3.SDL_GPUVertexAttribute * 2
        )()

        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        attributes[1].location = 1
        attributes[1].buffer_slot = 0
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        attributes[1].offset = 8

        rasterizer = sdl3.SDL_GPURasterizerState()

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

        multisample = sdl3.SDL_GPUMultisampleState()

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        depth = sdl3.SDL_GPUDepthStencilState()

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        color_target.blend_state.enable_blend = True

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

        color_target.blend_state.enable_color_write_mask = True

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        color_targets[0] = color_target

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1
        target_info.depth_stencil_format = 0
        target_info.has_depth_stencil_target = False

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = (
            vertex_buffer_descriptions
        )

        vertex_input.num_vertex_buffers = 1

        vertex_input.vertex_attributes = attributes
        vertex_input.num_vertex_attributes = 2

        info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        info.vertex_shader = (
            self.geometry_vertex_shader.shader
        )

        info.fragment_shader = (
            self.geometry_fragment_shader.shader
        )

        info.vertex_input_state = vertex_input

        info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        info.rasterizer_state = rasterizer
        info.multisample_state = multisample
        info.depth_stencil_state = depth
        info.target_info = target_info
        info.props = 0

        self.geometry_pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(info),
            )
        )

        self._check(
            self.geometry_pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )

    # ----------------------------------------------------------
    # Batch
    # ----------------------------------------------------------

    def begin(self):
        if self._destroyed:
            raise RuntimeError(
                "GPUShapeBatch has been destroyed"
            )

        self._shape_count = 0
        self._geometry_data.clear()
        self._geometry_vertex_count = 0

    # ----------------------------------------------------------
    # Quad based shapes
    # ----------------------------------------------------------

    def rect(
        self,
        x,
        y,
        width,
        height,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation=0.0,
        origin=(0.5, 0.5),
    ):
        self._add_shape(
            x,
            y,
            width,
            height,
            color,
            rotation,
            origin,
        )

    def circle(
        self,
        x,
        y,
        diameter,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation=0.0,
        origin=(0.5, 0.5),
    ):
        diameter = float(diameter)

        self._add_shape(
            x,
            y,
            diameter,
            diameter,
            color,
            rotation,
            origin,
        )

    def ellipse(
        self,
        x,
        y,
        width,
        height,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation=0.0,
        origin=(0.5, 0.5),
    ):
        self._add_shape(
            x,
            y,
            width,
            height,
            color,
            rotation,
            origin,
        )

    def _add_shape(
        self,
        x,
        y,
        width,
        height,
        color,
        rotation,
        origin,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUShapeBatch has been destroyed"
            )

        if self._shape_count >= self.max_shapes:
            raise RuntimeError(
                "GPUShapeBatch capacity exceeded "
                f"({self.max_shapes} shapes)"
            )

        origin_x, origin_y = origin

        if not 0.0 <= float(origin_x) <= 1.0:
            raise ValueError(
                "origin x must be between 0.0 and 1.0"
            )

        if not 0.0 <= float(origin_y) <= 1.0:
            raise ValueError(
                "origin y must be between 0.0 and 1.0"
            )

        offset = (
            self._shape_count
            * self.INSTANCE_STRIDE
        )

        r, g, b, a = color

        struct.pack_into(
            "<11f",
            self._instance_data,
            offset,

            float(x),
            float(y),

            float(width),
            float(height),

            math.radians(float(rotation)),

            float(origin_x),
            float(origin_y),

            float(r),
            float(g),
            float(b),
            float(a),
        )

        self._shape_count += 1

    # ----------------------------------------------------------
    # Triangle
    # ----------------------------------------------------------

    def triangle(
        self,
        x1,
        y1,
        x2,
        y2,
        x3,
        y3,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        self._add_geometry_triangle(
            x1,
            y1,
            x2,
            y2,
            x3,
            y3,
            color,
        )

    # ----------------------------------------------------------
    # Polygon
    # ----------------------------------------------------------

    def polygon(
        self,
        points,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPUShapeBatch has been destroyed"
            )

        points = list(points)

        if len(points) < 3:
            raise ValueError(
                "polygon requires at least 3 points"
            )

        if len(points) > self.MAX_POLYGON_POINTS:
            raise ValueError(
                "polygon exceeds maximum point count "
                f"({self.MAX_POLYGON_POINTS})"
            )

        normalized_points = []

        for point in points:
            if len(point) != 2:
                raise ValueError(
                    "polygon points must contain "
                    "(x, y)"
                )

            normalized_points.append(
                (
                    float(point[0]),
                    float(point[1]),
                )
            )

        x0, y0 = normalized_points[0]

        for index in range(
            1,
            len(normalized_points) - 1,
        ):
            x1, y1 = normalized_points[index]
            x2, y2 = normalized_points[index + 1]

            self._add_geometry_vertex(
                x0,
                y0,
                color,
            )

            self._add_geometry_vertex(
                x1,
                y1,
                color,
            )

            self._add_geometry_vertex(
                x2,
                y2,
                color,
            )

    def _add_geometry_triangle(
        self,
        x1,
        y1,
        x2,
        y2,
        x3,
        y3,
        color,
    ):
        self._add_geometry_vertex(
            x1,
            y1,
            color,
        )

        self._add_geometry_vertex(
            x2,
            y2,
            color,
        )

        self._add_geometry_vertex(
            x3,
            y3,
            color,
        )

    def _add_geometry_vertex(
        self,
        x,
        y,
        color,
    ):
        if (
            self._geometry_vertex_count
            >= self.max_geometry_vertices
        ):
            raise RuntimeError(
                "GPUShapeBatch geometry capacity exceeded "
                f"({self.max_geometry_vertices} vertices). "
                "Increase max_geometry_vertices when creating "
                "the renderer/shape batch."
            )

        r, g, b, a = color

        self._geometry_data.extend(
            struct.pack(
                "<6f",
                float(x),
                float(y),
                float(r),
                float(g),
                float(b),
                float(a),
            )
        )

        self._geometry_vertex_count += 1

    # ----------------------------------------------------------
    # Camera
    # ----------------------------------------------------------

    def _update_camera_uniform(self):
        if self.camera is None:
            camera_x = 0.0
            camera_y = 0.0
            camera_zoom = 1.0
            shake_x = 0.0
            shake_y = 0.0

        else:
            camera_x = float(self.camera.x)
            camera_y = float(self.camera.y)
            camera_zoom = float(self.camera.zoom)
            shake_x = float(self.camera.shake_x)
            shake_y = float(self.camera.shake_y)

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

    # ----------------------------------------------------------
    # GPU upload
    # ----------------------------------------------------------

    def render_into(self, command_buffer):
        if self._destroyed:
            raise RuntimeError(
                "GPUShapeBatch has been destroyed"
            )

        rendered = 0

        if self._shape_count > 0:
            instance_size = (
                self._shape_count
                * self.INSTANCE_STRIDE
            )

            self.instance_buffer.upload_into(
                command_buffer,
                memoryview(
                    self._instance_data
                )[:instance_size],
            )

            rendered += self._shape_count

        if self._geometry_vertex_count > 0:
            self.geometry_buffer.upload_into(
                command_buffer,
                self._geometry_data,
            )

            rendered += self._geometry_vertex_count

        if rendered == 0:
            return 0

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

        return rendered

    # ----------------------------------------------------------
    # Draw
    # ----------------------------------------------------------

    def draw_into(self, render_pass):
        if self._destroyed:
            raise RuntimeError(
                "GPUShapeBatch has been destroyed"
            )

        rendered = 0

        if self._shape_count > 0:
            sdl3.SDL_BindGPUGraphicsPipeline(
                render_pass,
                self.pipeline,
            )

            instance_size = (
                self._shape_count
                * self.INSTANCE_STRIDE
            )

            vertex_bindings = (
                sdl3.SDL_GPUBufferBinding * 2
            )()

            vertex_bindings[0] = (
                self.quad_buffer.binding(
                    0,
                    self.quad_buffer.size,
                )
            )

            vertex_bindings[1] = (
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

            sdl3.SDL_DrawGPUPrimitives(
                render_pass,
                6,
                self._shape_count,
                0,
                0,
            )

            rendered += self._shape_count

        if self._geometry_vertex_count > 0:
            sdl3.SDL_BindGPUGraphicsPipeline(
                render_pass,
                self.geometry_pipeline,
            )

            vertex_bindings = (
                sdl3.SDL_GPUBufferBinding * 1
            )()

            vertex_bindings[0] = (
                self.geometry_buffer.binding(
                    0,
                    len(self._geometry_data),
                )
            )

            sdl3.SDL_BindGPUVertexBuffers(
                render_pass,
                0,
                vertex_bindings,
                1,
            )

            sdl3.SDL_DrawGPUPrimitives(
                render_pass,
                self._geometry_vertex_count,
                1,
                0,
                0,
            )

            rendered += self._geometry_vertex_count

        return rendered

    # ----------------------------------------------------------
    # Clear
    # ----------------------------------------------------------

    def clear(self):
        self._shape_count = 0
        self._geometry_data.clear()
        self._geometry_vertex_count = 0

    # ----------------------------------------------------------
    # Destroy
    # ----------------------------------------------------------

    def destroy(self):
        if self._destroyed:
            return

        self._destroyed = True

        if self.geometry_pipeline:
            try:
                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.device,
                    self.geometry_pipeline,
                )
            except Exception:
                pass

            self.geometry_pipeline = None

        if self.pipeline:
            try:
                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.device,
                    self.pipeline,
                )
            except Exception:
                pass

            self.pipeline = None

        if self.geometry_buffer:
            try:
                self.geometry_buffer.destroy()
            except Exception:
                pass

            self.geometry_buffer = None

        if self.instance_buffer:
            try:
                self.instance_buffer.destroy()
            except Exception:
                pass

            self.instance_buffer = None

        if self.quad_buffer:
            try:
                self.quad_buffer.destroy()
            except Exception:
                pass

            self.quad_buffer = None

        if self.geometry_vertex_shader:
            try:
                self.geometry_vertex_shader.destroy()
            except Exception:
                pass

            self.geometry_vertex_shader = None

        if self.geometry_fragment_shader:
            try:
                self.geometry_fragment_shader.destroy()
            except Exception:
                pass

            self.geometry_fragment_shader = None

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

        self._instance_data = bytearray()
        self._geometry_data.clear()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()