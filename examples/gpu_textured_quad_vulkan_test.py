from __future__ import annotations

import ctypes
import os
from pathlib import Path


# Vulkan erzwingen, bevor SDL_GPU initialisiert wird.
os.environ["SDL_GPU_DRIVER"] = "vulkan"

import sdl3

from nexora.rendering.gpu.context import GPUContext


ROOT = Path(__file__).resolve().parents[1]

VERTEX_SHADER_PATH = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "textured_quad.vert.spv"
)

FRAGMENT_SHADER_PATH = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "textured_quad.frag.spv"
)


def get_sdl_error() -> str:
    error = sdl3.SDL_GetError()

    if isinstance(error, bytes):
        return error.decode(
            "utf-8",
            errors="replace",
        )

    return str(error)


def check(value, message: str) -> None:

    if not value:
        raise RuntimeError(
            f"{message}: {get_sdl_error()}"
        )


class TexturedQuadVulkanTest:

    def __init__(self):

        self.context = None

        self.vertex_shader = None
        self.fragment_shader = None

        self.pipeline = None

        self.texture = None
        self.sampler = None
        self.vertex_buffer = None

        self.running = True

        # Keep shader memory alive while SDL owns the shaders.
        self._shader_buffers = []

        # Keep vertex data alive.
        self._vertex_data = None

    # =========================================================
    # INITIALIZE
    # =========================================================

    def initialize(self):

        print()
        print("=" * 60)
        print("NEXORA SDL_GPU VULKAN TEXTURED QUAD TEST")
        print("=" * 60)
        print()

        print("Backend: Vulkan")
        print()

        if not VERTEX_SHADER_PATH.exists():

            raise FileNotFoundError(
                f"Vertex shader not found:\n"
                f"{VERTEX_SHADER_PATH}"
            )

        if not FRAGMENT_SHADER_PATH.exists():

            raise FileNotFoundError(
                f"Fragment shader not found:\n"
                f"{FRAGMENT_SHADER_PATH}"
            )

        # =====================================================
        # 1. GPU CONTEXT
        # =====================================================

        print("[1/7] Creating Vulkan GPU context...")

        self.context = GPUContext(
            800,
            600,
            "Nexora Vulkan Textured Quad",
            debug=True,
            frames_in_flight=2,
        )

        print(
            "      Driver:",
            self.context.driver,
        )

        print(
            "      Swapchain format:",
            self.context.swapchain_format,
        )

        print()

        # =====================================================
        # 2. SHADERS
        # =====================================================

        print("[2/7] Loading SPIR-V shaders...")

        vertex_data = (
            VERTEX_SHADER_PATH.read_bytes()
        )

        fragment_data = (
            FRAGMENT_SHADER_PATH.read_bytes()
        )

        print(
            "      Vertex:",
            len(vertex_data),
            "bytes",
        )

        print(
            "      Fragment:",
            len(fragment_data),
            "bytes",
        )

        vertex_buffer = (
            ctypes.c_ubyte * len(vertex_data)
        ).from_buffer_copy(vertex_data)

        fragment_buffer = (
            ctypes.c_ubyte * len(fragment_data)
        ).from_buffer_copy(fragment_data)

        self._shader_buffers = [
            vertex_buffer,
            fragment_buffer,
        ]

        # -----------------------------------------------------
        # Vertex shader
        # -----------------------------------------------------

        vertex_info = (
            sdl3.SDL_GPUShaderCreateInfo()
        )

        vertex_info.code_size = len(vertex_data)

        vertex_info.code = ctypes.cast(
            vertex_buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )

        vertex_info.entrypoint = b"main"

        vertex_info.format = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
        )

        vertex_info.stage = (
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX
        )

        vertex_info.num_samplers = 0
        vertex_info.num_storage_textures = 0
        vertex_info.num_storage_buffers = 0
        vertex_info.num_uniform_buffers = 0
        vertex_info.props = 0

        self.vertex_shader = (
            sdl3.SDL_CreateGPUShader(
                self.context.device,
                ctypes.byref(vertex_info),
            )
        )

        check(
            self.vertex_shader,
            "Vertex shader creation failed",
        )

        print("      Vertex shader OK")

        # -----------------------------------------------------
        # Fragment shader
        # -----------------------------------------------------

        fragment_info = (
            sdl3.SDL_GPUShaderCreateInfo()
        )

        fragment_info.code_size = len(fragment_data)

        fragment_info.code = ctypes.cast(
            fragment_buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )

        fragment_info.entrypoint = b"main"

        fragment_info.format = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
        )

        fragment_info.stage = (
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT
        )

        # One sampler is declared in the fragment shader.
        fragment_info.num_samplers = 1
        fragment_info.num_storage_textures = 0
        fragment_info.num_storage_buffers = 0
        fragment_info.num_uniform_buffers = 0
        fragment_info.props = 0

        self.fragment_shader = (
            sdl3.SDL_CreateGPUShader(
                self.context.device,
                ctypes.byref(fragment_info),
            )
        )

        check(
            self.fragment_shader,
            "Fragment shader creation failed",
        )

        print("      Fragment shader OK")
        print()

        # =====================================================
        # 3. TEXTURE
        # =====================================================

        print("[3/7] Creating texture...")

        texture_info = (
            sdl3.SDL_GPUTextureCreateInfo()
        )

        texture_info.type = (
            sdl3.SDL_GPU_TEXTURETYPE_2D
        )

        texture_info.format = (
            sdl3.SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM
        )

        texture_info.usage = (
            sdl3.SDL_GPU_TEXTUREUSAGE_SAMPLER
        )

        texture_info.width = 2
        texture_info.height = 2

        texture_info.layer_count_or_depth = 1
        texture_info.num_levels = 1

        texture_info.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        texture_info.props = 0

        self.texture = (
            sdl3.SDL_CreateGPUTexture(
                self.context.device,
                ctypes.byref(texture_info),
            )
        )

        check(
            self.texture,
            "Texture creation failed",
        )

        print("      Texture OK")

        # -----------------------------------------------------
        # 2x2 texture
        #
        # RED       GREEN
        #
        # BLUE      WHITE
        # -----------------------------------------------------

        pixel_data = bytes(
            [
                # Row 0
                255, 0, 0, 255,
                0, 255, 0, 255,

                # Row 1
                0, 0, 255, 255,
                255, 255, 255, 255,
            ]
        )

        transfer_info = (
            sdl3.SDL_GPUTransferBufferCreateInfo()
        )

        transfer_info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )

        transfer_info.size = len(pixel_data)

        transfer_info.props = 0

        transfer_buffer = (
            sdl3.SDL_CreateGPUTransferBuffer(
                self.context.device,
                ctypes.byref(transfer_info),
            )
        )

        check(
            transfer_buffer,
            "Texture transfer buffer creation failed",
        )

        mapped = sdl3.SDL_MapGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
            False,
        )

        check(
            mapped,
            "Texture transfer buffer map failed",
        )

        ctypes.memmove(
            mapped,
            pixel_data,
            len(pixel_data),
        )

        sdl3.SDL_UnmapGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
        )

        command_buffer = (
            sdl3.SDL_AcquireGPUCommandBuffer(
                self.context.device
            )
        )

        check(
            command_buffer,
            "Texture upload command buffer failed",
        )

        copy_pass = (
            sdl3.SDL_BeginGPUCopyPass(
                command_buffer
            )
        )

        check(
            copy_pass,
            "Begin texture copy pass failed",
        )

        source = (
            sdl3.SDL_GPUTextureTransferInfo()
        )

        source.transfer_buffer = transfer_buffer
        source.offset = 0

        destination = (
            sdl3.SDL_GPUTextureRegion()
        )

        destination.texture = self.texture
        destination.mip_level = 0
        destination.layer = 0

        destination.x = 0
        destination.y = 0
        destination.z = 0

        destination.w = 2
        destination.h = 2
        destination.d = 1

        sdl3.SDL_UploadToGPUTexture(
            copy_pass,
            ctypes.byref(source),
            ctypes.byref(destination),
            False,
        )

        sdl3.SDL_EndGPUCopyPass(
            copy_pass
        )

        check(
            sdl3.SDL_SubmitGPUCommandBuffer(
                command_buffer
            ),
            "Texture upload submit failed",
        )

        sdl3.SDL_WaitForGPUIdle(
            self.context.device
        )

        sdl3.SDL_ReleaseGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
        )

        print("      Texture upload OK")
        print()

        # =====================================================
        # 4. SAMPLER
        # =====================================================

        print("[4/7] Creating sampler...")

        sampler_info = (
            sdl3.SDL_GPUSamplerCreateInfo()
        )

        sampler_info.min_filter = (
            sdl3.SDL_GPU_FILTER_NEAREST
        )

        sampler_info.mag_filter = (
            sdl3.SDL_GPU_FILTER_NEAREST
        )

        sampler_info.mipmap_mode = (
            sdl3.SDL_GPU_SAMPLERMIPMAPMODE_NEAREST
        )

        sampler_info.address_mode_u = (
            sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
        )

        sampler_info.address_mode_v = (
            sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
        )

        sampler_info.address_mode_w = (
            sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
        )

        sampler_info.mip_lod_bias = 0.0
        sampler_info.max_anisotropy = 1.0
        sampler_info.max_lod = 0.0

        sampler_info.enable_anisotropy = False
        sampler_info.enable_compare = False

        sampler_info.compare_op = (
            sdl3.SDL_GPU_COMPAREOP_ALWAYS
        )

        sampler_info.props = 0

        self.sampler = (
            sdl3.SDL_CreateGPUSampler(
                self.context.device,
                ctypes.byref(sampler_info),
            )
        )

        check(
            self.sampler,
            "Sampler creation failed",
        )

        print("      Sampler OK")
        print()

        # =====================================================
        # 5. PIPELINE
        # =====================================================

        print("[5/7] Creating textured pipeline...")

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = None
        vertex_input.num_vertex_buffers = 0

        vertex_input.vertex_attributes = None
        vertex_input.num_vertex_attributes = 0

        # -----------------------------------------------------
        # Rasterizer
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Multisampling
        # -----------------------------------------------------

        multisample = (
            sdl3.SDL_GPUMultisampleState()
        )

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        # -----------------------------------------------------
        # Depth
        # -----------------------------------------------------

        depth = (
            sdl3.SDL_GPUDepthStencilState()
        )

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # -----------------------------------------------------
        # Color target
        # -----------------------------------------------------

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

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

        # -----------------------------------------------------
        # Target info
        # -----------------------------------------------------

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1

        target_info.depth_stencil_format = (
            sdl3.SDL_GPU_TEXTUREFORMAT_INVALID
        )

        target_info.has_depth_stencil_target = False

        # -----------------------------------------------------
        # Pipeline info
        # -----------------------------------------------------

        pipeline_info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        pipeline_info.vertex_shader = (
            self.vertex_shader
        )

        pipeline_info.fragment_shader = (
            self.fragment_shader
        )

        pipeline_info.vertex_input_state = (
            vertex_input
        )

        pipeline_info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        pipeline_info.rasterizer_state = (
            rasterizer
        )

        pipeline_info.multisample_state = (
            multisample
        )

        pipeline_info.depth_stencil_state = (
            depth
        )

        pipeline_info.target_info = (
            target_info
        )

        pipeline_info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.context.device,
                ctypes.byref(pipeline_info),
            )
        )

        check(
            self.pipeline,
            "Textured graphics pipeline creation failed",
        )

        print("      Pipeline OK")
        print()

        # =====================================================
        # 6. VERTEX BUFFER
        # =====================================================

        print("[6/7] Creating vertex buffer...")

        # Six vertices.
        #
        # Each vertex:
        #
        # float2 position
        # float2 uv
        #
        # 16 bytes.
        #
        # 6 * 16 = 96 bytes.

        vertex_values = (
            ctypes.c_float * 24
        )(
            # Triangle 1
            -0.5, -0.5, 0.0, 0.0,
             0.5, -0.5, 1.0, 0.0,
             0.5,  0.5, 1.0, 1.0,

            # Triangle 2
            -0.5, -0.5, 0.0, 0.0,
             0.5,  0.5, 1.0, 1.0,
            -0.5,  0.5, 0.0, 1.0,
        )

        vertex_bytes = bytes(
            vertex_values
        )

        self._vertex_data = vertex_values

        buffer_info = (
            sdl3.SDL_GPUBufferCreateInfo()
        )

        buffer_info.usage = (
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX
        )

        buffer_info.size = len(vertex_bytes)

        buffer_info.props = 0

        self.vertex_buffer = (
            sdl3.SDL_CreateGPUBuffer(
                self.context.device,
                ctypes.byref(buffer_info),
            )
        )

        check(
            self.vertex_buffer,
            "Vertex buffer creation failed",
        )

        # -----------------------------------------------------
        # Upload vertex data
        # -----------------------------------------------------

        transfer_info = (
            sdl3.SDL_GPUTransferBufferCreateInfo()
        )

        transfer_info.usage = (
            sdl3.SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD
        )

        transfer_info.size = len(vertex_bytes)

        transfer_info.props = 0

        transfer_buffer = (
            sdl3.SDL_CreateGPUTransferBuffer(
                self.context.device,
                ctypes.byref(transfer_info),
            )
        )

        check(
            transfer_buffer,
            "Vertex transfer buffer creation failed",
        )

        mapped = sdl3.SDL_MapGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
            False,
        )

        check(
            mapped,
            "Vertex transfer buffer map failed",
        )

        ctypes.memmove(
            mapped,
            vertex_bytes,
            len(vertex_bytes),
        )

        sdl3.SDL_UnmapGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
        )

        command_buffer = (
            sdl3.SDL_AcquireGPUCommandBuffer(
                self.context.device
            )
        )

        check(
            command_buffer,
            "Vertex upload command buffer failed",
        )

        copy_pass = (
            sdl3.SDL_BeginGPUCopyPass(
                command_buffer
            )
        )

        check(
            copy_pass,
            "Begin vertex copy pass failed",
        )

        source = (
            sdl3.SDL_GPUTransferBufferLocation()
        )

        source.transfer_buffer = transfer_buffer
        source.offset = 0

        destination = (
            sdl3.SDL_GPUBufferRegion()
        )

        destination.buffer = self.vertex_buffer
        destination.offset = 0
        destination.size = len(vertex_bytes)

        sdl3.SDL_UploadToGPUBuffer(
            copy_pass,
            ctypes.byref(source),
            ctypes.byref(destination),
            False,
        )

        sdl3.SDL_EndGPUCopyPass(
            copy_pass
        )

        check(
            sdl3.SDL_SubmitGPUCommandBuffer(
                command_buffer
            ),
            "Vertex upload submit failed",
        )

        sdl3.SDL_WaitForGPUIdle(
            self.context.device
        )

        sdl3.SDL_ReleaseGPUTransferBuffer(
            self.context.device,
            transfer_buffer,
        )

        print("      Vertex buffer OK")
        print()

        # =====================================================
        # 7. READY
        # =====================================================

        print("[7/7] Rendering...")
        print()

        print("=" * 60)
        print("VULKAN TEXTURED QUAD READY")
        print("=" * 60)
        print()
        print("You should see a large quad")
        print("with four colored corners:")
        print()
        print("  RED       GREEN")
        print()
        print("  BLUE      WHITE")
        print()
        print("Close the window to exit.")
        print()

    # =========================================================
    # EVENTS
    # =========================================================

    def poll_events(self):

        event = sdl3.SDL_Event()

        while sdl3.SDL_PollEvent(
            ctypes.byref(event)
        ):

            if event.type == sdl3.SDL_EVENT_QUIT:

                self.running = False

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):

        if not self.context.begin_frame():
            return

        render_pass = None

        try:

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

            # -------------------------------------------------
            # Pipeline
            # -------------------------------------------------

            sdl3.SDL_BindGPUGraphicsPipeline(
                render_pass,
                self.pipeline,
            )

            # -------------------------------------------------
            # Vertex buffer
            # -------------------------------------------------

            vertex_binding = (
                sdl3.SDL_GPUBufferBinding()
            )

            vertex_binding.buffer = (
                self.vertex_buffer
            )

            vertex_binding.offset = 0

            sdl3.SDL_BindGPUVertexBuffers(
                render_pass,
                0,
                ctypes.byref(vertex_binding),
                1,
            )

            # -------------------------------------------------
            # Texture + sampler
            # -------------------------------------------------

            texture_binding = (
                sdl3.SDL_GPUTextureSamplerBinding()
            )

            texture_binding.texture = (
                self.texture
            )

            texture_binding.sampler = (
                self.sampler
            )

            # PySDL3 signature:
            #
            #   render_pass
            #   first_slot
            #   bindings
            #   num_bindings
            #
            sdl3.SDL_BindGPUFragmentSamplers(
                render_pass,
                0,
                ctypes.byref(texture_binding),
                1,
            )

            # -------------------------------------------------
            # Draw
            # -------------------------------------------------

            sdl3.SDL_DrawGPUPrimitives(
                render_pass,
                6,
                1,
                0,
                0,
            )

            # -------------------------------------------------
            # End pass
            # -------------------------------------------------

            self.context.end_render_pass(
                render_pass
            )

            render_pass = None

            # -------------------------------------------------
            # Submit
            # -------------------------------------------------

            self.context.end_frame()

        except Exception:

            # IMPORTANT:
            #
            # Once a swapchain texture has been acquired,
            # SDL_GPU does NOT allow cancelling the command
            # buffer.
            #
            # Therefore we must finish the render pass and
            # submit the command buffer instead of blindly
            # calling cancel_frame().

            if render_pass is not None:

                try:

                    self.context.end_render_pass(
                        render_pass
                    )

                except Exception:
                    pass

                render_pass = None

            try:

                self.context.end_frame()

            except Exception:

                # At this point there is nothing useful left
                # to recover from in this standalone test.
                pass

            raise

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        self.initialize()

        try:

            while self.running:

                self.poll_events()

                self.render()

        finally:

            self.destroy()

    # =========================================================
    # DESTROY
    # =========================================================

    def destroy(self):

        print()
        print("Shutting down...")

        if self.context is not None:

            try:
                self.context.wait_idle()
            except Exception:
                pass

        # -----------------------------------------------------
        # Vertex buffer
        # -----------------------------------------------------

        if self.vertex_buffer is not None:

            try:

                sdl3.SDL_ReleaseGPUBuffer(
                    self.context.device,
                    self.vertex_buffer,
                )

            except Exception:
                pass

            self.vertex_buffer = None

        # -----------------------------------------------------
        # Texture
        # -----------------------------------------------------

        if self.texture is not None:

            try:

                sdl3.SDL_ReleaseGPUTexture(
                    self.context.device,
                    self.texture,
                )

            except Exception:
                pass

            self.texture = None

        # -----------------------------------------------------
        # Sampler
        # -----------------------------------------------------

        if self.sampler is not None:

            try:

                sdl3.SDL_ReleaseGPUSampler(
                    self.context.device,
                    self.sampler,
                )

            except Exception:
                pass

            self.sampler = None

        # -----------------------------------------------------
        # Pipeline
        # -----------------------------------------------------

        if self.pipeline is not None:

            try:

                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.context.device,
                    self.pipeline,
                )

            except Exception:
                pass

            self.pipeline = None

        # -----------------------------------------------------
        # Vertex shader
        # -----------------------------------------------------

        if self.vertex_shader is not None:

            try:

                sdl3.SDL_ReleaseGPUShader(
                    self.context.device,
                    self.vertex_shader,
                )

            except Exception:
                pass

            self.vertex_shader = None

        # -----------------------------------------------------
        # Fragment shader
        # -----------------------------------------------------

        if self.fragment_shader is not None:

            try:

                sdl3.SDL_ReleaseGPUShader(
                    self.context.device,
                    self.fragment_shader,
                )

            except Exception:
                pass

            self.fragment_shader = None

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        if self.context is not None:

            try:
                self.context.destroy()
            except Exception:
                pass

            self.context = None

        print("Done.")


def main():

    test = TexturedQuadVulkanTest()

    test.run()


if __name__ == "__main__":
    main()