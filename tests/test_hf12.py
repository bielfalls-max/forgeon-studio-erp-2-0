from contextlib import contextmanager
from decimal import Decimal
from copy import deepcopy
import json
import pytest
from PySide6.QtWidgets import QMessageBox,QFileDialog,QDialog
from forgeon.db.store import Store
from forgeon.business.service import ERP
from forgeon.business.pricing import calculate
from forgeon.business.printers import profiles,save_profile,initialize_costs
from forgeon.business.project_quote import quote_project
from forgeon.importers.slicing import read_slicing,read_slicing_files,combine_plates
from forgeon.ui.production import SlicingProductDialog
from forgeon.ui.main import MainWindow


def gcode(tmp_path,index=1):
    path=tmp_path/f'placa-{index}.gcode'
    path.write_text(f'; HEADER_BLOCK_START\n; model printing time: 1h; total estimated time: 1h 20m\n; total filament weight [g] : {index+5}.5\n; filament: 3\n; HEADER_BLOCK_END\n; filament_colour = #D5B6A4;#000000;#0056B8\n; filament_type = PETG;PLA;PLA\n; printer_model = Bambu Lab A1\nG1 X999 E999\n')
    return path


@contextmanager
def fresh_erp(tmp_path):
    store=Store(tmp_path/'fresh.sqlite3')
    try:yield ERP(store)
    finally:store.close()


def test_bambu_total_weight_uses_real_filament_slot_and_palette(tmp_path):
    p=read_slicing(gcode(tmp_path))[0]
    assert p['colors']==[{'label':'#0056B8','hex':'#0056B8','material':'PLA','grams':'6.5'}]
    assert p['printer_model']=='Bambu Lab A1'
    assert Decimal(p['hours']).quantize(Decimal('.0001'))==Decimal('1.3333')


def test_six_gcodes_combine_all_plates_and_divide_complete_units(tmp_path):
    files=[gcode(tmp_path,n) for n in range(1,7)];plates=read_slicing_files(files)
    recipe=combine_plates(plates,list(range(6)),2)
    assert len(plates)==6 and len(recipe['colors'])==1
    assert Decimal(recipe['colors'][0]['grams'])==27
    assert Decimal(recipe['hours']).quantize(Decimal('.0001'))==Decimal('4.0000')
    assert all(p.name in plate['name'] for p,plate in zip(files,plates))


def test_duplicate_files_and_3mf_gcode_mix_are_rejected(tmp_path):
    p=gcode(tmp_path);duplicate=tmp_path/'copia.gcode';duplicate.write_bytes(p.read_bytes())
    with pytest.raises(ValueError,match='idênticos'):read_slicing_files([p,duplicate])
    from test_hf02 import sliced
    with pytest.raises(ValueError,match='Não misture'):read_slicing_files([sliced(tmp_path),p])
    p.write_text(p.read_text()+'; HEADER_BLOCK_START\n')
    with pytest.raises(ValueError,match='cabeçalhos'):read_slicing(p)


def test_initial_cost_defaults_are_filled_once_and_edits_survive_reopening(tmp_path):
    with fresh_erp(tmp_path) as erp:
        s=erp.s.settings()
        assert {k:s[k] for k in ('packaging_default','labor_unit','loss_percent','energy_kwh','power_w','machine_hour')}=={'packaging_default':'0.53','labor_unit':'2','loss_percent':'10','energy_kwh':'1.10','power_w':'140','machine_hour':'1'}
        pid=erp.save_product({'name':'Modelo de teste','weight':'100','hours':'2'})
        assert erp.product(pid)['packaging_cents']==53
        settings=erp.s.settings();settings.update(labor_unit='3',energy_kwh='1.45',packaging_default='0.80',loss_percent='7');erp.save_settings(settings)
        ERP(erp.s)
        assert erp.s.settings()['labor_unit']=='3' and erp.s.settings()['loss_percent']=='7'
        assert erp.product(pid)['packaging_cents']==53


def test_existing_zero_packaging_gets_default_without_changing_frozen_cost(erp):
    from test_orders import load,row
    from test_hf02 import legacy_database
    pid=erp.save_product({'name':'Sonic','model':'10 cm','weight':'20','hours':'1'})
    erp.origin('Sonic','10 cm','00001',pid);load(erp,[row()]);items=erp.s.rows('SELECT * FROM order_items')
    with erp.s.transaction():
        erp.s.db.execute("DELETE FROM preferences WHERE key='cost_defaults_hf12'")
        erp.s.db.execute("DELETE FROM settings WHERE key IN('packaging_default','labor_unit','loss_percent')")
    initialize_costs(erp)
    assert erp.product(pid)['packaging_cents']==53
    assert erp.s.rows('SELECT * FROM order_items')==items


def test_loss_reserve_applies_only_to_manufacture_and_labor_once(erp):
    config=erp.s.settings();config.update(loss_percent='10',labor_unit='2',energy_kwh='1.10',power_w='120',machine_hour='1')
    product={'weight':'100','hours':'2','manual_cents':None,'packaging_cents':53,'other_cents':100}
    c=calculate(product,[],config)
    # (9 + .264 + 2) * 1.10 + 2 + .53 + 1 = 15.9204
    assert c['total_cents']==1592 and c['loss_cents']==113 and c['labor_cents']==200
    assert c['packaging_cents']==53 and c['grams']=='100'  # reserva não é baixa de estoque
    with pytest.raises(ValueError):calculate(product,[],{**config,'loss_percent':'NaN'})
    with pytest.raises(ValueError):calculate(product,[],{**config,'loss_percent':'101'})


def test_quote_by_slicer_is_read_only_and_can_change_profile(app,tmp_path,monkeypatch):
    warnings=[];monkeypatch.setattr(QMessageBox,'warning',lambda *a:warnings.append(a[-1]))
    with fresh_erp(tmp_path) as erp:
        paths=[gcode(tmp_path,i) for i in (1,2)];before=erp.s.db.total_changes
        dialog=SlicingProductDialog(erp,paths,quote=True)
        assert dialog.printer.currentData()=='a1' and dialog.packaging.text()=='0.53'
        dialog.save();first=dialog.quote_data
        assert first and first['labor_cents']==200 and first['loss_percent']=='10' and not first['missing']
        assert dialog.result()!=QDialog.DialogCode.Accepted
        dialog.printer.setCurrentIndex(dialog.printer.findData('ad5x'));assert dialog.quote_data is None
        dialog.save();assert dialog.quote_data['energy_cents']>first['energy_cents']
        assert erp.s.db.total_changes==before and not erp.s.rows('SELECT * FROM products')
        dialog.reject();assert not warnings


def test_quote_missing_time_stays_partial_instead_of_inventing_time(erp):
    recipe={'hours':None};colors=[{'grams':'25','material':'PLA','color':'Branco','kg':'90'}]
    before=erp.s.db.total_changes;c=quote_project(erp,recipe,colors,'0.53','0')
    assert 'tempo ausente' in c['missing'] and erp.s.db.total_changes==before


def test_import_saves_printer_and_profile_edit_changes_only_future_cost(app,erp,tmp_path,monkeypatch):
    from test_orders import load,row
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:pytest.fail(str(a[-1])))
    dialog=SlicingProductDialog(erp,gcode(tmp_path));dialog.name.setText('Figura teste');dialog.model.setText('13 cm');dialog.confirm.setChecked(True);dialog.save()
    pid=dialog.result_data[0];assert erp.product(pid)['_power_w']=='120'
    erp.origin('Figura teste','13 cm','00001',pid);load(erp,[{**row(title='Figura teste'),'variation':'13 cm'}]);before=erp.s.rows('SELECT * FROM order_items')
    old=erp.cost(pid)['energy_cents'];save_profile(erp.s,'a1','240','2.5')
    assert erp.cost(pid)['energy_cents']>old and erp.product(pid)['_machine_hour']=='2.5'
    assert erp.s.rows('SELECT * FROM order_items')==before
    detail=json.loads(erp.s.one('SELECT detail FROM product_slices WHERE product_id=?',(pid,))['detail'])
    assert detail['source_files']==['placa-1.gcode']


def test_pricing_has_project_quote_action_and_uses_multiple_file_picker(app,erp,tmp_path,monkeypatch):
    path=gcode(tmp_path);monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *a:([str(path)],''));calls=[]
    def execute(dialog):calls.append((dialog.quote_mode,len(dialog.paths)));return QDialog.DialogCode.Rejected
    monkeypatch.setattr(SlicingProductDialog,'exec',execute)
    w=MainWindow(erp)
    try:w.nav.setCurrentRow(3);w.quote_from_slicer();assert calls==[(True,1)]
    finally:w.close()


def test_upgrade_preserves_custom_rates_packaging_and_linked_supplies(tmp_path):
    s=Store(tmp_path/'legacy.sqlite3')
    try:
        with s.transaction():
            s.db.execute("UPDATE settings SET value='1.37' WHERE key='energy_kwh'")
            s.db.execute("UPDATE settings SET value='199' WHERE key='power_w'")
            a=s.db.execute("INSERT INTO products(name) VALUES('Sem embalagem')").lastrowid
            b=s.db.execute("INSERT INTO products(name,packaging_cents) VALUES('Personalizada',97)").lastrowid
            c=s.db.execute("INSERT INTO products(name) VALUES('Com caixa vinculada')").lastrowid
            sid=s.db.execute("INSERT INTO supplies(name,category,unit,unit_cents) VALUES('Caixa','Embalagens','un','53')").lastrowid
            s.db.execute('INSERT INTO product_supplies VALUES(?,?,?)',(c,sid,'1'))
        erp=ERP(s)
        assert erp.product(a)['packaging_cents']==53 and erp.product(b)['packaging_cents']==97
        assert erp.product(c)['packaging_cents']==0 and erp.product(c)['other_cents']==53
        assert s.settings()['energy_kwh']=='1.37' and s.settings()['power_w']=='199'
    finally:s.close()


def test_new_sales_product_gets_packaging_but_no_invented_production_cost(tmp_path):
    from test_orders import load,row
    with fresh_erp(tmp_path) as erp:
        load(erp,[{**row(title='Anúncio sintético'),'variation':'Figura inédita'}])
        from forgeon.business.studio import catalog_from_sales
        with erp.s.transaction():catalog_from_sales(erp)
        item=erp.s.one('SELECT * FROM order_items')
        assert erp.product(item['product_id'])['packaging_cents']==53
        assert item['cost_cents'] is None and erp.cost(item['product_id'])['missing']


def test_existing_simulator_overrides_profile_temporarily_without_saving(erp):
    from forgeon.business.organization import set_preference
    from forgeon.business.management import simulator
    pid=erp.save_product({'name':'Figura perfil','weight':'20','hours':'2'})
    set_preference(erp.s,'product_printer:'+str(pid),'a1');before=erp.s.db.total_changes
    base=simulator(erp,pid);assert base['base']['energy_cents']==24 and base['difference_cents']==0
    changed=simulator(erp,pid,settings={'power_w':'240','machine_hour':'3','loss_percent':'10','labor_unit':'2'})
    assert changed['scenario']['energy_cents']==48 and changed['scenario']['machine_cents']==600
    assert changed['scenario']['loss_cents']>0 and changed['scenario']['labor_cents']==200
    assert erp.product(pid)['_power_w']=='120' and erp.s.db.total_changes==before
