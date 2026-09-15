param(
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"

# ============================================================
# PROJECT PATHS
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$ProjectName = Split-Path -Leaf $ProjectRoot

# ============================================================
# OUTPUT ZIP
# ============================================================

if ([string]::IsNullOrWhiteSpace($Output)) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $FileName = $ProjectName + "_" + $Timestamp + ".zip"
    $Output = Join-Path $ProjectRoot $FileName
}
elseif (-not [System.IO.Path]::IsPathRooted($Output)) {
    $Output = Join-Path $ProjectRoot $Output
}

$Output = [System.IO.Path]::GetFullPath($Output)

# ============================================================
# TEMP DIRECTORY
# ============================================================

$TempName = "nexora_package_" + [guid]::NewGuid().ToString("N")
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) $TempName
$StageRoot = Join-Path $TempRoot $ProjectName

# ============================================================
# EXCLUDED DIRECTORY NAMES
#
# These are excluded wherever they occur.
# ============================================================

$ExcludedDirectoryNames = @(
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "htmlcov",
    "_build",
    "saves"
)

# ============================================================
# EXCLUDED ROOT DIRECTORIES
#
# These are only excluded when they are directly inside the
# project root.
#
# IMPORTANT:
#
#   nexora\settings\
#
# remains INCLUDED.
#
# Only:
#
#   <project>\settings\
#
# is excluded because that is local runtime configuration.
# ============================================================

$ExcludedRootDirectories = @(
    "settings"
)

# ============================================================
# EXCLUDED FILE PATTERNS
# ============================================================

$ExcludedFilePatterns = @(
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.backup",
    "*.swp",
    "*.swo",
    "*.zip",
    "*.7z",
    "*.rar",
    ".coverage",
    "coverage.xml",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    ".env.*"
)

# ============================================================
# RELATIVE PATH
#
# Compatible with Windows PowerShell 5.1.
# ============================================================

function Get-RelativePath {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $BasePath = [System.IO.Path]::GetFullPath($BasePath)
    $TargetPath = [System.IO.Path]::GetFullPath($TargetPath)

    if (-not $BasePath.EndsWith("\")) {
        $BasePath += "\"
    }

    $BaseUri = New-Object System.Uri($BasePath)
    $TargetUri = New-Object System.Uri($TargetPath)

    $RelativeUri = $BaseUri.MakeRelativeUri($TargetUri)

    $RelativePath = [System.Uri]::UnescapeDataString(
        $RelativeUri.ToString()
    )

    return $RelativePath.Replace("/", "\")
}

# ============================================================
# DIRECTORY CHECK
# ============================================================

function Test-ExcludedDirectory {
    param(
        [string]$RelativeDirectory
    )

    if ([string]::IsNullOrWhiteSpace($RelativeDirectory)) {
        return $false
    }

    $Normalized = $RelativeDirectory.Replace("/", "\")
    $Parts = $Normalized -split "\\"

    # --------------------------------------------------------
    # Root-only exclusions
    # --------------------------------------------------------

    if ($Parts.Count -gt 0) {
        $RootDirectory = $Parts[0]

        foreach ($Excluded in $ExcludedRootDirectories) {
            if ($RootDirectory -ieq $Excluded) {
                return $true
            }
        }
    }

    # --------------------------------------------------------
    # Global directory exclusions
    # --------------------------------------------------------

    foreach ($Part in $Parts) {
        foreach ($Excluded in $ExcludedDirectoryNames) {
            if ($Part -ieq $Excluded) {
                return $true
            }
        }

        if ($Part -like "*.egg-info") {
            return $true
        }
    }

    return $false
}

# ============================================================
# FILE CHECK
# ============================================================

function Test-ExcludedFile {
    param(
        [System.IO.FileInfo]$File,
        [string]$RelativePath
    )

    # Never include the ZIP currently being generated.

    $FilePath = [System.IO.Path]::GetFullPath($File.FullName)

    if ($FilePath -ieq $Output) {
        return $true
    }

    # Check parent directory.

    $Parent = Split-Path -Parent $RelativePath

    if (-not [string]::IsNullOrWhiteSpace($Parent)) {
        if (Test-ExcludedDirectory $Parent) {
            return $true
        }
    }

    # Check filename.

    foreach ($Pattern in $ExcludedFilePatterns) {
        if ($File.Name -like $Pattern) {
            return $true
        }
    }

    return $false
}

# ============================================================
# HEADER
# ============================================================

Write-Host ""
Write-Host "============================================================"
Write-Host " Nexora Project Packager"
Write-Host "============================================================"
Write-Host ""

Write-Host "PowerShell:"
Write-Host "  $($PSVersionTable.PSVersion)"
Write-Host ""

Write-Host "Project:"
Write-Host "  $ProjectRoot"
Write-Host ""

Write-Host "Output:"
Write-Host "  $Output"
Write-Host ""

# ============================================================
# CREATE TEMP DIRECTORY
# ============================================================

if (Test-Path -LiteralPath $TempRoot) {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $StageRoot -Force | Out-Null

try {

    # ========================================================
    # SCAN PROJECT
    # ========================================================

    Write-Host "Scanning project..."
    Write-Host ""

    $Files = Get-ChildItem `
        -LiteralPath $ProjectRoot `
        -Recurse `
        -File `
        -Force

    $IncludedFiles = @()
    $ExcludedCount = 0

    foreach ($File in $Files) {

        $RelativePath = Get-RelativePath `
            -BasePath $ProjectRoot `
            -TargetPath $File.FullName

        if (Test-ExcludedFile `
            -File $File `
            -RelativePath $RelativePath) {

            $ExcludedCount++
            continue
        }

        $IncludedFiles += [PSCustomObject]@{
            File = $File
            RelativePath = $RelativePath
        }
    }

    Write-Host "Included files: $($IncludedFiles.Count)"
    Write-Host "Excluded files: $ExcludedCount"
    Write-Host ""

    # ========================================================
    # COPY FILES
    # ========================================================

    Write-Host "Preparing package..."

    foreach ($Entry in $IncludedFiles) {

        $Destination = Join-Path `
            $StageRoot `
            $Entry.RelativePath

        $DestinationDirectory = Split-Path `
            -Parent `
            $Destination

        if (-not (Test-Path -LiteralPath $DestinationDirectory)) {
            New-Item `
                -ItemType Directory `
                -Path $DestinationDirectory `
                -Force |
                Out-Null
        }

        Copy-Item `
            -LiteralPath $Entry.File.FullName `
            -Destination $Destination `
            -Force
    }

    # ========================================================
    # REMOVE OLD OUTPUT WITH SAME NAME
    # ========================================================

    if (Test-Path -LiteralPath $Output) {
        Write-Host "Removing existing archive..."

        Remove-Item `
            -LiteralPath $Output `
            -Force
    }

    # ========================================================
    # CREATE ZIP
    # ========================================================

    Write-Host "Creating ZIP..."

    Compress-Archive `
        -Path $StageRoot `
        -DestinationPath $Output `
        -CompressionLevel Optimal

    # ========================================================
    # RESULT
    # ========================================================

    $Zip = Get-Item -LiteralPath $Output
    $SizeMB = $Zip.Length / 1MB

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " Package created successfully"
    Write-Host "============================================================"
    Write-Host ""

    Write-Host "Included files:"
    Write-Host "  $($IncludedFiles.Count)"
    Write-Host ""

    Write-Host "Excluded files:"
    Write-Host "  $ExcludedCount"
    Write-Host ""

    Write-Host "ZIP size:"
    Write-Host ("  {0:N2} MB" -f $SizeMB)
    Write-Host ""

    Write-Host "Archive:"
    Write-Host "  $Output"
    Write-Host ""
}
finally {

    # ========================================================
    # CLEAN TEMP DIRECTORY
    # ========================================================

    if (Test-Path -LiteralPath $TempRoot) {

        Write-Host "Cleaning temporary files..."

        Remove-Item `
            -LiteralPath $TempRoot `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }
}