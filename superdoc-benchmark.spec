# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

datas = [
    ('scripts/export_word_pdf.applescript', 'scripts'),
    ('harness', 'harness'),
    ('node', 'node'),
]
binaries = []
# Rich dynamically imports unicode data modules like:
# rich._unicode_data.unicode17-0-0
# PyInstaller does not reliably detect these, so include all submodules.
hiddenimports = collect_submodules('rich._unicode_data')

a = Analysis(
    ['src/superdoc_benchmark/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='superdoc-benchmark',
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
