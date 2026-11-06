from zipfile import ZipFile
import sqlite3
import pytest
from openpyxl import Workbook,load_workbook
from forgeon.db.store import Store
from forgeon.importers.slicing import read_slicing,per_unit
from forgeon.importers.sheets import read_xlsx
from forgeon.importers import catalog
from forgeon.reports.xlsx import export,templates


def test_backup_restore_and_preservation(erp,product,tmp_path):
    backup=erp.s.backup(tmp_path/'copy.sqlite3')
    erp.save_product({'name':'Depois'})
    previous=erp.s.restore(backup)
    assert [p['name'] for p in erp.s.rows('SELECT * FROM products')]==['Sonic']
    with sqlite3.connect(previous) as c:
        assert c.execute('SELECT count(*) FROM products').fetchone()[0]==2
    erp.s.validate(erp.s.db)
    with pytest.raises(ValueError):erp.s.backup(backup)


def test_incompatible_backup_rejected_without_changing_database(erp,product,tmp_path):
    old=tmp_path/'legacy.sqlite3'
    with sqlite3.connect(old) as c:c.execute('CREATE TABLE old(x)')
    with pytest.raises(ValueError):erp.s.restore(old)
    assert erp.product(product)['name']=='Sonic'
    old.write_bytes(b'not sqlite')
    with pytest.raises(sqlite3.DatabaseError):erp.s.restore(old)
    assert erp.product(product)['name']=='Sonic'


def test_backup_with_trigger_rejected(erp,product,tmp_path):
    path=erp.s.backup(tmp_path/'unsafe.sqlite3')
    with sqlite3.connect(path) as c:
        c.execute("CREATE TRIGGER bad AFTER INSERT ON products BEGIN DELETE FROM products; END")
    with pytest.raises(ValueError):erp.s.restore(path)
    assert erp.product(product)['name']=='Sonic'


def test_xlsx_export_strings_never_formulas(tmp_path):
    path=tmp_path/'export.xlsx'
    export(path,{'Dados':[{'name':'=HYPERLINK("http://example.com")','sku':'00001','total_cents':1234},{'name':'+1+2','sku':'@SUM(1)','total_cents':0}]})
    wb=load_workbook(path,data_only=False); ws=wb.active
    assert ws['A2'].data_type=='s'
    assert ws['A3'].data_type=='s'
    assert ws['B2'].value=='00001'
    assert ws['C2'].value=='R$ 12,34'
    assert ws.max_row==3
    wb.close()


def test_xlsx_read_zero_mask_and_no_formula(tmp_path):
    path=tmp_path/'test.xlsx';wb=Workbook();ws=wb.active
    ws.append(['SKU','Produto']);ws.append([12,'Boneco']);ws['A2'].number_format='00000';wb.save(path)
    headers,rows,_=read_xlsx(path)
    assert rows[0]['SKU']=='00012'
    ws['B2']='=1+1';wb.save(path)
    with pytest.raises(ValueError,match='Fórmula'):read_xlsx(path)


def test_empty_templates_and_catalog_transaction(erp,tmp_path):
    templates(tmp_path)
    assert len(list(tmp_path.glob('modelo_*.xlsx')))==5
    for path in tmp_path.glob('modelo_*.xlsx'):
        _,rows,_=read_xlsx(path)
        assert rows==[]
    rows=catalog.prepare([{'Nome':'Novo','Peso g':'10','Horas':'1'}],'produtos')
    catalog.commit(erp,rows,'produtos')
    assert erp.s.one('SELECT * FROM products')['name']=='Novo'
    rows=catalog.prepare([{'Material':'PLA','Cor':'Branco','Preço kg R$':'90'},{'Material':'PLA','Cor':'Branco','Preço kg R$':'90'}],'filamentos')
    with pytest.raises(sqlite3.IntegrityError):catalog.commit(erp,rows,'filamentos')
    assert erp.s.rows('SELECT * FROM filaments')==[]


def test_bambu_multiplate_per_unit(tmp_path):
    path=tmp_path/'sliced.3mf'
    xml='''<config><plate><metadata key="index" value="1"/><metadata key="prediction" value="7200"/>
    <filament id="1" type="PLA" color="#FFFFFF" used_g="40"/><filament id="2" type="PLA" used_g="20"/></plate>
    <plate><metadata key="index" value="2"/><metadata key="prediction" value="3600"/><filament id="1" used_g="30"/></plate></config>'''
    with ZipFile(path,'w') as z:z.writestr('Metadata/slice_info.config',xml)
    plates=read_slicing(path)
    assert len(plates)==2
    c=per_unit(plates[0],2)
    assert c['hours']=='1'
    assert [x['grams'] for x in c['colors']]==['20','10']
    with pytest.raises(ValueError):per_unit(plates[0],0)


def test_gcode_metadata_only(tmp_path):
    path=tmp_path/'test.gcode'
    path.write_text('; filament used [g] = 30.5, 10\n; estimated printing time (normal mode) = 1h 30m\nM112\nG1 X0\n',encoding='utf-8')
    c=read_slicing(path)[0]
    assert c['hours']=='1.500000000000000000000000000'
    assert c['colors'][0]['grams']=='30.5'
    path.write_text('G1 X1 Y1\n',encoding='utf-8')
    with pytest.raises(ValueError):read_slicing(path)


def test_xml_entities_and_zip_paths_rejected(tmp_path):
    path=tmp_path/'bad.3mf'
    with ZipFile(path,'w') as z:
        z.writestr('Metadata/slice_info.config','<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><config>&e;</config>')
    with pytest.raises(Exception):read_slicing(path)
    with ZipFile(path,'w') as z:z.writestr('../outside','bad')
    with pytest.raises(ValueError):read_slicing(path)
    with ZipFile(path,'w') as z:z.writestr('3D/model.model','<model/>')
    with pytest.raises(ValueError,match='sem metadados'):read_slicing(path)
