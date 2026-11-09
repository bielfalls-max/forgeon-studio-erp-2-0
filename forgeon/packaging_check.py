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
                    store.db.execute('DELETE FROM recipe_revisions WHERE product_id=?',(pid,))
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
                assert result['screens'] == 16
                # Exercise HF03–HF05 inside the packaged binary as well as the empty UI.
                from .business import workshop,management
                pid=erp.save_product({'name':'Produto sintético do pacote','weight':'10','hours':'1'})
                fid=erp.filament('PLA','Preto sintético','100');erp.set_color(pid,fid,'10')
                rid=workshop.register_roll(erp,fid,'Rolo sintético','100')
                jid=workshop.create_job(erp,pid,2);workshop.change_state(erp,jid,'Pronto')
                assert workshop.roll_balance(store,rid)==80
                event=workshop.record_loss(erp,fid,'5','0','Verificação sintética')
                workshop.void_loss(erp,event,'Estorno sintético')
                assert workshop.roll_balance(store,rid)==80
                assert management.simulator(erp,pid)['scenario']['total_cents']>0
                management.save_receipt(erp,'01/11/2026','10','REPASSE-SINTETICO')
                assert len(management.receipt_rows(erp))==1
                for index in range(window.stack.count()):
                    window.nav.setCurrentRow(index);app.processEvents()
                    assert window.stack.widget(index).help_button.text()=='ⓘ Como usar'
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
