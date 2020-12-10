# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

locales = ['de_DE','es_ES','fr_FR','nl_NL']
locale_paths = []
for l in locales:
    locale_paths.append((f'locale\\{l}\\LC_MESSAGES\\pdfstitcher.mo',f'locale\\{l}\\LC_MESSAGES'))

a = Analysis(['pdfstitcher.py'],
             pathex=['C:\\Users\\cfcur\\Documents\\Python\\sewingutils'],
             binaries=[],
             datas=locale_paths,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='pdfstitcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='pdfstitcher')
