struct PSInput
{
    float4 color : TEXCOORD0;
    float2 local : TEXCOORD1;
};

float4 main(PSInput input) : SV_Target0
{
    float distance_squared =
        dot(
            input.local,
            input.local
        );

    if (distance_squared > 0.25)
    {
        discard;
    }

    return input.color;
}