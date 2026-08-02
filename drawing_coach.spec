# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Drawing Coach — onedir, cross-platform."""
import subprocess
import sys
from pathlib import Path

# Stamp version before analysis
subprocess.run([sys.executable, "scripts/build_version.py"], check=True)

block_cipher = None

a = Analysis(
    ["src/drawing_coach/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pynput backend selection happens at runtime
        "pynput.keyboard._xorg",
        "pynput.keyboard._win32",
        "pynput.keyboard._darwin",
        "pynput.mouse._xorg",
        "pynput.mouse._win32",
        "pynput.mouse._darwin",
        # litellm encoders
        "tiktoken_ext.openai_public",
        "tiktoken_ext",
        # mss platform backends
        "mss.darwin",
        "mss.linux",
        "mss.windows",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["fastapi", "uvicorn", "starlette", "httpx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="drawing-coach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="drawing-coach",
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Drawing Coach.app",
        icon=None,
        bundle_identifier="com.drawing-coach.app",
        info_plist=str(Path("scripts/macos/Info.plist").resolve()),
    )
