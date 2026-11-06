"""Verificação explícita do pacote; usa apenas um banco temporário descartável."""
import json
import platform
import tempfile
import traceback
from pathlib import Path


def check(destination):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .db.store import Store
    from .business.service import ERP
    from .ui.main import MainWindow

    app = QApplication.instance() or QApplication([])
    errors = []
    previous_warning, previous_critical = QMessageBox.warning, QMessageBox.critical
    QMessageBox.warning = lambda *args, **kwargs: errors.append(str(args[-1]))
    QMessageBox.critical = lambda *args, **kwargs: errors.append(str(args[-1]))
    from .version import VERSION
    result = {'version':VERSION, 'ok': False, 'platform': platform.platform(), 'screens': 0, 'errors': errors}
    try:
        with tempfile.TemporaryDirectory(prefix='forgeon-check-') as folder:
            store = Store(Path(folder) / 'check.sqlite3')
            window = None
            try:
                erp = ERP(store)
                # Exercise packaged SQL resource, application imports, Qt plugins, persistence and backup.
                pid = erp.save_product({'name': 'Verificação temporária', 'weight': '100', 'hours': '1'})
                assert erp.cost(pid)['total_cents'] > 0
                saved = store.backup()
                store.restore(saved)
                with store.transaction():
                    store.db.execute('DELETE FROM products WHERE id=?', (pid,))
                window = MainWindow(erp)
                assert not window.windowIcon().isNull(), 'Ícone não incluído no pacote'
                assert not window.backdrop.image.isNull(), 'Paisagem não incluída no pacote'
                assert window.updates_page.notes.toPlainText(), 'Notas não incluídas no pacote'
                window.show()
                app.processEvents()
                for index in range(window.stack.count()):
                    window.nav.setCurrentRow(index)
                    app.processEvents()
                    assert window.stack.currentIndex() == index
                    result['screens'] += 1
                assert result['screens'] == 11
                store.validate(store.db)
                assert not errors, errors
                result['ok'] = True
            finally:
                if window is not None:
                    window.close()
                store.close()
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        QMessageBox.warning, QMessageBox.critical = previous_warning, previous_critical
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1
