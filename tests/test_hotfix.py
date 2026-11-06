from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog,QMessageBox
from forgeon.ui.widgets import Table
from forgeon.ui.main import MainWindow
from forgeon.ui.visual import ASSETS
from forgeon.reports.finance import report


def test_sorted_table_keeps_correct_record_and_column_selection(app):
    table=Table();table.fill([{'id':1,'total_cents':900},{'id':2,'total_cents':100},{'id':3,'total_cents':2000}],[('id','ID'),('total_cents','Custo')])
    table.sortItems(1,Qt.SortOrder.AscendingOrder);table.selectRow(0)
    assert table.selected()['id']==2
    table.sortItems(1,Qt.SortOrder.DescendingOrder);table.selectRow(0)
    assert table.selected()['id']==3
    table.setColumnHidden(0,True)
    assert table.visible_records()[0]=={'total_cents':2000}
    table.fill([{'id':4,'total_cents':300}],[('id','ID'),('total_cents','Custo')])
    assert table.isColumnHidden(0)
    table.show_all_columns();assert not table.isColumnHidden(0)
    table.fill([{'sku':'00001','name':'=SUM(1)\n@teste'}],[('sku','SKU'),('name','Nome')]);table.selectRow(0);table.copy_row()
    from PySide6.QtWidgets import QApplication
    assert QApplication.clipboard().text()=="'00001\t'=SUM(1) @teste"


def test_dashboard_and_reports_never_fetch_updates_on_open(app,erp,monkeypatch):
    from urllib.request import OpenerDirector
    def forbidden(*a,**k):raise AssertionError('Consulta de rede não autorizada ao abrir o ERP')
    monkeypatch.setattr(OpenerDirector,'open',forbidden)
    w=MainWindow(erp)
    for i in range(11):w.nav.setCurrentRow(i);app.processEvents()
    assert '2.0.1' in w.updates_page.notes.toPlainText()
    assert not w.updates_page.download_button.isEnabled()
    assert w.updates_page.task is None
    w.focus_toggle.setChecked(True)
    assert erp.s.settings()['appearance_focus']=='1'
    assert w.backdrop.focus_mode
    w.close()


def test_report_pdf_is_created_with_current_period(app,erp,tmp_path,monkeypatch):
    path=tmp_path/'relatorio.pdf';errors=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'PDF'))
    monkeypatch.setattr(QMessageBox,'information',lambda *a,**k:None)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:errors.append(a[-1]))
    w=MainWindow(erp);w.show();w.nav.setCurrentRow(8);app.processEvents();w.export_report_pdf()
    assert not errors,errors
    assert path.read_bytes().startswith(b'%PDF-') and path.stat().st_size>1000
    w.close()


def test_daily_series_excludes_cancelled_and_matches_report(erp,product):
    from test_orders import row,load
    erp.origin('Sonic','10 cm','00001',product)
    load(erp,[row('A'),row('B',status='Cancelado')])
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['sales_by_day']==[{'date':'2026-11-06','gross_cents':5000}]
    assert sum(d['gross_cents'] for d in r['sales_by_day'])==r['gross_cents']


def test_hotfix_versions_and_resources_agree():
    from forgeon.version import VERSION
    root=Path(__file__).resolve().parent.parent
    assert VERSION=='2.0.1'
    assert f'#define AppVersion "{VERSION}"' in (root/'packaging/ForgeonStudioERP.iss').read_text()
    assert (ASSETS/'forgeon.ico').read_bytes()[:4]==b'\x00\x00\x01\x00'
    assert (ASSETS/'swiss-alps.png').is_file()


def test_chart_exports_real_png(app,tmp_path,monkeypatch):
    from forgeon.ui.charts import ChartCard
    from PySide6.QtGui import QImage
    target=tmp_path/'grafico.png'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),'PNG'))
    chart=ChartCard('Vendas do período','Dados de teste');chart.resize(640,330)
    chart.line([{'date':'2026-11-01','gross_cents':10000},{'date':'2026-11-06','gross_cents':25000}]);chart.show();app.processEvents();chart.save_png()
    assert not QImage(str(target)).isNull()
    assert target.stat().st_size>1000
    chart.close()
