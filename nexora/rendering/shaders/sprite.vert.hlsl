struct VSInput
{
    // Per-vertex quad data
    float2 position : TEXCOORD0;
    float2 uv       : TEXCOORD1;

    // Per-instance data
    float2 instance_position : TEXCOORD2;
    float2 instance_size     : TEXCOORD3;
    float  instance_rotation : TEXCOORD4;
    float2 instance_origin   : TEXCOORD5;
    float  instance_alpha    : TEXCOORD6;
    float  instance_flip_x   : TEXCOORD7;
    float  instance_flip_y   : TEXCOORD8;
    float2 instance_uv       : TEXCOORD9;
    float2 instance_uv_size  : TEXCOORD10;
};


struct VSOutput
{
    float4 position : SV_Position;
    float2 uv       : TEXCOORD0;
    float  alpha    : TEXCOORD1;
};


cbuffer CameraBuffer : register(b0, space1)
{
    float2 camera_position;
    float2 viewport_size;

    float camera_zoom;

    float2 camera_shake;

    float padding;
};


VSOutput main(
    VSInput input
)
{
    VSOutput output;

    // ==========================================================
    // LOCAL QUAD COORDINATES
    // ==========================================================

    float2 local = input.position;

    // ----------------------------------------------------------
    // Origin
    //
    // origin = (0.5, 0.5) -> center
    // origin = (0.0, 0.0) -> top-left
    // ----------------------------------------------------------

    local -= (
        input.instance_origin
        - 0.5
    );

    // ==========================================================
    // IMPORTANT
    //
    // Do NOT flip the geometry here.
    //
    // Sprite flipping is performed by flipping the UV
    // coordinates below.
    //
    // Flipping both geometry and UVs would cancel the visual
    // flip.
    // ==========================================================


    // ==========================================================
    // PIXEL SIZE
    // ==========================================================

    local *= (
        input.instance_size
    );


    // ==========================================================
    // ROTATION
    // ==========================================================

    float c = cos(
        input.instance_rotation
    );

    float s = sin(
        input.instance_rotation
    );

    float2 rotated;

    rotated.x =
        local.x * c
        - local.y * s;

    rotated.y =
        local.x * s
        + local.y * c;


    // ==========================================================
    // WORLD POSITION
    // ==========================================================

    float2 world_position =
        input.instance_position
        + rotated;


    // ==========================================================
    // CAMERA
    // ==========================================================

    float2 camera_relative =
        world_position
        - camera_position
        + camera_shake;

    camera_relative *= (
        camera_zoom
    );


    // ==========================================================
    // PIXEL -> NDC
    // ==========================================================

    float2 ndc;

    ndc.x =
        (
            camera_relative.x
            / viewport_size.x
        )
        * 2.0;

    ndc.y =
        -(
            camera_relative.y
            / viewport_size.y
        )
        * 2.0;


    output.position = float4(
        ndc,
        0.0,
        1.0
    );


    // ==========================================================
    // UV
    // ==========================================================

    float2 uv = (
        input.uv
    );


    // ----------------------------------------------------------
    // Horizontal flip
    // ----------------------------------------------------------

    if (
        input.instance_flip_x
        > 0.5
    )
    {
        uv.x = (
            1.0
            - uv.x
        );
    }


    // ----------------------------------------------------------
    // Vertical flip
    // ----------------------------------------------------------

    if (
        input.instance_flip_y
        > 0.5
    )
    {
        uv.y = (
            1.0
            - uv.y
        );
    }


    // ==========================================================
    // ATLAS UV
    // ==========================================================

    output.uv =
        input.instance_uv
        + uv
        * input.instance_uv_size;


    // ==========================================================
    // ALPHA
    // ==========================================================

    output.alpha = (
        input.instance_alpha
    );


    return output;
}