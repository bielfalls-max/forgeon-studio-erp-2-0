from forgeon.ui.main import MainWindow
from forgeon.ui.widgets import Form,Table
from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QMessageBox


def test_all_screens_empty_database(app,erp,monkeypatch):
    errors=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:errors.append(str(args[-1])))
    window=MainWindow(erp); window.show();app.processEvents()
    assert window.stack.count()==10
    for i in range(10):
        window.nav.setCurrentRow(i);app.processEvents()
        assert window.stack.currentIndex()==i
    assert not errors,errors
    assert window.products_table.rowCount()==0
    assert window.orders_table.rowCount()==0
    window.close()


def test_all_screens_populated(app,erp,product,monkeypatch):
    from forgeon.importers.sheets import preview_orders,import_orders
    from test_orders import row,M
    fid=erp.filament('PLA','Laranja',100);erp.set_color(product,fid,100)
    erp.origin('Sonic','10 cm','00001',product)
    orders,_=preview_orders([row()],M);import_orders(erp,orders)
    erp.expense('06/11/2026','Aluguel','Oficina',100)
    erp.purchase('06/11/2026',fid,1000,90,10)
    errors=[];monkeypatch.setattr(QMessageBox,'warning',lambda *a:errors.append(str(a[-1])))
    w=MainWindow(erp);w.show()
    for i in range(10):w.nav.setCurrentRow(i);app.processEvents()
    assert not errors,errors
    assert w.products_table.rowCount()==1
    assert w.orders_table.rowCount()==1
    assert w.origins_table.rowCount()==1
    assert w.expenses_table.rowCount()==1
    w.close()


def test_form_reads_combo_data_and_text(app):
    f=Form('Teste',[('name','Nome','Sonic'),('pid','Produto',[('Sonic',1),('Silver',2)])])
    assert f.values()=={'name':'Sonic','pid':1}
    f.inputs['pid'].setCurrentIndex(1)
    assert f.values()['pid']==2
    f.close()


def test_two_instances_locked(tmp_path):
    path=str(tmp_path/'app.lock')
    one=QLockFile(path);two=QLockFile(path)
    one.setStaleLockTime(0);two.setStaleLockTime(0)
    assert one.tryLock(0)
    assert not two.tryLock(0)
    one.unlock()
    assert two.tryLock(0)
    two.unlock()
