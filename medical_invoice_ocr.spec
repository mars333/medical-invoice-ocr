# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata


datas = []
binaries = []
hiddenimports = []
datas += collect_data_files("medical_invoice_ocr")
for package in (
    "paddle",
    "paddleocr",
    "paddlex",
    "modelscope",
    "modelscope_hub",
    "aistudio_sdk",
    "cv2",
    "shapely",
    "pyclipper",
    "imagesize",
    "pypdfium2",
    "bidi",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# PaddleX checks the installed distribution metadata at runtime before it
# creates the OCR pipeline.  PyInstaller does not include this metadata merely
# because the importable modules are present, so keep the OCR-core records.
for distribution in (
    "paddlex",
    "imagesize",
    "opencv-contrib-python",
    "pyclipper",
    "pypdfium2",
    "python-bidi",
    "shapely",
):
    datas += copy_metadata(distribution)

a = Analysis(
    ["app.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "notebook", "jupyter", "IPython"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="医院票据识别工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    # Paddle's Windows inference runtime cannot reliably open model JSON files
    # when an ancestor directory contains non-ASCII characters.
    name="medical-invoice-excel",
)
