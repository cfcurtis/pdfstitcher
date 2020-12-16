# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

locales = ['de_DE','es_ES','fr_FR','nl_NL']
locale_paths = []
for l in locales:
    locale_paths.append((f'locale/{l}/LC_MESSAGES/pdfstitcher.mo',f'locale/{l}/LC_MESSAGES'))

a = Analysis(['pdfstitcher.py'],
             pathex=['/Users/charlotte/sewingutils'],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='pdfstitcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
app = BUNDLE(exe,
             name='pdfstitcher.app',
             icon=None,
             bundle_identifier=None)
