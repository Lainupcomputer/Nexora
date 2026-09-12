struct PSInput
{
    float4 color : TEXCOORD0;

    float2 local_position : TEXCOORD1;
    float2 size           : TEXCOORD2;
    float  radius         : TEXCOORD3;
};

float rounded_box_sdf(
    float2 p,
    float2 half_size,
    float radius
)
{
    float2 q =
        abs(p) -
        half_size +
        radius;

    return length(max(q, 0.0))
        + min(max(q.x, q.y), 0.0)
        - radius;
}

float4 main(PSInput input) : SV_Target0
{
    float2 half_size =
        input.size * 0.5;

    float radius =
        min(
            input.radius,
            min(
                half_size.x,
                half_size.y
            )
        );

    float distance =
        rounded_box_sdf(
            input.local_position,
            half_size,
            radius
        );

    // Fully inside
    if (distance <= 0.0)
    {
        return input.color;
    }

    // Outside
    discard;

    return float4(
        0.0,
        0.0,
        0.0,
        0.0
    );
}