from __future__ import annotations

import ctypes
import struct
from pathlib import Path

import sdl3


WIDTH = 1280
HEIGHT = 720

ROOT = Path(__file__).resolve().parents[1]
SHADER_DIR = ROOT / "nexora" / "rendering" / "shaders" / "bin"


def check(condition, message):
    if not condition:
        error = sdl3.SDL_GetError()
        raise RuntimeError(f"{message}: {error}")


class GPUTriangle:
    def __init__(self):
        self.window = None
        self.device = None

        self.vertex_shader = None
        self.fragment_shader = None
        self.pipeline = None

        self.vertex_buffer = None
        self.transfer_buffer = None

    def initialize(self):
        check(
            sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO),
            "SDL_Init failed",
        )

        self.window = sdl3.SDL_CreateWindow(
            b"Nexora GPU Triangle",
            WIDTH,
            HEIGHT,
            0,
        )
        check(self.window, "SDL_CreateWindow failed")

        print("SDL window created")

        formats = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            | sdl3.SDL_GPU_SHADERFORMAT_DXIL
            | sdl3.SDL_GPU_SHADERFORMAT_MSL
        )

        self.device = sdl3.SDL_CreateGPUDevice(
            formats,
            True,
            None,
        )
        check(self.device, "SDL_CreateGPUDevice failed")

        print(
            "GPU driver:",
            sdl3.SDL_GetGPUDeviceDriver(self.device).decode()
            if sdl3.SDL_GetGPUDeviceDriver(self.device)
            else "<unknown>",
        )

        check(
            sdl3.SDL_ClaimWindowForGPUDevice(
                self.device,
                self.window,
            ),
            "SDL_ClaimWindowForGPUDevice failed",
        )

        print("GPU window claimed")

        sdl3.SDL_SetGPUAllowedFramesInFlight(
            self.device,
            2,
        )

        self._create_shaders()
        self._create_vertex_buffer()
        self._create_pipeline()

        print("GPU triangle resources created")

    def _load_binary(self, path: Path):
        data = path.read_bytes()

        if not data:
            raise RuntimeError(f"Empty shader: {path}")

        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)

        return data, buffer

    def _create_shader(self, path, stage):
        data, buffer = self._load_binary(path)

        info = sdl3.SDL_GPUShaderCreateInfo()

        info.code_size = len(data)
        info.code = ctypes.cast(
            buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )
        info.entrypoint = b"main"
        info.format = sdl3.SDL_GPU_SHADERFORMAT_DXIL
        info.stage = stage

        info.num_samplers = 0
        info.num_storage_textures = 0
        info.num_storage_buffers = 0
        info.num_uniform_buffers = 0
        info.props = 0

        shader = sdl3.SDL_CreateGPUShader(
            self.device,
            ctypes.byref(info),
        )

        check(shader, f"SDL_CreateGPUShader failed: {path}")

        return shader

    def _create_shaders(self):
        self.vertex_shader = self._create_shader(
            SHADER_DIR / "triangle.vert.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
        )

        self.fragment_shader = self._create_shader(
            SHADER_DIR / "triangle.frag.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
        )

    def _create_vertex_buffer(self):
        #
        # Vertex:
        #   float2 position = 8 bytes
        #   float4 color    = 16 bytes
        #
        # Total = 24 bytes
        #

        vertices = struct.pack(
            "<ff ffff",
            -0.7,
            -0.6,
            1.0,
            0.1,
            0.1,
            1.0,

        ) + struct.pack(
            "<ff ffff",
            0.7,
            -0.6,
            0.1,
            1.0,
            0.1,
            1.0,

        ) + struct.pack(
            "<ff ffff",
            0.0,
            0.7,
            0.1,
            0.5,
            1.0,
            1.0,
        )

        vertex_size = len(vertices)

        buffer_info = sdl3.SDL_GPUBufferCreateInfo()

        buffer_info.usage = sdl3.SDL_GPU_BUFFERUSAGE_VERTEX
        buffer_info.size = vertex_size
        buffer_info.props = 0

        self.vertex_buffer = sdl3.SDL_CreateGPUBuffer(
            self.device,
            ctypes.byref(buffer_info),
        )

        check(
            self.vertex_buffer,
            "SDL_CreateGPUBuffer failed",
        )

        transfer_info = sdl3.SDL_GPUTransferBufferCreateInfo()

        transfer_info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )
        transfer_info.size = vertex_size
        transfer_info.props = 0

        self.transfer_buffer = (
            sdl3.SDL_CreateGPUTransferBuffer(
                self.device,
                ctypes.byref(transfer_info),
            )
        )

        check(
            self.transfer_buffer,
            "SDL_CreateGPUTransferBuffer failed",
        )

        mapped = sdl3.SDL_MapGPUTransferBuffer(
            self.device,
            self.transfer_buffer,
            False,
        )

        check(
            mapped,
            "SDL_MapGPUTransferBuffer failed",
        )

        ctypes.memmove(
            mapped,
            vertices,
            vertex_size,
        )

        sdl3.SDL_UnmapGPUTransferBuffer(
            self.device,
            self.transfer_buffer,
        )

        command_buffer = sdl3.SDL_AcquireGPUCommandBuffer(
            self.device,
        )

        check(
            command_buffer,
            "SDL_AcquireGPUCommandBuffer failed",
        )

        copy_pass = sdl3.SDL_BeginGPUCopyPass(
            command_buffer,
        )

        check(
            copy_pass,
            "SDL_BeginGPUCopyPass failed",
        )

        source = sdl3.SDL_GPUTransferBufferLocation()

        source.transfer_buffer = self.transfer_buffer
        source.offset = 0

        destination = sdl3.SDL_GPUBufferRegion()

        destination.buffer = self.vertex_buffer
        destination.offset = 0
        destination.size = vertex_size

        sdl3.SDL_UploadToGPUBuffer(
            copy_pass,
            source,
            destination,
            False,
        )

        sdl3.SDL_EndGPUCopyPass(copy_pass)

        check(
            sdl3.SDL_SubmitGPUCommandBuffer(
                command_buffer,
            ),
            "Vertex upload submit failed",
        )

        # The buffer is immediately needed for the next frame.
        # Wait once during initialization.
        sdl3.SDL_WaitForGPUIdle(self.device)

    def _create_pipeline(self):
        vertex_description = (
            sdl3.SDL_GPUVertexBufferDescription()
        )

        vertex_description.slot = 0
        vertex_description.pitch = 24
        vertex_description.input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )
        vertex_description.instance_step_rate = 0

        vertex_attributes = (
            sdl3.SDL_GPUVertexAttribute * 2
        )()

        # POSITION0 -> float2
        vertex_attributes[0].location = 0
        vertex_attributes[0].buffer_slot = 0
        vertex_attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        vertex_attributes[0].offset = 0

        # COLOR0 -> float4
        vertex_attributes[1].location = 1
        vertex_attributes[1].buffer_slot = 0
        vertex_attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        vertex_attributes[1].offset = 8

        vertex_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 1
        )()

        vertex_descriptions[0] = vertex_description

        vertex_input = sdl3.SDL_GPUVertexInputState()

        vertex_input.vertex_buffer_descriptions = (
            vertex_descriptions
        )
        vertex_input.num_vertex_buffers = 1

        vertex_input.vertex_attributes = vertex_attributes
        vertex_input.num_vertex_attributes = 2

        rasterizer = sdl3.SDL_GPURasterizerState()

        rasterizer.fill_mode = sdl3.SDL_GPU_FILLMODE_FILL
        rasterizer.cull_mode = sdl3.SDL_GPU_CULLMODE_NONE
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

        target_format = (
            sdl3.SDL_GetGPUSwapchainTextureFormat(
                self.device,
                self.window,
            )
        )

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = target_format

        color_target.blend_state.enable_blend = False
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

        pipeline_info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        pipeline_info.vertex_shader = self.vertex_shader
        pipeline_info.fragment_shader = self.fragment_shader

        pipeline_info.vertex_input_state = vertex_input

        pipeline_info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        pipeline_info.rasterizer_state = rasterizer
        pipeline_info.multisample_state = multisample
        pipeline_info.depth_stencil_state = depth
        pipeline_info.target_info = target_info
        pipeline_info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(pipeline_info),
            )
        )

        check(
            self.pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )

    def render(self):
        command_buffer = sdl3.SDL_AcquireGPUCommandBuffer(
            self.device,
        )

        if not command_buffer:
            return

        texture = sdl3.LP_SDL_GPUTexture()
        width = ctypes.c_uint32()
        height = ctypes.c_uint32()

        acquired = (
            sdl3.SDL_WaitAndAcquireGPUSwapchainTexture(
                command_buffer,
                self.window,
                ctypes.byref(texture),
                ctypes.byref(width),
                ctypes.byref(height),
            )
        )

        if not acquired:
            sdl3.SDL_CancelGPUCommandBuffer(
                command_buffer,
            )
            return

        # Minimized window.
        if not texture:
            sdl3.SDL_SubmitGPUCommandBuffer(
                command_buffer,
            )
            return

        target = sdl3.SDL_GPUColorTargetInfo()

        target.texture = texture
        target.mip_level = 0
        target.layer_or_depth_plane = 0

        target.clear_color = sdl3.SDL_FColor(
            0.03,
            0.03,
            0.05,
            1.0,
        )

        target.load_op = sdl3.SDL_GPU_LOADOP_CLEAR
        target.store_op = sdl3.SDL_GPU_STOREOP_STORE

        target.resolve_texture = None
        target.resolve_mip_level = 0
        target.resolve_layer = 0
        target.cycle = False
        target.cycle_resolve_texture = False

        render_pass = sdl3.SDL_BeginGPURenderPass(
            command_buffer,
            ctypes.byref(target),
            1,
            None,
        )

        check(
            render_pass,
            "SDL_BeginGPURenderPass failed",
        )

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

        binding = sdl3.SDL_GPUBufferBinding()

        binding.buffer = self.vertex_buffer
        binding.offset = 0

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            ctypes.byref(binding),
            1,
        )

        sdl3.SDL_DrawGPUPrimitives(
            render_pass,
            3,
            1,
            0,
            0,
        )

        sdl3.SDL_EndGPURenderPass(render_pass)

        check(
            sdl3.SDL_SubmitGPUCommandBuffer(
                command_buffer,
            ),
            "SDL_SubmitGPUCommandBuffer failed",
        )

    def run(self):
        running = True
        event = sdl3.SDL_Event()

        while running:
            while sdl3.SDL_PollEvent(ctypes.byref(event)):
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

            self.render()

    def shutdown(self):
        if self.device:
            sdl3.SDL_WaitForGPUIdle(self.device)

        if self.pipeline:
            sdl3.SDL_ReleaseGPUGraphicsPipeline(
                self.device,
                self.pipeline,
            )

        if self.vertex_shader:
            sdl3.SDL_ReleaseGPUShader(
                self.device,
                self.vertex_shader,
            )

        if self.fragment_shader:
            sdl3.SDL_ReleaseGPUShader(
                self.device,
                self.fragment_shader,
            )

        if self.transfer_buffer:
            sdl3.SDL_ReleaseGPUTransferBuffer(
                self.device,
                self.transfer_buffer,
            )

        if self.vertex_buffer:
            sdl3.SDL_ReleaseGPUBuffer(
                self.device,
                self.vertex_buffer,
            )

        if self.device and self.window:
            sdl3.SDL_ReleaseWindowFromGPUDevice(
                self.device,
                self.window,
            )

        if self.device:
            sdl3.SDL_DestroyGPUDevice(self.device)

        if self.window:
            sdl3.SDL_DestroyWindow(self.window)

        sdl3.SDL_Quit()


def main():
    app = GPUTriangle()

    try:
        app.initialize()
        print("GPU triangle initialized")
        print("Close the window to exit.")
        app.run()

    finally:
        app.shutdown()


if __name__ == "__main__":
    main()