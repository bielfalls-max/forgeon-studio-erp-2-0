"""Dados sintéticos: nenhum arquivo ou dado comercial enviado pelo usuário acompanha o repositório."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from decimal import Decimal
from contextlib import closing
from datetime import date
import sqlite3,json
import pytest
from openpyxl import Workbook
from forgeon.importers.slicing import read_slicing,combine_plates
from forgeon.importers.sheets import read_xlsx,detect,LABELS,preview_orders,import_orders,import_period
from forgeon.business.production import save_sliced_product
from forgeon.business.numbers import day
from forgeon.db.store import Store,DEFAULTS
from forgeon.reports.finance import report
from forgeon.ui.main import MainWindow
from forgeon.ui.production import SlicingProductDialog
from PySide6.QtWidgets import QMessageBox,QFileDialog,QDialog


def sliced(tmp_path):
    file=tmp_path/'FiguraExemplo.gcode.3mf'
    plates=''.join(f'<plate><metadata key="index" value="{i}"/><metadata key="prediction" value="3600"/><object name="parte"/><filament id="{i}" type="PLA" color="{color}" used_g="{i}"/></plate>' for i,color in enumerate(['#FFFFFF','#000000','#2850E0','#C12E1F','#A6A9AA','#F4EE2A'],1))
    with ZipFile(file,'w') as z:z.writestr('Metadata/slice_info.config','<config>'+plates+'</config>')
    return file


def make_sheet(tmp_path):
    file=tmp_path/'Order.all.20260101_20260106.xlsx';wb=Workbook();ws=wb.active
    ws.append(['ID do pedido','Data de criação do pedido','Status do pedido','Nome do Produto','Nome da variação','Número de referência SKU','Preço acordado','Quantidade','Subtotal do produto','Valor Total','Total global','Taxa de comissão bruta','Taxa de comissão líquida','Taxa de serviço bruta','Taxa de serviço líquida','Taxa de transação','Taxa de envio pagas pelo comprador','Desconto do vendedor','Desconto do vendedor','CPF do Comprador'])
    ws.append(['EXEMPLO-1','2026-01-03 15:30','A Enviar','Anúncio misto','Figura Exemplo','00001','10','2','20','35','34','8','4','6','3','1','5','5','5','PII_NAO_GRAVAR'])
    ws.append(['EXEMPLO-1','2026-01-03 15:30','A Enviar','Anúncio misto','Outra Figura','00001','10','1','10','35','34','8','4','6','3','1','5','5','5','PII_NAO_GRAVAR'])
    wb.save(file)
    # Reproduce the broken worksheet dimension from a real-world exporter without its contents.
    with ZipFile(file) as z:entries={n:z.read(n) for n in z.namelist()}
    import re
    entries['xl/worksheets/sheet1.xml']=re.sub(br'<dimension ref="[^"]+"',b'<dimension ref="A1:A1"',entries['xl/worksheets/sheet1.xml'])
    with ZipFile(file,'w',ZIP_DEFLATED) as z:
        for name,data in entries.items():z.writestr(name,data)
    return file


def test_multiplate_recipe_creates_product_colors_and_pricing(erp,tmp_path):
    file=sliced(tmp_path);plates=read_slicing(file);recipe=combine_plates(plates,list(range(6)),1,file.name)
    assert recipe['name']=='Figura Exemplo'
    assert Decimal(recipe['hours'])==6
    assert sum(Decimal(c['grams']) for c in recipe['colors'])==21
    pid,_,_=save_sliced_product(erp,recipe['name'],'',recipe,[{**c,'kg':'100'} for c in recipe['colors']])
    assert erp.cost(pid)['grams']=='21'
    assert len(erp.colors(pid))==6 and erp.cost(pid)['suggested_cents']>0
    assert erp.s.one('SELECT * FROM product_slices WHERE product_id=?',(pid,))
    half=combine_plates(plates,list(range(6)),2,file.name)
    assert Decimal(half['hours'])==3 and sum(Decimal(c['grams']) for c in half['colors'])==Decimal('10.5')


def test_broken_dimensions_duplicate_headers_and_liquid_fees(erp,tmp_path):
    file=make_sheet(tmp_path);headers,rows,_=read_xlsx(file)
    assert len(rows)==2 and 'Desconto do vendedor [2]' in headers
    mapping=detect(headers,list(LABELS));assert mapping['commission']=='Taxa de comissão líquida'
    orders,_=preview_orders(rows,mapping,file.name);period=import_period(orders,file.name)
    assert len(orders)==1 and orders[0]['gross_cents']==3000 and orders[0]['fees_cents']==800
    assert orders[0]['financial']['buyer_shipping_cents']==500
    assert period['active_month']=='2026-01' and period['partial']
    import_orders(erp,orders,period);import_orders(erp,orders,period)
    assert len(erp.s.rows('SELECT * FROM orders'))==1 and len(erp.s.rows('SELECT * FROM order_items'))==2
    assert erp.s.settings()['active_month']=='2026-01'
    assert 'PII_NAO_GRAVAR' not in str(erp.s.rows('SELECT * FROM order_financials'))+str(erp.s.rows('SELECT * FROM audit'))


def test_exact_variation_joins_recipe_without_hiding_sku_conflict(erp,tmp_path):
    file=sliced(tmp_path);recipe=combine_plates(read_slicing(file),list(range(6)),1,file.name)
    pid,_,_=save_sliced_product(erp,recipe['name'],'',recipe,[{**c,'kg':'100'} for c in recipe['colors']])
    f=make_sheet(tmp_path);h,rows,_=read_xlsx(f);orders,_=preview_orders(rows,detect(h,list(LABELS)),f.name);import_orders(erp,orders)
    r=report(erp,'01/01/2026','31/01/2026')
    assert r['gross_cents']==3000 and r['fees_cents']==800
    assert r['usage_total_grams']=='42' and r['usage_total_hours']=='12'
    assert any(i['variation']=='Outra Figura' and i['unit_grams'] is None for i in r['usage_items'])
    assert r['unknown_usage_units']==1 and r['planned_grams']=='42' and r['sent_grams']=='0'
    assert erp.match_product('Anúncio Figura Exemplo','Outra Figura') is None
    assert erp.match_product('Anúncio Figura Exemplo','Figura Exemplo Preto') is None
    other=erp.save_product({'name':'Outra Figura','weight':'5','hours':'1'})
    erp.resolve_known_products()
    assert erp.conflicts()=={'00001'}
    assert erp.s.one("SELECT original_sku FROM order_items WHERE product_id=?",(pid,))['original_sku']=='00001'


def test_orders_first_then_recipe_fills_pending_with_current_snapshot(erp,tmp_path):
    f=make_sheet(tmp_path);h,rows,_=read_xlsx(f);orders,_=preview_orders(rows,detect(h,list(LABELS)));import_orders(erp,orders)
    file=sliced(tmp_path);recipe=combine_plates(read_slicing(file),list(range(6)),1,file.name)
    pid,linked,frozen=save_sliced_product(erp,recipe['name'],'',recipe,[{**c,'kg':'100'} for c in recipe['colors']])
    assert linked==1 and frozen==1
    item=erp.s.one('SELECT * FROM order_items WHERE product_id=?',(pid,));old=item['cost_cents']
    assert item['cost_at'] and erp.s.one('SELECT * FROM item_usage WHERE item_id=?',(item['id'],))
    erp.set_color(pid,erp.colors(pid)[0]['filament_id'],'999')
    import_orders(erp,orders)
    current=erp.s.one('SELECT * FROM order_items WHERE product_id=?',(pid,))
    assert current['cost_cents']==old
    assert report(erp,'01/01/2026','31/01/2026')['usage_total_grams']=='42'


def legacy_database(path):
    with closing(sqlite3.connect(path)) as db,db:
        db.executescript(Path(__file__).resolve().parents[1].joinpath('forgeon/db/schema.sql').read_text())
        db.executemany('INSERT INTO settings VALUES(?,?)',DEFAULTS.items())
        db.execute("INSERT INTO products(name,weight,hours) VALUES('Produto preservado','10','1')")
        db.execute("INSERT INTO orders(id,date,status,gross_cents,fees_cents,source) VALUES('LEGACY-EXEMPLO','2026-01-01','Entregue',1000,100,'Shopee')")
        detail=json.dumps({'grams':'10','hours':'1','colors':[],'missing':[]})
        db.execute("INSERT INTO order_items(order_id,item_key,product_id,original_sku,title,variation,qty,unit_cents,cost_cents,cost_detail,cost_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",('LEGACY-EXEMPLO','chave',1,'00003','Produto preservado','',2,500,200,detail,'2026-01-01T12:00:00'))


def test_schema_upgrade_keeps_legacy_data_and_backup(tmp_path):
    path=tmp_path/'old.sqlite3';legacy_database(path);s=Store(path)
    assert s.db.execute('PRAGMA user_version').fetchone()[0]==3
    assert s.one('SELECT name FROM products')['name']=='Produto preservado'
    assert s.one('SELECT cost_cents FROM order_items')['cost_cents']==200
    from forgeon.business.service import ERP
    legacy_report=report(ERP(s),'01/01/2026','31/01/2026')
    assert legacy_report['production_cents']==400 and legacy_report['usage_total_grams']=='20'
    backup=next((tmp_path/'backups').glob('*.sqlite3'))
    with closing(sqlite3.connect(backup)) as old:assert old.execute('PRAGMA user_version').fetchone()[0]==1
    s.close()


def test_restore_version_one_backup_promotes_staging_only(erp,tmp_path):
    source=tmp_path/'v1.sqlite3';legacy_database(source);erp.s.restore(source)
    assert erp.s.db.execute('PRAGMA user_version').fetchone()[0]==3
    assert erp.s.one('SELECT name FROM products')['name']=='Produto preservado'
    with closing(sqlite3.connect(source)) as original:assert original.execute('PRAGMA user_version').fetchone()[0]==1


def test_wizard_and_empty_pricing_have_real_actions(app,erp,tmp_path,monkeypatch):
    file=sliced(tmp_path);errors=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:errors.append(str(a[-1])))
    dialog=SlicingProductDialog(erp,file);dialog.confirm.setChecked(True);dialog.save()
    assert not errors and dialog.result_data and dialog.result()==QDialog.DialogCode.Accepted
    w=MainWindow(erp);w.nav.setCurrentRow(1);w.update_products();assert w.products_table.rowCount()==1
    assert not w.product_empty.isVisible()
    w.nav.setCurrentRow(3);assert w.pricing_product.currentData() is not None
    assert w.pricing_components.rowCount()>0 and w.pricing_catalog.rowCount()==1
    assert not errors,errors
    w.close()


def test_import_opens_identified_period_and_report_columns(app,erp,tmp_path,monkeypatch):
    file=make_sheet(tmp_path);errors=[]
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(file),'XLSX'))
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:errors.append(str(a[-1])))
    import forgeon.ui.main as ui
    monkeypatch.setattr(ui,'preview',lambda *a,**k:True)
    w=MainWindow(erp);w.mapping=lambda headers,keys:detect(headers,keys);w.info=lambda *a:None
    w.import_order_file()
    assert not errors,errors
    assert w.dashboard_month.text()=='2026-01'
    assert w.report_start.text()=='2026-01-01' and w.report_end.text()=='2026-01-06'
    assert w.financial_orders_table.rowCount()==1 and w.usage_items_table.rowCount()==2
    assert w.report_tabs.currentIndex()==7
    w.close()


def test_incomplete_order_is_refused_before_replacing_items(tmp_path):
    file=make_sheet(tmp_path);headers,rows,_=read_xlsx(file)
    headers.append('Número de produtos pedidos')
    rows[0]['Número de produtos pedidos']='3'
    with pytest.raises(ValueError,match='todos os itens'):preview_orders(rows[:1],detect(headers,list(LABELS)))
