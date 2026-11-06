# Executar na raiz: python -m PyInstaller --clean --noconfirm packaging/ForgeonStudioERP.spec
from pathlib import Path
root = Path(SPECPATH).parent

a = Analysis(
    [str(root / 'forgeon_launcher.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'forgeon' / 'db' / 'schema.sql'), 'forgeon/db')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='ForgeonStudioERP', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ForgeonStudioERP')
