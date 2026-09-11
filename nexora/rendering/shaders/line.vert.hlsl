struct VSInput
{
    float2 position : TEXCOORD0;

    float2 instance_position : TEXCOORD1;
    float2 instance_size     : TEXCOORD2;
    float  instance_rotation : TEXCOORD3;
    float2 instance_origin   : TEXCOORD4;
    float4 instance_color    : TEXCOORD5;
};

struct VSOutput
{
    float4 position : SV_Position;
    float4 color : TEXCOORD0;
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

    float2 local = input.position;

    local -= (input.instance_origin - 0.5);

    local *= input.instance_size;

    float c = cos(input.instance_rotation);
    float s = sin(input.instance_rotation);

    float2 rotated;

    rotated.x =
        local.x * c -
        local.y * s;

    rotated.y =
        local.x * s +
        local.y * c;

    float2 world_position =
        input.instance_position +
        rotated;

    float2 camera_relative =
        world_position -
        camera_position +
        camera_shake;

    camera_relative *= camera_zoom;

    float2 ndc;

    ndc.x =
        (camera_relative.x /
         viewport_size.x) * 2.0;

    ndc.y =
        -(camera_relative.y /
          viewport_size.y) * 2.0;

    output.position =
        float4(
            ndc,
            0.0,
            1.0
        );

    output.color =
        input.instance_color;

    return output;
}