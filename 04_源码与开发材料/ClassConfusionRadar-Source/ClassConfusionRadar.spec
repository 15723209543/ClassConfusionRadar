# 本文件的作用是：配置当前工具、服务或构建流程所需的参数。
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH)
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

hiddenimports = (
    collect_submodules("app")
    + [
        "scripts.demo_seed",
        "scripts.public_demo_seed",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "sqlalchemy.dialects.sqlite",
    ]
)

datas = [
    (str(project_root / "frontend" / "dist"), "frontend_dist"),
    (str(project_root / "docs" / "samples"), "docs/samples"),
    (str(project_root / "demo_data"), "demo_data"),
]

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[str(project_root), str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ClassConfusionRadar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=str(project_root / "assets" / "app_icon.ico"),
)
