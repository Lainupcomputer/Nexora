# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    copy_metadata,
)


# ==============================================================
# Paths
# ==============================================================

PROJECT_DIR = Path(SPECPATH).resolve()

ENGINE_DIR = PROJECT_DIR.parent


# ==============================================================
# Nexora package
# ==============================================================

(
    nexora_datas,
    nexora_binaries,
    nexora_hiddenimports,
) = collect_all(
    "nexora"
)

nexora_hiddenimports += collect_submodules(
    "nexora"
)


# ==============================================================
# PySDL3 package
# ==============================================================

(
    sdl3_datas,
    sdl3_binaries,
    sdl3_hiddenimports,
) = collect_all(
    "sdl3"
)

sdl3_hiddenimports += collect_submodules(
    "sdl3"
)


# --------------------------------------------------------------
# PySDL3 metadata
# --------------------------------------------------------------
#
# PySDL3 checks its installed distribution metadata.
#
# Without this, the frozen application may show:
#
#     Warning: No metadata detected.
#
# and may try downloading SDL binaries at runtime.
# --------------------------------------------------------------

sdl3_metadata = copy_metadata(
    "PySDL3"
)


# ==============================================================
# Hidden imports
# ==============================================================

hiddenimports = [
    # ----------------------------------------------------------
    # Python standard library
    # ----------------------------------------------------------

    "wave",

    # ----------------------------------------------------------
    # Nexora
    # ----------------------------------------------------------

    *nexora_hiddenimports,

    # ----------------------------------------------------------
    # PySDL3
    # ----------------------------------------------------------

    *sdl3_hiddenimports,
]


# Remove duplicates while preserving order.
hiddenimports = list(
    dict.fromkeys(
        hiddenimports
    )
)


# ==============================================================
# Data files
# ==============================================================

datas = [
    # Nexora package data
    *nexora_datas,

    # PySDL3 package data
    *sdl3_datas,

    # PySDL3 distribution metadata
    *sdl3_metadata,
]


# ==============================================================
# Game assets
# ==============================================================

assets_dir = (
    PROJECT_DIR
    / "assets"
)

if assets_dir.is_dir():
    datas.append(
        (
            str(
                assets_dir
            ),
            "assets",
        )
    )


# ==============================================================
# Optional game data directory
# ==============================================================

data_dir = (
    PROJECT_DIR
    / "data"
)

if data_dir.is_dir():
    datas.append(
        (
            str(
                data_dir
            ),
            "data",
        )
    )


# ==============================================================
# Optional game shaders
# ==============================================================

shaders_dir = (
    PROJECT_DIR
    / "shaders"
)

if shaders_dir.is_dir():
    datas.append(
        (
            str(
                shaders_dir
            ),
            "shaders",
        )
    )


# ==============================================================
# Binary files
# ==============================================================

binaries = [
    # Nexora binaries
    *nexora_binaries,

    # PySDL3 / SDL binaries
    *sdl3_binaries,
]


# ==============================================================
# Analysis
# ==============================================================

a = Analysis(
    [
        str(
            PROJECT_DIR
            / "main.py"
        ),
    ],

    # ----------------------------------------------------------
    # Module search paths
    # ----------------------------------------------------------
    #
    # Structure:
    #
    # Nexora Engine/
    # ├── nexora/
    # └── MyGame/
    #     ├── main.py
    #     └── MyGame.spec
    #
    # PROJECT_DIR:
    #     MyGame/
    #
    # ENGINE_DIR:
    #     Nexora Engine/
    #
    # This allows PyInstaller to find:
    #
    #     Nexora Engine/nexora/
    # ----------------------------------------------------------

    pathex=[
        str(
            PROJECT_DIR
        ),
        str(
            ENGINE_DIR
        ),
    ],

    binaries=binaries,

    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    excludes=[],

    noarchive=False,

    optimize=0,
)


# ==============================================================
# Python archive
# ==============================================================

pyz = PYZ(
    a.pure
)


# ==============================================================
# Python runtime options
# ==============================================================

runtime_options = [
    # ----------------------------------------------------------
    # Python 3.13 free-threading / No-GIL
    #
    # Equivalent to:
    #
    #     python -Xgil=0 main.py
    #
    # The build must itself be created using a free-threaded
    # Python interpreter.
    # ----------------------------------------------------------

    (
        "X gil=0",
        None,
        "OPTION",
    ),
]


# ==============================================================
# Executable
# ==============================================================

exe = EXE(
    pyz,

    a.scripts,

    runtime_options,

    exclude_binaries=True,

    name="MyGame",

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=False,

    console=True,

    disable_windowed_traceback=False,

    argv_emulation=False,

    target_arch=None,

    codesign_identity=None,

    entitlements_file=None,
)


# ==============================================================
# Onedir collection
# ==============================================================

coll = COLLECT(
    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=False,

    upx_exclude=[],

    name="MyGame",
)