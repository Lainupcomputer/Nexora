struct VSInput
{
    // Per-vertex quad data
    float2 position : TEXCOORD0;

    // Per-instance data
    float2 instance_position  : TEXCOORD1;
    float2 instance_size      : TEXCOORD2;
    float  instance_rotation  : TEXCOORD3;
    float2 instance_origin    : TEXCOORD4;
    float  instance_radius    : TEXCOORD5;
    float4 instance_color     : TEXCOORD6;
};

struct VSOutput
{
    float4 position       : SV_Position;
    float4 color          : TEXCOORD0;

    // Position inside the rectangle, centered around 0,0.
    // Used by the fragment shader for the rounded-corner SDF.
    float2 local_position : TEXCOORD1;
    float2 size            : TEXCOORD2;
    float  radius          : TEXCOORD3;
};

cbuffer CameraBuffer : register(b0, space1)
{
    float2 camera_position;
    float2 viewport_size;

    float camera_zoom;

    float2 camera_shake;

    float padding;
};

VSOutput main(VSInput input)
{
    VSOutput output;

    // --------------------------------------------------------------
    // Local quad coordinates
    // --------------------------------------------------------------

    float2 local = input.position;

    // Keep a centered version for the fragment shader.
    float2 centered_local =
        input.position *
        input.instance_size;

    // origin = (0.5, 0.5) -> center
    // origin = (0.0, 0.0) -> top-left
    local -= (input.instance_origin - 0.5);

    // --------------------------------------------------------------
    // Pixel size
    // --------------------------------------------------------------

    local *= input.instance_size;

    // --------------------------------------------------------------
    // Rotation
    // --------------------------------------------------------------

    float c = cos(input.instance_rotation);
    float s = sin(input.instance_rotation);

    float2 rotated;

    rotated.x =
        local.x * c -
        local.y * s;

    rotated.y =
        local.x * s +
        local.y * c;

    // --------------------------------------------------------------
    // World / screen position
    // --------------------------------------------------------------

    float2 world_position =
        input.instance_position +
        rotated;

    // --------------------------------------------------------------
    // Camera
    // --------------------------------------------------------------

    float2 camera_relative =
        world_position -
        camera_position +
        camera_shake;

    camera_relative *= camera_zoom;

    // --------------------------------------------------------------
    // Pixel -> NDC
    // --------------------------------------------------------------

    float2 ndc;

    ndc.x =
        (camera_relative.x / viewport_size.x) * 2.0;

    ndc.y =
        -(camera_relative.y / viewport_size.y) * 2.0;

    output.position =
        float4(
            ndc,
            0.0,
            1.0
        );

    // --------------------------------------------------------------
    // Fragment data
    // --------------------------------------------------------------

    output.color = input.instance_color;

    output.local_position = centered_local;
    output.size = input.instance_size;
    output.radius = input.instance_radius;

    return output;
}