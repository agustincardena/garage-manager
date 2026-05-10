# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ui\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('database/schema.sql', 'database'), ('locale', 'locale'), ('ui/theme/corporate_tokens.json', 'ui/theme'), ('ui/theme/style_config.json', 'ui/theme')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='GarageManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GarageManager',
)
