Texture2D<float4> texture0 : register(t0, space2);
SamplerState sampler0 : register(s0, space2);

struct PSInput
{
    float2 uv    : TEXCOORD0;
    float  alpha : TEXCOORD1;
};

float4 main(PSInput input) : SV_Target0
{
    float4 color =
        texture0.Sample(
            sampler0,
            input.uv
        );

    color.a *= input.alpha;

    return color;
}