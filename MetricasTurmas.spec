# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller. Uso:  pyinstaller --noconfirm MetricasTurmas.spec
# Resultado: dist/MetricasDasTurmas/ (pasta com MetricasDasTurmas.exe dentro).
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(SPECPATH)

datas = [(os.path.join(ROOT, "assets"), "assets")]          # modelo, exemplos e ícone
datas += collect_data_files("plotly")                         # plotly.min.js (gráficos 100% offline)

hiddenimports = (
    collect_submodules("plotly.graph_objs")
    + ["openpyxl", "xlrd", "odf", "pandas._libs.tslibs.timedeltas"]
)

icon = os.path.join(ROOT, "assets", "icon.ico")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "tkinter.test", "matplotlib", "scipy", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="MetricasDasTurmas",
    console=False,                                            # sem janela preta
    icon=icon if os.path.exists(icon) else None,
    upx=False,                                                # UPX aumenta falsos alarmes de antivírus
)
coll = COLLECT(exe, a.binaries, a.datas, name="MetricasDasTurmas", upx=False)
