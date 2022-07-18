# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None
locale_paths = []
locales_full = next(os.walk("pdfstitcher\\locale"))[1]
for l in locales_full:
    locale_paths.append(
        (f"pdfstitcher\\locale\\{l}\\LC_MESSAGES\\pdfstitcher.mo", f"locale\\{l}\\LC_MESSAGES")
    )

datas = locale_paths + [("pdfstitcher\\resources\\stitcher-icon.ico", "resources")]
datas += copy_metadata('pdfstitcher', recursive=True)

a = Analysis(
    ["pdfstitcher\\pdfstitcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="pdfstitcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="pdfstitcher\\resources\\stitcher-icon.ico",
)
