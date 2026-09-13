struct VSOutput
{
    float4 position : SV_Position;
    float2 uv       : TEXCOORD0;
};

VSOutput main(uint vertex_id : SV_VertexID)
{
    VSOutput output;

    float2 positions[6] =
    {
        float2(-0.5, -0.5),
        float2( 0.5, -0.5),
        float2( 0.5,  0.5),

        float2(-0.5, -0.5),
        float2( 0.5,  0.5),
        float2(-0.5,  0.5)
    };

    float2 uvs[6] =
    {
        float2(0.0, 0.0),
        float2(1.0, 0.0),
        float2(1.0, 1.0),

        float2(0.0, 0.0),
        float2(1.0, 1.0),
        float2(0.0, 1.0)
    };

    output.position = float4(positions[vertex_id], 0.0, 1.0);
    output.uv = uvs[vertex_id];

    return output;
}