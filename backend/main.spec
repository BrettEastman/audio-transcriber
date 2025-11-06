# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

# Robustly collect Whisper package data (e.g., assets/mel_filters.npz)
whisper_datas = collect_data_files('whisper', includes=['assets/*'])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=whisper_datas,
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'whisper',
        'torch',
        'numpy',
        'pydantic',
        'tempfile',
        'asyncio',
        'uuid',
        'logging',
        'shutil',
        'signal',
        'sys',
        'contextlib'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main_with_assets-aarch64-apple-darwin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
