"""Formatos sintéticos, sem dados comerciais ou compradores dos arquivos reais."""
from pathlib import Path
from contextlib import closing
import sqlite3,json
import pytest
from openpyxl import Workbook
from forgeon.importers.automatic import inspect_file,commit_plans,METRICS
from forgeon.importers.sheets import import_orders,preview_orders,detect,ALIASES
from forgeon.reports.finance import report,monthly
from forgeon.reports.shop import comparison,totals
from forgeon.db.store import Store,DEFAULTS


def make_shop(folder,start='2026-09-01',end='2026-10-31',last_value=150):
    from datetime import date
    first=date.fromisoformat(start).strftime('%d/%m/%Y');last=date.fromisoformat(end).strftime('%d/%m/%Y')
    path=folder/f'shopee-shop-stats.{start.replace("-","")}-{end.replace("-","")}.xlsx';w=Workbook();w.remove(w.active)
    for basis,value,count in [('Pedido Feito',last_value,2),('Produto Pago',100,1)]:
        ws=w.create_sheet(basis);headers=['Data']+list(METRICS.values());ws.append(headers)
        def values(when,amount,n):return [when,amount,amount,n,amount/n if n else 0,20,10,'5%',1,50,0,0]
        if start[:7]!=end[:7]:
            ws.append(values(first+'-'+last,value+20,count+1));ws.append([]);ws.append(headers);ws.append(values('01/09/2026',20,1));ws.append(values('01/10/2026',value,count))
        else:
            ws.append(values(first+'-'+last,value,count));ws.append([]);ws.append(headers);ws.append(values('01/10/2026',value,count))
    w.save(path);return path


def make_orders(folder,month='10'):
    path=folder/f'Order.all.2026{month}01_2026{month}31.xlsx';w=Workbook();ws=w.active;ws.title='orders'
    headers=['ID do pedido','Data de criação do pedido','Status do pedido','Nome do Produto','Nome da variação','Número de referência SKU','Quantidade','Preço acordado','Subtotal do produto','Taxas totais','Número de produtos pedidos','Hora do pagamento do pedido','CPF do Comprador']
    ws.append(headers)
    for product,price in [('Figura Exemplo',60),('Acessório Exemplo',40)]:ws.append(['SYNTH-A',f'2026-{month}-05 12:00:00','Concluído',product,'Pequeno','00001',1,price,price,10,2,f'2026-{month}-05 12:03:00','PRIVATE_NEVER_SAVE'])
    ws.append(['SYNTH-C',f'2026-{month}-07','Cancelado','Figura Exemplo','Grande','00002',1,50,50,0,1,'-','PRIVATE_NEVER_SAVE'])
    w.save(path);return path


def test_recognizes_all_sheets_headers_and_periods_without_mapping(tmp_path):
    shop=inspect_file(make_shop(tmp_path));orders=inspect_file(make_orders(tmp_path))
    assert shop['kind']=='shop' and len(shop['metrics'])==6 and len(shop['sheets'])==2
    assert orders['kind']=='orders' and len(orders['orders'])==2 and orders['period']['coverage_kind']=='all'
    assert orders['orders'][0]['financial']['paid_date']=='2026-10-05'
    assert 'PRIVATE_NEVER_SAVE' not in str(orders)


def test_two_files_idempotent_in_both_orders_and_no_sales_created_by_summary(erp,tmp_path):
    shop=inspect_file(make_shop(tmp_path));orders=inspect_file(make_orders(tmp_path));commit_plans(erp,[shop])
    assert not erp.s.rows('SELECT * FROM orders') and not erp.s.rows('SELECT * FROM settlements')
    commit_plans(erp,[orders]);before=report(erp,'01/10/2026','31/10/2026');commit_plans(erp,[orders,shop,orders]);after=report(erp,'01/10/2026','31/10/2026')
    for key in ('gross_cents','fees_cents','operating_cents','cash_cents','orders_count'):assert before[key]==after[key]
    assert after['gross_cents']==10000 and len(erp.s.rows('SELECT * FROM orders'))==2 and len(erp.s.rows('SELECT * FROM order_items'))==3
    assert len(erp.s.rows('SELECT * FROM shop_metrics'))==6
    for table in ('orders','order_items','audit','shop_metrics','order_financials'):assert 'PRIVATE_NEVER_SAVE' not in str(erp.s.rows('SELECT * FROM '+table))


def test_month_comparison_exact_counts_includes_cancelled_for_same_basis(erp,tmp_path):
    commit_plans(erp,[inspect_file(make_shop(tmp_path)),inspect_file(make_orders(tmp_path))]);rows=comparison(erp,'01/10/2026','31/10/2026')
    made=next(r for r in rows if r['basis_key']=='pedido_feito');paid=next(r for r in rows if r['basis_key']=='produto_pago')
    assert (made['revenue_cents'],made['detail_cents'],made['orders_count'],made['detail_orders'])==(15000,15000,2,2)
    assert made['state']=='Valores conferem' and paid['detail_cents']==10000 and paid['detail_orders']==1
    assert not erp.s.rows('SELECT * FROM settlements')


def test_annual_total_is_never_added_to_months_or_paid_basis(erp,tmp_path):
    commit_plans(erp,[inspect_file(make_shop(tmp_path))]);r=report(erp,'01/09/2026','31/10/2026')
    assert len(r['shop_comparison'])==4 and all(x['grain']=='month' for x in r['shop_comparison'])
    assert {x['basis']:x['revenue_cents'] for x in r['shop_totals']}=={'Pedido Feito':17000,'Produto Pago':12000}
    assert r['gross_cents']==0 and r['fees_cents']==0
    assert {x['month'] for x in monthly(erp)}=={'2026-09','2026-10'}


def test_unmatched_months_are_pending_and_monthly_rows_are_not_prorated(erp,tmp_path):
    commit_plans(erp,[inspect_file(make_shop(tmp_path)),inspect_file(make_orders(tmp_path))])
    sept=comparison(erp,'01/09/2026','30/09/2026');assert all(r['detail_cents'] is None and 'Sem pedidos' in r['state'] for r in sept)
    half=report(erp,'01/10/2026','15/10/2026');assert not half['shop_totals'] and all(not r['aligned'] for r in half['shop_comparison'])
    assert not comparison(erp,'01/11/2026','30/11/2026')


def test_batch_failure_rolls_back_orders_and_shop_records(erp,tmp_path):
    plan=inspect_file(make_shop(tmp_path));bad=inspect_file(make_orders(tmp_path));bad['orders'][0]['items'][0]['qty']=0
    with pytest.raises(sqlite3.IntegrityError):commit_plans(erp,[plan,bad])
    assert not erp.s.rows('SELECT * FROM orders') and not erp.s.rows('SELECT * FROM shop_metrics') and not erp.s.rows('SELECT * FROM import_history')
    assert list((erp.s.path.parent/'backups').glob('*.sqlite3'))


def test_partial_summary_cannot_replace_a_full_month(erp,tmp_path):
    full=inspect_file(make_shop(tmp_path,start='2026-10-01'));commit_plans(erp,[full]);partial=inspect_file(make_shop(tmp_path,start='2026-10-01',end='2026-10-15',last_value=60))
    with pytest.raises(ValueError,match='menos dias'):commit_plans(erp,[partial])
    assert report(erp,'01/10/2026','31/10/2026')['shop_totals'][0]['revenue_cents']==15000


def test_new_full_month_replaces_partial_once(erp,tmp_path):
    partial=inspect_file(make_shop(tmp_path,start='2026-10-01',end='2026-10-15',last_value=60));commit_plans(erp,[partial]);commit_plans(erp,[inspect_file(make_shop(tmp_path,start='2026-10-01'))])
    assert report(erp,'01/10/2026','31/10/2026')['shop_totals'][0]['revenue_cents']==15000


def test_formula_and_unknown_formats_rejected_before_commit(tmp_path):
    path=tmp_path/'unknown.xlsx';w=Workbook();w.active.append(['Data','Anotação']);w.active.append(['01/10/2026','Texto']);w.save(path)
    with pytest.raises(ValueError,match='Formato não reconhecido'):inspect_file(path)
    w.active['B2']='=1+1';w.save(path)
    with pytest.raises(ValueError,match='Fórmula'):inspect_file(path)


def test_frozen_costs_and_usage_survive_automatic_reimport(erp,tmp_path):
    pid=erp.save_product({'name':'Pequeno','weight':'10','hours':'1'});plan=inspect_file(make_orders(tmp_path));commit_plans(erp,[plan]);erp.resolve_known_products();old=erp.s.rows('SELECT item_key,cost_cents,cost_detail FROM order_items ORDER BY item_key');usage=erp.s.rows('SELECT detail,recorded FROM item_usage ORDER BY detail')
    erp.save_product({'name':'Pequeno','weight':'999','hours':'9'},pid);commit_plans(erp,[plan])
    assert erp.s.rows('SELECT item_key,cost_cents,cost_detail FROM order_items ORDER BY item_key')==old
    assert erp.s.rows('SELECT detail,recorded FROM item_usage ORDER BY detail')==usage


def test_manual_reimport_without_paid_column_preserves_known_payment(erp,tmp_path):
    plan=inspect_file(make_orders(tmp_path));commit_plans(erp,[plan]);plan['orders'][0]['financial'].update(paid_date=None,paid_date_available=False);import_orders(erp,plan['orders'],plan['period'])
    assert json.loads(erp.s.one("SELECT detail FROM order_financials WHERE order_id='SYNTH-A'")['detail'])['paid_date']=='2026-10-05'


def test_schema_three_migration_and_restore_preserve_source(erp,tmp_path):
    path=tmp_path/'v3.sqlite3'
    with closing(sqlite3.connect(path)) as db:
        db.executescript(Path('forgeon/db/schema.sql').read_text());db.executemany('INSERT INTO settings VALUES(?,?)',DEFAULTS.items());db.commit();Store.migrate(db,3);db.execute("INSERT INTO products(name) VALUES('Produto legado sintético')");db.commit()
    original=path.read_bytes();erp.s.restore(path);assert path.read_bytes()==original
    assert erp.s.db.execute('PRAGMA user_version').fetchone()[0]==6 and erp.s.one('SELECT name FROM products')['name']=='Produto legado sintético'


def test_ui_automatic_import_does_not_ask_sheet_or_mapping(app,erp,tmp_path,monkeypatch):
    from forgeon.ui.main import MainWindow
    from PySide6.QtWidgets import QFileDialog,QDialog,QMessageBox
    paths=[str(make_shop(tmp_path)),str(make_orders(tmp_path))];errors=[]
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *a,**k:(paths,'XLSX'));monkeypatch.setattr(QDialog,'exec',lambda self:QDialog.DialogCode.Accepted);monkeypatch.setattr(QMessageBox,'warning',lambda *a:errors.append(a[-1]))
    w=MainWindow(erp);w.info=lambda *a:None;w.form=lambda *a,**k:pytest.fail('Arquivo reconhecido pediu mapeamento manual')
    w.import_automatic_files();assert not errors,errors
    assert len(w.monthly_table.records)==2 and w.report_tabs.currentIndex()==0 and w.report_start.text()=='2026-09-01'
    w.close()


def test_ui_cancel_does_not_modify_database(app,erp,tmp_path,monkeypatch):
    from forgeon.ui.main import MainWindow
    from PySide6.QtWidgets import QDialog
    w=MainWindow(erp);monkeypatch.setattr(QDialog,'exec',lambda self:QDialog.DialogCode.Rejected)
    w.review_automatic([inspect_file(make_shop(tmp_path))]);assert not erp.s.rows('SELECT * FROM shop_metrics') and not erp.s.rows('SELECT * FROM import_history');w.close()


def test_complete_made_comparison_does_not_require_duplicate_announcement_stats(erp,tmp_path):
    erp.save_product({'name':'Pequeno','weight':'10','hours':'1'})
    commit_plans(erp,[inspect_file(make_shop(tmp_path)),inspect_file(make_orders(tmp_path))])
    assert report(erp,'01/10/2026','31/10/2026')['partial'] is False
    assert report(erp,'01/09/2026','31/10/2026')['partial'] is True


def test_conflicting_same_order_in_selected_files_is_refused(erp,tmp_path):
    from copy import deepcopy
    original=inspect_file(make_orders(tmp_path));changed=deepcopy(original);changed['source_hash']='another';changed['orders'][0]['fees_cents']+=100
    with pytest.raises(ValueError,match='conflitantes'):commit_plans(erp,[original,changed])
    assert not erp.s.rows('SELECT * FROM orders')


def test_comparison_is_integrated_without_extra_report_tab(app,erp,tmp_path):
    from forgeon.ui.main import MainWindow
    w=MainWindow(erp);assert w.nav.groups.count()==7 and w.report_tabs.count()==9
    assert not hasattr(w,'shop_table') and w.report_tabs.widget(0) is w.report_browser
    w.close()


def test_after_full_production_is_pending_until_recipe_exists(erp,tmp_path):
    commit_plans(erp,[inspect_file(make_orders(tmp_path))]);r=report(erp,'01/10/2026','31/10/2026')
    assert r['after_production_cents'] is None and r['production_pending']

    for p in erp.s.rows("SELECT * FROM products WHERE name='Pequeno'"):erp.save_product({'name':p['name'],'model':p['model'],'weight':'10','hours':'1','packaging':'2','other':'3'},p['id'])
    erp.freeze_missing_costs();erp.resolve_known_products()
    r=report(erp,'01/10/2026','31/10/2026')
    assert not r['production_pending'] and r['after_production_cents']==r['gross_cents']-r['fees_cents']-r['refunds_cents']-r['production_cents']-r['losses_cents']
    assert r['production_cents']==1410 and r['after_production_cents']==7590 and r['usage_total_grams']=='20'


def test_annual_summary_without_annual_orders_does_not_claim_full_net_profit(erp,tmp_path):
    erp.save_product({'name':'Pequeno','weight':'10','hours':'1'})
    commit_plans(erp,[inspect_file(make_shop(tmp_path)),inspect_file(make_orders(tmp_path))])
    annual=report(erp,'01/09/2026','31/10/2026');assert annual['after_production_cents'] is None and annual['production_pending']
    october=report(erp,'01/10/2026','31/10/2026');assert october['after_production_cents'] is not None
    assert october['financial_rows'][0]['after_production_cents']==october['financial_rows'][0]['net_cents']-october['financial_rows'][0]['production_cents']


def test_unknown_refund_does_not_claim_complete_net_result(erp,tmp_path):
    erp.save_product({'name':'Pequeno','weight':'10','hours':'1'});plan=inspect_file(make_orders(tmp_path));plan['orders'][0]['financial']['returned_qty']=1;commit_plans(erp,[plan])
    r=report(erp,'01/10/2026','31/10/2026');assert r['after_production_cents'] is None and r['result_pending']
    with erp.s.transaction():erp.s.db.execute("UPDATE orders SET refund_cents=2000 WHERE id='SYNTH-A'")
    r=report(erp,'01/10/2026','31/10/2026');assert r['after_production_cents']==6590


def test_export_report_with_pending_costs_writes_xlsx(app,erp,tmp_path,monkeypatch):
    from forgeon.ui.main import MainWindow
    from PySide6.QtWidgets import QFileDialog,QMessageBox
    from openpyxl import load_workbook
    target=tmp_path/'exportacao.xlsx';errors=[]
    commit_plans(erp,[inspect_file(make_orders(tmp_path))])
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),'XLSX'));monkeypatch.setattr(QMessageBox,'warning',lambda *a:errors.append(a[-1]))
    w=MainWindow(erp);w.info=lambda *a:None;w.report_start.setText('2026-10-01');w.report_end.setText('2026-10-31');w.nav.setCurrentRow(8);w.export_report()
    assert not errors,errors
    wb=load_workbook(target,read_only=True,data_only=False);summary=list(wb['Resumo'].values);wb.close()
    assert any('Após taxas e produção completa' in str(row) and 'Pendente' in str(row) for row in summary)
    w.close()
