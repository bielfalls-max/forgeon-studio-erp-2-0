"""Cenários sintéticos de navegação, filtros, preços pagos e histórico."""
import pytest
from PySide6.QtWidgets import QMessageBox
from forgeon.ui.main import MainWindow
from forgeon.ui.navigation import GROUPS
from forgeon.ui.filters import Filters
from forgeon.business import costs,workshop,management
from forgeon.business.organization import preference
from forgeon.reports.finance import report
from test_orders import load,row

@pytest.fixture
def window(app,erp,monkeypatch):
    errors=[];monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:errors.append(str(a[-1])))
    w=MainWindow(erp);yield w
    w.close();assert not errors,errors


def prepare_two_products(erp,product):
    f=erp.filament('PLA','Preto','90');erp.set_color(product,f,'100');erp.origin('Sonic','10 cm','00001',product)
    other=erp.save_product({'name':'Outro','model':'10 cm','weight':'50','hours':'1'});f2=erp.filament('PETG','Branco','110');erp.set_color(other,f2,'50');erp.origin('Outro','10 cm','00002',other)
    load(erp,[row('NOV',qty='2',status='A Enviar'),row('NOV',title='Outro',sku='00002',status='A Enviar'),{**row('OUT',title='Outro',sku='00002'),'date':'06/10/2026'}])
    return f,other,f2


def test_eight_groups_route_subtabs_and_keep_last_tab(window):
    assert window.nav.groups.count()==7 and sorted(i for _,routes in GROUPS for i in routes)==list(range(16))
    window.nav.groups.setCurrentRow(2);assert window.stack.currentIndex()==3
    window.nav.tabs.setCurrentIndex(1);assert window.stack.currentIndex()==14
    window.nav.groups.setCurrentRow(4);assert window.stack.currentIndex()==5
    window.nav.groups.setCurrentRow(2);assert window.stack.currentIndex()==14
    window.nav.setCurrentRow(15);assert window.nav.groups.currentRow()==5 and window.nav.tabs.currentIndex()==2
    window.set_sidebar_compact(True,persist=False);assert window.nav.groups.item(5).text()=='Finanças'
    window.set_sidebar_compact(False,persist=False);assert window.nav.groups.item(5).text()=='Financeiro'


def test_date_filter_custom_range_and_clear(erp,app):
    f=Filters(erp,dates=True,product=True,order=True,color=True);f.start.setText('01/10/2026');f.end.setText('31/10/2026');assert f.values()['start']=='2026-10-01'
    f.end.setText('30/09/2026')
    with pytest.raises(ValueError):f.values()
    f.clear();assert f.values()['start']=='' and f.values()['end']=='' and f.values()['product'] is None
    f.period.setCurrentIndex(f.period.findData('previous'));assert f.values()['start']<f.values()['end']


def test_orders_filters_and_export_items_do_not_leak_other_orders(window,erp,product):
    fid,other,fid2=prepare_two_products(erp,product);window.nav.setCurrentRow(5);f=window.orders_filters
    f.start.setText('01/11/2026');f.end.setText('30/11/2026');f.fields['color'].setText('Preto');window.update_orders()
    assert [r['id'] for r in window.orders_table.records]==['NOV']
    assert len(window.filtered_order_items())==1 and window.filtered_order_items()[0]['product_id']==product
    window.order_search.setText('Outro');f.clear();window.update_orders();assert {r['id'] for r in window.orders_table.records}=={'OUT','NOV'}
    window.order_status.setCurrentIndex(window.order_status.findData('texto:A Enviar'));window.update_orders();assert len(window.orders_table.records)==1


def test_finance_date_material_and_category_filters(window,erp):
    fid=erp.filament('PLA','Preto','90');erp.purchase('06/10/2026',fid,'500','40','5');erp.purchase('06/11/2026',fid,'1000','90','10');erp.expense('06/11/2026','Energia','Oficina','30');erp.expense('06/10/2026','Aluguel','Oficina','100')
    window.nav.setCurrentRow(7);f=window.finance_filters;f.start.setText('01/11/2026');f.end.setText('30/11/2026');window.update_finance();assert len(window.expenses_table.records)==1 and len(window.purchases_table.records)==1
    f.fields['material'].setText('PLA');window.update_finance();assert not window.expenses_table.records and len(window.purchases_table.records)==1
    f.clear();window.finance_query.setText('Aluguel');window.update_finance();assert len(window.expenses_table.records)==1 and not window.purchases_table.records


def test_production_removed_from_navigation(window):
    assert all(title!='Produção' for title,_ in GROUPS)
    window.nav.setCurrentRow(12);assert window.stack.widget(12).page_title=='Materiais e compras'


def test_stock_dates_filter_movements_not_current_balance(window,erp):
    fid=erp.filament('PLA','Preto','90');workshop.register_roll(erp,fid,'Antigo','500','06/10/2026');workshop.register_roll(erp,fid,'Novo','100','06/11/2026');window.nav.setCurrentRow(13)
    f=window.stock_filters;f.start.setText('01/11/2026');f.end.setText('30/11/2026');window.refresh_stock();assert len(window.roll_stock.records)==1 and len(window.moves_stock.records)==1 and window.material_stock.records[0]['grams']=='600'
    f.fields['color'].setText('Branco');window.refresh_stock();assert not window.material_stock.records and not window.moves_stock.records


def test_last_purchase_uses_mass_freight_and_explicit_apply_only(erp,product):
    fid=erp.filament('PLA','Preto','90');erp.set_color(product,fid,'100');erp.origin('Sonic','10 cm','00001',product);load(erp,[row()]);snapshot=erp.s.one('SELECT cost_cents,cost_detail FROM order_items');workshop.create_job(erp,product,1);recipe=erp.s.one('SELECT recipe FROM production_jobs')['recipe']
    erp.purchase('06/10/2026',fid,'1000','100','0');erp.purchase('06/11/2026',fid,'500','60','10');current=costs.material_costs(erp)[0]
    assert current['kg_cents']==9000 and current['purchase_kg_cents']==14000
    costs.use_purchase(erp,fid,current['purchase_id']);assert erp.cost(product)['material_cents']==1400
    assert erp.s.one('SELECT cost_cents,cost_detail FROM order_items')==snapshot and erp.s.one('SELECT recipe FROM production_jobs')['recipe']==recipe
    assert preference(erp.s,'cost:filament:'+str(fid))['source']=='Compra confirmada'


def test_current_cost_edit_is_dated_and_preserves_sale(erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row()]);old=erp.s.one('SELECT cost_cents FROM order_items')['cost_cents'];settings=erp.s.settings();settings.update({'energy_kwh':'1.50','machine_hour':'3','fee_percent':'15'});erp.save_settings(settings)
    assert preference(erp.s,'cost:settings')['reviewed'] and erp.s.settings()['energy_kwh']=='1.50' and erp.s.one('SELECT cost_cents FROM order_items')['cost_cents']==old


def test_simulator_sales_period_changes_observation_not_catalog(erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row('NOV'),{**row('OUT'),'date':'06/10/2026','unit':'20'}]);before=erp.s.db.total_changes
    r=management.simulator(erp,product,period={'start':'2026-11-01','end':'2026-11-30'});assert r['observed_units']==1 and r['at_average']['price_cents']==2500 and erp.s.db.total_changes==before


def test_product_and_pricing_filters_share_material_identity(window,erp,product):
    fid,other,fid2=prepare_two_products(erp,product);window.nav.setCurrentRow(1);window.products_filters.fields['color'].setText('Branco');window.update_products()
    assert [r['id'] for r in window.products_table.records]==[other] and [r['id'] for r in window.visible_products()]==[other]
    window.nav.setCurrentRow(3);window.pricing_filters.fields['material'].setText('PLA');window.update_pricing();assert [r['id'] for r in window.pricing_catalog.records]==[product]
    window.nav.setCurrentRow(2);window.materials_filters.fields['material'].setText('PLA');window.update_colors();assert len(window.filament_table.records)==1 and len(window.product_colors_table.records)==1


def test_receipts_id_reference_and_date_filters_consistent(window,erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row('A'),row('B')]);one=management.save_receipt(erp,'06/11/2026','45','REPASSE-A');two=management.save_receipt(erp,'06/12/2026','45','REPASSE-B');management.link_receipt(erp,one,'A','45');management.link_receipt(erp,two,'B','45')
    window.nav.setCurrentRow(15);window.receipt_start.setText('01/11/2026');window.receipt_end.setText('30/11/2026');window.receipt_order_start.setText('01/11/2026');window.receipt_order_end.setText('30/11/2026');window.receipts_filters.fields['order'].setText('A');window.receipt_search.setText('REPASSE-A');window.refresh_receipts()
    assert len(window.receipt_table.records)==1 and len(window.receipt_links.records)==1 and len(window.reconciliation_table.records)==1 and window.receipt_links.records[0]['order_id']=='A'


def test_report_order_filter_and_saved_dates(window,erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row('A'),row('B')]);r=report(erp,'01/11/2026','30/11/2026',filters={'order':'A'});assert r['orders_count']==1 and r['usage_orders'][0]['order_id']=='A'
    window.nav.setCurrentRow(8);window.report_start.setText('2026-11-01');window.report_end.setText('2026-11-30');window.report_extra['order'].setText('A');window.form=lambda *a,**k:{'name':'Novembro A'};window.save_report_preset();window.report_start.setText('2026-10-01');window.report_extra['order'].clear();window.report_presets.setCurrentIndex(1);window.load_report_preset()
    assert window.report_start.text()=='2026-11-01' and window.report_extra['order'].text()=='A'


def test_material_and_color_match_same_filament_in_report(erp,product):
    f=erp.filament('PLA','Preto','90');other=erp.filament('PETG','Branco','100');erp.set_color(product,f,'50');erp.set_color(product,other,'50');erp.origin('Sonic','10 cm','00001',product);load(erp,[row()])
    assert report(erp,'01/11/2026','30/11/2026',filters={'material':'PLA','color':'Branco'})['orders_count']==0
    assert report(erp,'01/11/2026','30/11/2026',filters={'material':'PETG','color':'Branco'})['orders_count']==1


def test_pricing_comparison_and_small_window_geometry(window,erp,product,app):
    from PySide6.QtCore import QTimer,QPoint
    from PySide6.QtWidgets import QApplication
    window.resize(1100,700);window.show();window.nav.setCurrentRow(3);app.processEvents();assert window.pricing_catalog.isHidden()
    assert window.pricing_components.mapToGlobal(QPoint(0,0)).y()>=max(c.mapToGlobal(QPoint(0,c.height())).y() for c in window.pricing_metrics)
    opened=[]
    def close_comparison():
        dialog=QApplication.activeModalWidget();opened.append(dialog.windowTitle());dialog.accept()
    QTimer.singleShot(30,close_comparison);window.compare_pricing_products();assert opened and window.pricing_catalog.isHidden() and len(window.pricing_catalog.records)==1
