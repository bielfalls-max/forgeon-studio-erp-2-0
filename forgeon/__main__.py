import sys
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QLockFile,QLocale
from .db.store import Store,data_directory
from .business.service import ERP
from .ui.main import MainWindow
from .ui.visual import app_icon
from .version import VERSION


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('FORGEON STUDIO ERP 2.0');app.setApplicationVersion(VERSION);app.setWindowIcon(app_icon())
    app.setOrganizationName('ForgeonStudioERP2')
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese,QLocale.Country.Brazil))
    folder=data_directory(); folder.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(folder/'forgeon2.lock'))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.warning(None,'FORGEON','Outro processo está usando este banco. Feche a outra instância e tente novamente.'); return 1
    store=None
    try:
        store=Store(folder/'forgeon2.sqlite3')
        window=MainWindow(ERP(store)); window.show()
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None,'FORGEON • Não foi possível abrir',str(exc)); return 1
    finally:
        if store:store.close()
        lock.unlock()


if __name__=='__main__':
    sys.exit(main())
