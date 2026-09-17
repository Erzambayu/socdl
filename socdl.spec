# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for socdl.

Build:
    pyinstaller socdl.spec --clean --noconfirm

Output: dist/socdl (or dist/socdl.exe on Windows).
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Make sure dynamically-imported platform backends are bundled.
hiddenimports = []
for pkg in ("yt_dlp", "gallery_dl", "instaloader", "platformdirs", "rich", "click"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# gallery-dl & yt-dlp rely on certifi for TLS roots
hiddenimports += ["certifi"]

datas = []
try:
    import certifi
    datas.append((certifi.where(), "certifi"))
except Exception:
    pass

a = Analysis(
    ["socdl_entry.py"],
    pathex=[str(Path("src").resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PyQt5", "PySide6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="socdl",
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
