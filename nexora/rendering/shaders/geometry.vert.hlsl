cbuffer Camera : register(b0, space1)
{
    float2 camera_position;
    float2 viewport_size;
    float camera_zoom;
    float2 camera_shake;
    float _padding;
};

struct VSInput
{
    float2 position : POSITION;
    float4 color    : COLOR0;
};

struct VSOutput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

VSOutput main(VSInput input)
{
    VSOutput output;

    float2 world_position =
        input.position
        - camera_position
        + camera_shake;

    world_position *= camera_zoom;

    float2 normalized =
        world_position
        / (viewport_size * 0.5);

    normalized.y = -normalized.y;

    output.position = float4(
        normalized,
        0.0,
        1.0
    );

    output.color = input.color;

    return output;
}