# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None
locale_paths = []
locales_full = next(os.walk('locale))[1]
for l in locales_full:
    locale_paths.append((f'locale\\{l}\\LC_MESSAGES\\pdfstitcher.mo',f'locale\\{l}\\LC_MESSAGES'))

a = Analysis(['pdfstitcher/pdfstitcher.py'],
             pathex=['.'],
             binaries=[],
             datas=locale_paths + [('resources\\stitcher-icon.ico','resources')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['numpy','Babel','PyYAML'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='pdfstitcher',
          icon='resources\\stitcher-icon.ico',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
