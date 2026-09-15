param(
    [switch]$Clean,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ============================================================
# Nexora Shader Builder
#
# HLSL -> SPIR-V using DXC
# ============================================================

$Root = Split-Path -Parent $PSScriptRoot

$ShaderDir = Join-Path `
    $Root `
    "nexora\rendering\shaders"

$OutputDir = Join-Path `
    $ShaderDir `
    "bin"

$DXC = Join-Path `
    $Root `
    "tools\dxc\dxc.exe"


Write-Host ""
Write-Host "============================================================"
Write-Host " Nexora Shader Builder"
Write-Host "============================================================"
Write-Host ""

Write-Host "Project:"
Write-Host "  $Root"
Write-Host ""

Write-Host "DXC:"
Write-Host "  $DXC"
Write-Host ""

Write-Host "Shader source:"
Write-Host "  $ShaderDir"
Write-Host ""

Write-Host "Shader output:"
Write-Host "  $OutputDir"
Write-Host ""


# ============================================================
# VALIDATE DXC
# ============================================================

if (-not (Test-Path $DXC)) {

    Write-Host "ERROR: DXC was not found:"
    Write-Host ""
    Write-Host "  $DXC"
    Write-Host ""

    exit 1
}


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

if (-not (Test-Path $OutputDir)) {

    New-Item `
        -ItemType Directory `
        -Path $OutputDir `
        | Out-Null
}


# ============================================================
# CLEAN
# ============================================================

if ($Clean) {

    Write-Host "Cleaning compiled shaders..."
    Write-Host ""

    Get-ChildItem `
        $OutputDir `
        -Filter "*.spv" `
        -File `
        -ErrorAction SilentlyContinue `
        | Remove-Item -Force
}


# ============================================================
# FIND SHADERS
# ============================================================

$Shaders = Get-ChildItem `
    $ShaderDir `
    -Filter "*.hlsl" `
    -File `
    | Sort-Object Name


if ($Shaders.Count -eq 0) {

    Write-Host "No HLSL shaders found."
    Write-Host ""

    exit 0
}


Write-Host (
    "Found {0} shader source(s)." `
        -f $Shaders.Count
)

Write-Host ""


# ============================================================
# COUNTERS
# ============================================================

$Built = 0
$Skipped = 0
$Failed = 0


# ============================================================
# BUILD
# ============================================================

foreach ($Shader in $Shaders) {

    # --------------------------------------------------------
    # Determine shader stage from filename
    #
    # *.vert.hlsl -> vs_6_0
    # *.frag.hlsl -> ps_6_0
    # *.comp.hlsl -> cs_6_0
    # --------------------------------------------------------

    if (
        $Shader.Name -match "\.vert\.hlsl$"
    ) {

        $Profile = "vs_6_0"

    }
    elseif (
        $Shader.Name -match "\.frag\.hlsl$"
    ) {

        $Profile = "ps_6_0"

    }
    elseif (
        $Shader.Name -match "\.comp\.hlsl$"
    ) {

        $Profile = "cs_6_0"

    }
    else {

        Write-Host (
            "[SKIP] {0} - unknown shader stage" `
                -f $Shader.Name
        )

        $Skipped++

        continue
    }


    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    $InputFile = (
        $Shader.FullName
    )

    $OutputName = (
        $Shader.Name `
            -replace "\.hlsl$", ".spv"
    )

    $OutputFile = Join-Path `
        $OutputDir `
        $OutputName


    # --------------------------------------------------------
    # Incremental build
    # --------------------------------------------------------

    $NeedsBuild = $true

    if (
        (-not $Force) `
        -and `
        (Test-Path $OutputFile)
    ) {

        $OutputInfo = (
            Get-Item $OutputFile
        )

        if (
            $OutputInfo.LastWriteTimeUtc `
            -ge `
            $Shader.LastWriteTimeUtc
        ) {

            $NeedsBuild = $false
        }
    }


    if (-not $NeedsBuild) {

        Write-Host (
            "[SKIP] {0}" `
                -f $Shader.Name
        )

        $Skipped++

        continue
    }


    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    Write-Host (
        "[BUILD] {0}" `
            -f $Shader.Name
    )

    Write-Host (
        "        profile: {0}" `
            -f $Profile
    )

    Write-Host (
        "        output:  {0}" `
            -f $OutputName
    )


    & $DXC `
        -spirv `
        -T $Profile `
        -E main `
        -Fo $OutputFile `
        $InputFile


    # --------------------------------------------------------
    # Check DXC result
    # --------------------------------------------------------

    if ($LASTEXITCODE -ne 0) {

        Write-Host ""
        Write-Host (
            "[FAILED] {0}" `
                -f $Shader.Name
        )
        Write-Host ""

        $Failed++

        break
    }


    # --------------------------------------------------------
    # Verify output
    # --------------------------------------------------------

    if (-not (Test-Path $OutputFile)) {

        Write-Host ""
        Write-Host "ERROR: DXC returned successfully but"
        Write-Host "the output file was not created:"
        Write-Host ""
        Write-Host "  $OutputFile"
        Write-Host ""

        $Failed++

        break
    }


    $Built++

    Write-Host "        OK"
    Write-Host ""
}


# ============================================================
# SUMMARY
# ============================================================

Write-Host "============================================================"
Write-Host " Shader Build Summary"
Write-Host "============================================================"
Write-Host ""

Write-Host (
    "Built:   {0}" `
        -f $Built
)

Write-Host (
    "Skipped: {0}" `
        -f $Skipped
)

Write-Host (
    "Failed:  {0}" `
        -f $Failed
)

Write-Host ""


# ============================================================
# RESULT
# ============================================================

if ($Failed -gt 0) {

    Write-Host "Shader build FAILED."
    Write-Host ""

    exit 1
}


Write-Host "Shader build completed successfully."
Write-Host ""

exit 0