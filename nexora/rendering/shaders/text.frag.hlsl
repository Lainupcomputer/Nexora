Texture2D<float4> texture0 : register(t0, space2);
SamplerState sampler0 : register(s0, space2);

cbuffer TextColorBuffer : register(b0, space3)
{
    float4 text_color;
};

struct PSInput
{
    float2 uv    : TEXCOORD0;
    float  alpha : TEXCOORD1;
};

float4 main(PSInput input) : SV_Target0
{
    float4 glyph =
        texture0.Sample(
            sampler0,
            input.uv
        );

    float4 color =
        glyph * text_color;

    color.a *= input.alpha;

    return color;
}