import sqlite3
from contextlib import closing
import pytest
from forgeon.importers.sheets import preview_stats,read_xlsx
from forgeon.importers.slicing import duration
from forgeon.business.numbers import quantity
from forgeon.reports.finance import report


def test_stats_partial_period_cannot_claim_full_month():
    rows=preview_stats([{'Anúncio':'A','Receita':'1'}],{'listing':'Anúncio','revenue':'Receita'},'01/11/2026','15/11/2026',False)
    assert rows[0]['partial']==1


def test_stats_reject_total_row():
    with pytest.raises(ValueError):
        preview_stats([{'Anúncio':'Total','Receita':'1'}],{'listing':'Anúncio','revenue':'Receita'},'01/11/2026','30/11/2026',False)


def test_schema_mismatch_not_restored(erp,product,tmp_path):
    path=erp.s.backup(tmp_path/'different.sqlite3')
    with closing(sqlite3.connect(path)) as db, db:db.execute('ALTER TABLE products ADD COLUMN incompatible TEXT')
    with pytest.raises(ValueError,match='Esquema'):erp.s.restore(path)
    assert erp.product(product)['name']=='Sonic'


def test_bad_header_has_clear_error(tmp_path):
    from openpyxl import Workbook
    path=tmp_path/'a.xlsx';w=Workbook();w.active.append(['Produto']);w.save(path)
    with pytest.raises(ValueError,match='cabeçalho'):read_xlsx(path,header_row=10)


def test_negative_duration_not_made_positive():
    assert duration('-1h') is None
    assert duration('abc1h') is None
    assert duration('3600')==1

@pytest.mark.parametrize('value',['0','1.5','-1','NaN'])
def test_quantity_invalid(value):
    with pytest.raises(ValueError):quantity(value)


def test_empty_report_is_partial(erp):
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['partial'] and r['gross_cents']==0 and r['orders_count']==0


def test_mapped_but_blank_money_is_partial():
    from forgeon.importers.sheets import preview_orders
    from test_orders import row,M
    r=row();r['gross']='';r['fees']=''
    result,_=preview_orders([r],M)
    assert result[0]['partial']==1
    assert result[0]['gross_cents']==2500


def test_blank_status_rejected():
    from forgeon.importers.sheets import preview_orders
    from test_orders import row,M
    with pytest.raises(ValueError):preview_orders([row(status='')],M)


def test_restore_closes_staged_database_before_removing_it(erp,product,tmp_path):
    backup=erp.s.backup(tmp_path/'valid.sqlite3')
    erp.s.restore(backup)
    assert not list(erp.s.path.parent.glob('*.restore'))
    # On Windows deletion also verifies that backup connections released file handles.
    backup.unlink()
    assert not backup.exists()
