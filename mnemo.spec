# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['entry.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['mnemo', 'mnemo.cli', 'mnemo.mcp_server', 'tree_sitter_python', 'tree_sitter_javascript', 'tree_sitter_typescript', 'tree_sitter_go', 'tree_sitter_c_sharp'],
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
    name='mnemo',
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
