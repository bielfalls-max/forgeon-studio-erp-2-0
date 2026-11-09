# Executar na raiz: python -m PyInstaller --clean --noconfirm packaging/ForgeonStudioERP.spec
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata
import sys
root = Path(SPECPATH).parent

metadata = []
for package in ('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','openpyxl','et_xmlfile','defusedxml'):
    metadata += copy_metadata(package)
licenses = [(str(root / 'packaging' / 'licenses'), 'licenses')]
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    licenses.append((str(python_license), 'licenses/Python'))

a = Analysis(
    [str(root / 'forgeon_launcher.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'forgeon' / 'db' / 'schema.sql'), 'forgeon/db'),(str(root / 'forgeon' / 'db' / 'migration_v2.sql'), 'forgeon/db'),(str(root / 'forgeon' / 'db' / 'migration_v3.sql'), 'forgeon/db'),(str(root / 'forgeon' / 'assets'), 'forgeon/assets')] + metadata + licenses,
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
    icon=str(root / 'forgeon' / 'assets' / 'forgeon.ico'),
    version=str(root / 'packaging' / 'version-info.txt'),
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ForgeonStudioERP')
