"""Cenários sintéticos para organização, produção/estoque e conciliação."""
from decimal import Decimal
import json
import sqlite3
from contextlib import closing
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox,QTabWidget
from forgeon.business import workshop as shop,management as mgmt,organization as org
from forgeon.business.revisions import revisions
from forgeon.ui.main import MainWindow
from forgeon.ui.widgets import Page,Table
from forgeon.ui.help import help_text
from forgeon.reports.finance import report
from forgeon.db.store import Store
from test_orders import load,row


@pytest.fixture
def recipe(erp,product):
    fid=erp.filament('PLA','Preto','100');erp.set_color(product,fid,'100')
    return product,fid


def test_reservation_and_ready_are_distinct_and_idempotent(erp,recipe):
    pid,fid=recipe;rid=shop.register_roll(erp,fid,'Rolo sintético','500')
    jid=shop.create_job(erp,pid,2)
    balance=shop.stock(erp)[0]
    assert balance['grams']=='500' and balance['reserved_grams']=='200' and balance['available_grams']=='300'
    shop.change_state(erp,jid,'Em impressão');assert shop.roll_balance(erp.s,rid)==500
    assert shop.change_state(erp,jid,'Pronto')
    assert not shop.change_state(erp,jid,'Pronto')
    assert shop.roll_balance(erp.s,rid)==300
    assert shop.stock(erp)[0]['reserved_grams']=='0'
    assert len(erp.s.rows("SELECT * FROM production_events WHERE kind='consumo'"))==1
    with pytest.raises(ValueError,match='voltar'):shop.change_state(erp,jid,'A produzir')
    shop.change_state(erp,jid,'Cancelado');assert shop.roll_balance(erp.s,rid)==300


def test_shortage_rolls_back_all_materials_and_event(erp,recipe):
    pid,fid=recipe;other=erp.filament('PLA','Branco','90');erp.set_color(pid,other,'20')
    rid=shop.register_roll(erp,fid,'Preto','500');jid=shop.create_job(erp,pid,1)
    with pytest.raises(ValueError,match='insuficiente'):shop.change_state(erp,jid,'Pronto')
    assert shop.roll_balance(erp.s,rid)==500
    assert erp.s.one('SELECT state FROM production_jobs')['state']=='A produzir'
    assert not erp.s.rows('SELECT * FROM production_events')
    shop.register_roll(erp,other,'Branco','20');shop.change_state(erp,jid,'Pronto')
    assert shop.roll_balance(erp.s,rid)==400


def test_purchase_creates_one_roll_and_finance_is_not_counted_twice(erp,recipe):
    pid,fid=recipe;erp.purchase('06/11/2026',fid,'1000','100','10')
    assert len(shop.rolls(erp))==1 and shop.rolls(erp)[0]['grams']=='1000'
    baseline=report(erp,'01/11/2026','30/11/2026')
    assert baseline['purchases_cents']==11000 and baseline['operating_cents']==0 and baseline['cash_cents']==-11000
    jid=shop.create_job(erp,pid,1);shop.change_state(erp,jid,'Pronto')
    assert shop.rolls(erp)[0]['grams']=='900'
    assert report(erp,'01/11/2026','30/11/2026')['operating_cents']==0  # avulso não cria venda


def test_loss_reversal_preserves_history_and_cash(erp,recipe):
    pid,fid=recipe;rid=shop.register_roll(erp,fid,'Rolo','500')
    jid=shop.create_job(erp,pid,1)
    base=report(erp,'01/11/2026','30/11/2026')
    eid=shop.record_loss(erp,fid,'50','1','Falha sintética','06/11/2026',jid)
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['losses_cents']==615 and r['operating_cents']==base['operating_cents']-615
    assert r['cash_cents']==base['cash_cents'] and shop.roll_balance(erp.s,rid)==450
    assert shop.void_loss(erp,eid,'Correção') and not shop.void_loss(erp,eid,'Correção')
    assert shop.roll_balance(erp.s,rid)==500
    assert report(erp,'01/11/2026','30/11/2026')['losses_cents']==0
    eid=shop.record_loss(erp,fid,'10','0','Já baixado','06/11/2026',already_deducted=True)
    assert shop.roll_balance(erp.s,rid)==500
    shop.void_loss(erp,eid,'Correção');assert shop.roll_balance(erp.s,rid)==500


def test_failed_loss_and_invalid_adjustments_are_atomic(erp,recipe):
    pid,fid=recipe;rid=shop.register_roll(erp,fid,'Rolo','10')
    with pytest.raises(ValueError):shop.record_loss(erp,fid,'11','0','Falha')
    assert not erp.s.rows('SELECT * FROM production_events')
    with pytest.raises(ValueError):shop.adjust_roll(erp,rid,'-1','Pesagem')
    with pytest.raises(ValueError):shop.adjust_roll(erp,rid,'5','')
    shop.adjust_roll(erp,rid,'7.5','Pesagem confirmada');assert shop.roll_balance(erp.s,rid)==Decimal('7.5')


def test_sync_and_reimport_changed_quantity_requires_review(erp,recipe):
    pid,fid=recipe;erp.origin('Sonic','10 cm','00001',pid)
    load(erp,[row(status='A Enviar')]);assert shop.sync_jobs(erp)==1 and shop.sync_jobs(erp)==0
    rid=shop.register_roll(erp,fid,'Rolo','1000');jid=shop.jobs(erp)[0]['id']
    load(erp,[row(status='A Enviar',qty='2')]);assert 'alterad' in shop.jobs(erp)[0]['pending']
    with pytest.raises(ValueError,match='alterado'):shop.change_state(erp,jid,'Pronto')
    shop.refresh_job(erp,jid);assert shop.jobs(erp)[0]['units']==2
    shop.change_state(erp,jid,'Pronto');assert shop.roll_balance(erp.s,rid)==800
    load(erp,[row(status='Cancelado',qty='2')]);assert any(p['type']=='Pedido cancelado na produção' for p in org.pending(erp))


def test_recipe_revision_does_not_rewrite_job_or_order(erp,recipe):
    pid,fid=recipe;erp.origin('Sonic','10 cm','00001',pid);load(erp,[row()])
    jid=shop.create_job(erp,pid,1);old=erp.s.one('SELECT cost_cents FROM order_items')['cost_cents']
    erp.set_color(pid,fid,'150')
    assert len(revisions(erp,pid))>=3
    assert shop.jobs(erp)[0]['grams']=='100'
    assert erp.s.one('SELECT cost_cents FROM order_items')['cost_cents']==old
    assert revisions(erp,pid)[0]['grams']=='150'


def test_simulator_changes_no_persisted_product_parameters_or_history(erp,recipe):
    pid,fid=recipe
    before=erp.s.db.total_changes
    scenario=mgmt.simulator(erp,pid,filament_change='100',packaging='5',settings={'fee_percent':'10','profit_percent':'40'})
    assert erp.s.db.total_changes==before
    assert scenario['scenario']['material_cents']==scenario['base']['material_cents']*2
    assert scenario['scenario']['suggested_cents']>scenario['base']['suggested_cents']
    with pytest.raises(ValueError):mgmt.simulator(erp,pid,filament_change='NaN')
    with pytest.raises(ValueError):mgmt.simulator(erp,pid,settings={'fee_percent':'90','profit_percent':'20'})


def test_receipts_separate_from_sales_and_use_receipt_dates(erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row()])
    baseline=report(erp,'01/11/2026','30/11/2026')
    rid=mgmt.save_receipt(erp,'02/12/2026','45','REPASSE-SINTETICO')
    mgmt.link_receipt(erp,rid,'A','45');mgmt.link_receipt(erp,rid,'A','45')
    rec=mgmt.reconciliation(erp,'01/11/2026','30/11/2026')[0]
    assert rec['received_cents']==4500 and rec['difference_cents']==0
    nov=report(erp,'01/11/2026','30/11/2026');dec=report(erp,'01/12/2026','31/12/2026')
    assert nov['gross_cents']==baseline['gross_cents'] and nov['operating_cents']==baseline['operating_cents'] and nov['received_cents']==0
    assert dec['gross_cents']==0 and dec['received_cents']==4500 and dec['received_cash_cents']==4500
    with pytest.raises(ValueError):mgmt.save_receipt(erp,'02/12/2026','44','REPASSE-SINTETICO')
    assert mgmt.receipt_rows(erp)[0]['amount_cents']==4500


def test_receipt_import_idempotency_and_transaction_rollback(erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row('A'),row('B')])
    rows=[{'Data':'06/11/2026','Referência':'R1','Valor recebido R$':'90','Pedido ID':oid,'Valor vinculado R$':'45'} for oid in ('A','B')]
    prepared=mgmt.prepare_receipts(rows);assert mgmt.import_receipts(erp,prepared)==1;mgmt.import_receipts(erp,prepared)
    assert len(mgmt.receipt_rows(erp))==1 and len(erp.s.rows('SELECT * FROM settlement_links'))==2
    with pytest.raises(ValueError):mgmt.prepare_receipts(rows+rows[:1])
    bad=mgmt.prepare_receipts([{'Data':'07/11/2026','Referência':'R2','Valor recebido R$':'40','Pedido ID':'A','Valor vinculado R$':'45'}])
    with pytest.raises(ValueError):mgmt.import_receipts(erp,bad)
    assert len(mgmt.receipt_rows(erp))==1


def test_receipt_multiple_orders_cannot_exceed_deposit(erp,product):
    load(erp,[row('A'),row('B')]);rid=mgmt.save_receipt(erp,'06/11/2026','50','R')
    mgmt.link_receipt(erp,rid,'A','40')
    with pytest.raises(ValueError):mgmt.link_receipt(erp,rid,'B','20')
    assert mgmt.receipt_rows(erp)[0]['unallocated_cents']==1000
    mgmt.unlink_receipt(erp,rid,'A');assert mgmt.receipt_rows(erp)[0]['unallocated_cents']==5000


def test_filters_use_frozen_recipe_and_presets_survive_reopen(erp,recipe):
    pid,fid=recipe;erp.origin('Sonic','10 cm','00001',pid);load(erp,[row()])
    erp.set_color(pid,fid,'400')
    filtered=report(erp,'01/11/2026','30/11/2026',filters={'sku':'00001','color':'Preto','material':'PLA','coverage':'completos'})
    assert filtered['usage_total_grams']=='100'
    assert not report(erp,'01/11/2026','30/11/2026',filters={'color':'Azul'})['orders_count']
    org.save_preset(erp.s,'PLA preto',{'color':'Preto','material':'PLA'})
    assert json.loads(erp.s.one('SELECT detail FROM filter_presets')['detail'])['color']=='Preto'


def test_diagnostic_contains_no_names_skus_paths_or_audit_detail(erp,product):
    erp.origin('NOME_SECRETO','MODELO_PRIVADO','SKU_PRIVADO',product);load(erp,[row()])
    diagnostic=json.dumps(org.diagnostic(erp.s))
    for value in ('Sonic','NOME_SECRETO','MODELO_PRIVADO','SKU_PRIVADO',str(erp.s.path),'CPF_PRIVADO_NAO_PERSISTIR'):assert value not in diagnostic
    assert org.diagnostic(erp.s)['integrity']=='ok'


def test_bulk_link_rollback_and_frozen_cost_preserved(erp,product):
    oid=erp.origin('X','V','123',None)
    with pytest.raises(ValueError):org.apply_links(erp,[(oid,product),(99999,product)])
    assert erp.s.one('SELECT product_id FROM origins WHERE id=?',(oid,))['product_id'] is None
    assert org.apply_links(erp,[(oid,product)])==1
    assert erp.s.one('SELECT product_id FROM origins WHERE id=?',(oid,))['product_id']==product


def test_import_comparison_detects_new_unchanged_updated_and_file(erp,tmp_path):
    from forgeon.importers.sheets import preview_orders
    from test_orders import M
    data,_=preview_orders([row()],M);path=tmp_path/'exemplo.xlsx';path.write_bytes(b'arquivo sintetico')
    comparison,duplicate=org.compare_import(erp.s,data,path);assert comparison[0]['action']=='Novo' and not duplicate
    load(erp,[row()]);comparison,_=org.compare_import(erp.s,data,path);assert comparison[0]['action']=='Sem alteração comercial'
    data[0]['fees_cents']+=1;comparison,_=org.compare_import(erp.s,data,path);assert comparison[0]['action']=='Atualizado'
    org.record_import(erp.s,path,{'start':'2026-11-01','end':'2026-11-06'},comparison)
    assert org.compare_import(erp.s,data,path)[1]


def test_help_all_screens_and_subtabs_and_remember_columns(app,erp,recipe,monkeypatch):
    errors=[];monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:errors.append(a[-1]))
    window=MainWindow(erp)
    for index in range(16):
        window.nav.setCurrentRow(index);app.processEvents();page=window.stack.widget(index)
        assert isinstance(page,Page) and page.help_button.text()=='ⓘ Como usar'
        assert 'Como interpretar' in help_text(page.page_title),page.page_title
        for tabs in page.findChildren(QTabWidget):
            assert tabs.cornerWidget()
            for i in range(tabs.count()):assert not help_text(tabs.tabText(i)).startswith('# Como usar')
    window.nav.setCurrentRow(1);table=window.products_table;table.set_hidden(1,True);table.horizontalHeader().moveSection(0,2);table.setColumnWidth(2,210);table.save_layout();window.close()
    second=MainWindow(erp);second.nav.setCurrentRow(1)
    assert second.products_table.isColumnHidden(1)
    assert second.products_table.horizontalHeader().logicalIndex(2)==0
    assert second.products_table.columnWidth(2)==210
    assert not errors,errors
    second.close()


def test_v2_migration_and_restore_preserve_source_and_current_new_tables(erp,tmp_path):
    from forgeon.db.store import DEFAULTS
    source=tmp_path/'v2.sqlite3'
    with closing(sqlite3.connect(source)) as old:
        old.executescript(Path('forgeon/db/schema.sql').read_text());old.executemany('INSERT INTO settings VALUES(?,?)',DEFAULTS.items());old.commit();Store.migrate(old,2)
        old.execute("INSERT INTO products(name,weight,hours) VALUES('Legado sintético','10','1')");old.commit()
    original=source.read_bytes();erp.s.restore(source)
    assert source.read_bytes()==original and erp.s.db.execute('PRAGMA user_version').fetchone()[0]==3
    assert erp.s.one('SELECT name FROM products')['name']=='Legado sintético'
    org.set_preference(erp.s,'appearance',{'font':14});backup=erp.s.backup();erp.s.restore(backup)
    assert org.preference(erp.s,'appearance')['font']==14
    erp.s.verify_schema(erp.s.db)
