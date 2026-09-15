Texture2D<float4> scene_texture
    : register(t0, space2);

SamplerState scene_sampler
    : register(s0, space2);


cbuffer PostProcessBuffer
    : register(b0, space3)
{
    // x = grayscale
    // y = vignette
    // z = brightness
    // w = contrast
    float4 color_settings;

    // x = saturation
    // y = chromatic aberration
    // z = film grain
    // w = scanline strength
    float4 effect_settings;

    // x = pixel size
    // y = distortion
    // z = time
    // w = health
    float4 dynamic_settings;

    // x = damage pulse
    // y = scanline frequency
    // z = screen width
    // w = screen height
    float4 screen_settings;

    // xyz = tint / color grading
    // w = distortion speed
    float4 tint_settings;

    // xyz = ambient light color
    // w = ambient intensity
    float4 ambient_settings;

    // x = active light count
    // y = lighting enabled (0/1)
    float4 lighting_settings;

    // xy = screen-space position in pixels
    // z = radius in pixels
    // w = intensity
    float4 light_position_radius_intensity[32];

    // xyz = light color
    // w = falloff exponent
    float4 light_color_falloff[32];
};


struct PSInput
{
    float2 uv : TEXCOORD0;
};


float random_noise(
    float2 position
)
{
    float3 p3 =
        frac(
            float3(
                position.xyx
            )
            * 0.1031
        );

    p3 += dot(
        p3,
        p3.yzx + 33.33
    );

    return frac(
        (
            p3.x + p3.y
        )
        * p3.z
    );
}


float3 apply_saturation(
    float3 color,
    float amount
)
{
    float luminance =
        dot(
            color,
            float3(
                0.2126,
                0.7152,
                0.0722
            )
        );

    return lerp(
        luminance.xxx,
        color,
        amount
    );
}


float4 sample_chromatic(
    float2 uv,
    float amount,
    float screen_width
)
{
    if (amount <= 0.0001)
    {
        return scene_texture.Sample(
            scene_sampler,
            uv
        );
    }

    float safe_width =
        max(
            screen_width,
            1.0
        );

    float2 offset =
        float2(
            amount / safe_width,
            0.0
        );

    float red =
        scene_texture.Sample(
            scene_sampler,
            uv + offset
        ).r;

    float green =
        scene_texture.Sample(
            scene_sampler,
            uv
        ).g;

    float blue =
        scene_texture.Sample(
            scene_sampler,
            uv - offset
        ).b;

    float alpha =
        scene_texture.Sample(
            scene_sampler,
            uv
        ).a;

    return float4(
        red,
        green,
        blue,
        alpha
    );
}


float3 apply_lighting(
    float3 base_color,
    float2 uv,
    float screen_width,
    float screen_height
)
{
    if (lighting_settings.y < 0.5)
    {
        return base_color;
    }

    float3 light_factor =
        ambient_settings.xyz
        * max(ambient_settings.w, 0.0);

    float2 pixel_position =
        uv * float2(screen_width, screen_height);

    int light_count =
        min((int)lighting_settings.x, 32);

    [loop]
    for (int index = 0; index < light_count; ++index)
    {
        float4 position_data =
            light_position_radius_intensity[index];

        float4 color_data =
            light_color_falloff[index];

        float radius = max(position_data.z, 0.0001);
        float distance_to_light =
            length(pixel_position - position_data.xy);

        float attenuation = saturate(
            1.0 - distance_to_light / radius
        );

        attenuation = pow(
            attenuation,
            max(color_data.w, 0.01)
        );

        light_factor +=
            color_data.xyz
            * max(position_data.w, 0.0)
            * attenuation;
    }

    return base_color * max(light_factor, 0.0);
}


float4 main(
    PSInput input
) : SV_Target0
{
    // ----------------------------------------------------------
    // Settings
    // ----------------------------------------------------------

    float grayscale =
        color_settings.x;

    float vignette =
        color_settings.y;

    float brightness =
        color_settings.z;

    float contrast =
        color_settings.w;

    float saturation =
        effect_settings.x;

    float chromatic_aberration =
        effect_settings.y;

    float film_grain =
        effect_settings.z;

    float scanlines =
        effect_settings.w;

    float pixel_size =
        max(
            dynamic_settings.x,
            1.0
        );

    float distortion =
        dynamic_settings.y;

    float time =
        dynamic_settings.z;

    float health =
        saturate(
            dynamic_settings.w
        );

    float damage_pulse =
        screen_settings.x;

    float scanline_frequency =
        max(
            screen_settings.y,
            0.01
        );

    float screen_width =
        max(
            screen_settings.z,
            1.0
        );

    float screen_height =
        max(
            screen_settings.w,
            1.0
        );

    float3 tint =
        tint_settings.xyz;

    float distortion_speed =
        tint_settings.w;

    // ----------------------------------------------------------
    // UV
    // ----------------------------------------------------------

    float2 uv =
        input.uv;

    // ----------------------------------------------------------
    // Distortion
    // ----------------------------------------------------------

    if (distortion > 0.0001)
    {
        float wave_x =
            sin(
                uv.y
                * 14.0
                + time
                * distortion_speed
            );

        float wave_y =
            cos(
                uv.x
                * 11.0
                + time
                * distortion_speed
                * 0.8
            );

        uv.x +=
            wave_x
            * distortion
            * 0.008;

        uv.y +=
            wave_y
            * distortion
            * 0.005;
    }

    // ----------------------------------------------------------
    // Pixelation
    // ----------------------------------------------------------

    if (pixel_size > 1.0)
    {
        float2 resolution =
            float2(
                screen_width,
                screen_height
            );

        float2 pixel_position =
            uv
            * resolution;

        pixel_position =
            floor(
                pixel_position
                / pixel_size
            )
            * pixel_size;

        pixel_position +=
            pixel_size
            * 0.5;

        uv =
            pixel_position
            / resolution;
    }

    uv = saturate(
        uv
    );

    // ----------------------------------------------------------
    // Scene sample + chromatic aberration
    // ----------------------------------------------------------

    float4 color =
        sample_chromatic(
            uv,
            chromatic_aberration,
            screen_width
        );

    // ----------------------------------------------------------
    // Brightness
    // ----------------------------------------------------------

    color.rgb *=
        brightness;

    // ----------------------------------------------------------
    // Contrast
    // ----------------------------------------------------------

    color.rgb =
        (
            color.rgb
            - 0.5
        )
        * contrast
        + 0.5;

    // ----------------------------------------------------------
    // Saturation
    // ----------------------------------------------------------

    color.rgb =
        apply_saturation(
            color.rgb,
            saturation
        );

    // ----------------------------------------------------------
    // Grayscale
    // ----------------------------------------------------------

    float luminance =
        dot(
            color.rgb,
            float3(
                0.2126,
                0.7152,
                0.0722
            )
        );

    color.rgb =
        lerp(
            color.rgb,
            luminance.xxx,
            saturate(
                grayscale
            )
        );

    // ----------------------------------------------------------
    // Color grading / tint
    // ----------------------------------------------------------

    color.rgb *=
        tint;

    // ----------------------------------------------------------
    // 2D lighting
    // ----------------------------------------------------------

    color.rgb = apply_lighting(
        color.rgb,
        input.uv,
        screen_width,
        screen_height
    );

    // ----------------------------------------------------------
    // Vignette
    // ----------------------------------------------------------

    float2 centered_uv =
        input.uv
        - 0.5;

    float distance_from_center =
        length(
            centered_uv
        );

    float vignette_mask =
        smoothstep(
            0.25,
            0.72,
            distance_from_center
        );

    color.rgb *=
        1.0
        - vignette_mask
        * saturate(
            vignette
        );

    // ----------------------------------------------------------
    // Scanlines
    // ----------------------------------------------------------

    if (scanlines > 0.0001)
    {
        float scan =
            sin(
                input.uv.y
                * screen_height
                * 3.14159265
                * scanline_frequency
            );

        scan =
            scan
            * 0.5
            + 0.5;

        float scan_darkening =
            (
                1.0
                - scan
            )
            * saturate(
                scanlines
            )
            * 0.35;

        color.rgb *=
            1.0
            - scan_darkening;
    }

    // ----------------------------------------------------------
    // Film grain
    // ----------------------------------------------------------

    if (film_grain > 0.0001)
    {
        float noise =
            random_noise(
                input.uv
                * screen_height
                + time
                * 17.0
            );

        noise =
            noise
            - 0.5;

        color.rgb +=
            noise
            * film_grain
            * 0.20;
    }

    // ----------------------------------------------------------
    // Low health / damage effect
    // ----------------------------------------------------------

    float low_health =
        1.0
        - health;

    if (
        low_health > 0.0001
        && damage_pulse > 0.0001
    )
    {
        float heartbeat =
            0.5
            + 0.5
            * sin(
                time
                * 7.5
            );

        heartbeat =
            heartbeat
            * heartbeat;

        float damage_amount =
            low_health
            * damage_pulse
            * (
                0.35
                + heartbeat
                * 0.65
            );

        // Red tint
        float3 damage_color =
            float3(
                1.0,
                0.08,
                0.05
            );

        color.rgb =
            lerp(
                color.rgb,
                color.rgb
                * damage_color,
                saturate(
                    damage_amount
                    * 0.65
                )
            );

        // Stronger edge darkening
        color.rgb *=
            1.0
            - vignette_mask
            * damage_amount
            * 0.60;
    }

    // ----------------------------------------------------------
    // Clamp
    // ----------------------------------------------------------

    color.rgb =
        saturate(
            color.rgb
        );

    return color;
}