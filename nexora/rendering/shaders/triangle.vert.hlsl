struct VSOutput
{
    float4 position : SV_Position;
    float4 color    : TEXCOORD0;
};

VSOutput main(uint vertex_id : SV_VertexID)
{
    float2 positions[3] =
    {
        float2( 0.0,  0.7),
        float2(-0.7, -0.7),
        float2( 0.7, -0.7)
    };

    float4 colors[3] =
    {
        float4(1.0, 0.0, 0.0, 1.0),
        float4(0.0, 1.0, 0.0, 1.0),
        float4(0.0, 0.0, 1.0, 1.0)
    };

    VSOutput output;

    output.position = float4(positions[vertex_id], 0.0, 1.0);
    output.color = colors[vertex_id];

    return output;
}