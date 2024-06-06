# -*- mode: python ; coding: utf-8 -*-

import os
import platform
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import importlib.metadata
__version__ = importlib.metadata.version("pdfstitcher")

APPLE_SIGN_IDENTITY = os.environ["APPLE_SIGN_IDENTITY"]

block_cipher = None
locale_paths = []
locales_full = next(os.walk("pdfstitcher/locale"))[1]
for l in locales_full:
    locale_paths.append(
        (f"pdfstitcher/locale/{l}/LC_MESSAGES/pdfstitcher.mo", f"locale/{l}/LC_MESSAGES")
    )

datas = locale_paths
datas += copy_metadata('pdfstitcher', recursive=True)
datas += collect_data_files('pdf_mangler')

a = Analysis(
    ["pdfstitcher/gui/app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['babel.numbers'],
    hookspath=[],
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
    target_arch=platform.machine(),
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    codesign_identity=APPLE_SIGN_IDENTITY
)
app = BUNDLE(
    exe,
    name="pdfstitcher.app",
    icon="pdfstitcher/resources/stitcher-icon.icns",
    bundle_identifier="com.charlottecurtis.pdfstitcher",
    version=f"{__version__}",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeExtensions": ["pdf"],
                "LSItemContentTypes": ["com.adobe.pdf"],
                "CFBundlerTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
            }
        ],
    },
)
