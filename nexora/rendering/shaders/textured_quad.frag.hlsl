Texture2D<float4> texture0 : register(t0, space2);
SamplerState sampler0 : register(s0, space2);

struct PSInput
{
    float2 uv : TEXCOORD0;
};

float4 main(PSInput input) : SV_Target0
{
    return texture0.Sample(sampler0, input.uv);
}