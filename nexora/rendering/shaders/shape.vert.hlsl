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
    float4 color    : TEXCOORD0;
    float2 local    : TEXCOORD1;
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

    /*
     * Original quad coordinates:
     *
     *     -0.5 ... +0.5
     *
     * Convert the normalized origin:
     *
     *     0.0 -> -0.5
     *     0.5 ->  0.0
     *     1.0 -> +0.5
     */
    float2 origin =
        input.instance_origin - 0.5;

    /*
     * Scale the quad.
     */
    float2 local =
        input.position * input.instance_size;

    /*
     * Move the local coordinates so that
     * the requested origin becomes the pivot.
     */
    local -= origin * input.instance_size;

    /*
     * Rotate around the origin.
     */
    float sine = sin(input.instance_rotation);
    float cosine = cos(input.instance_rotation);

    float2 rotated;

    rotated.x =
        local.x * cosine -
        local.y * sine;

    rotated.y =
        local.x * sine +
        local.y * cosine;

    /*
     * Transform into world space.
     */
    float2 world_position =
        input.instance_position +
        rotated;

    /*
     * Camera transformation.
     */
    float2 camera_relative =
        world_position -
        camera_position +
        camera_shake;

    camera_relative *= camera_zoom;

    /*
     * World -> NDC.
     */
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

    output.color =
        input.instance_color;

    /*
     * Keep the original untransformed quad coordinates.
     *
     * The fragment shader uses these coordinates
     * for the circle mask.
     */
    output.local =
        input.position;

    return output;
}