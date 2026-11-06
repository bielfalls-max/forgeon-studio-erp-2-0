from decimal import Decimal
import pytest
from forgeon.business.numbers import decimal,cents,day,money
from forgeon.business.pricing import calculate
from forgeon.db.store import Store

@pytest.mark.parametrize('v',['-1','NaN','Infinity','-Infinity','abc','1e99'])
def test_reject_numbers(v):
    with pytest.raises(ValueError):decimal(v)


def test_brazil_numbers():
    assert cents('R$ 1.234,56')==123456
    assert cents('1.005')==101
    assert day('06/11/2026')=='2026-11-06'
    assert money(123456)=='R$ 1.234,56'


def test_price_exact(erp,product):
    # 100 g * 90/kg + 2 h * 0.15 kW * 1 + 2 h * 1 + embalagem 2 + outros 1
    c=erp.cost(product)
    assert c['material_cents']==900
    assert c['energy_cents']==30
    assert c['machine_cents']==200
    assert c['total_cents']==1430
    assert c['suggested_cents']==2043
    settings=erp.s.settings();settings.update(fee_percent='10',fee_fixed='2',profit_percent='30')
    p=erp.product(product)
    c=calculate(p,[],settings)
    assert c['suggested_cents']==2717
    settings['pricing_mode']='acrescimo'
    assert calculate(p,[],settings)['suggested_cents']==2288
    settings.update(fee_percent='80',pricing_mode='margem')
    with pytest.raises(ValueError):calculate(p,[],settings)


def test_manual_replaces_manufacture(erp,product):
    erp.save_product({'name':'Sonic','weight':'100','hours':'2','manual':'20','packaging':'2','other':'1'},product)
    c=erp.cost(product)
    assert c['total_cents']==2300
    assert c['manufacture_cents']==2000


def test_color_weight_and_copy_without_sku(erp,product):
    white=erp.filament('PLA','Branco','100')
    gold=erp.filament('PLA','Dourado','120')
    erp.set_color(product,white,'25');erp.set_color(product,gold,'50')
    assert erp.cost(product)['grams']=='75'
    assert erp.cost(product)['material_cents']==850
    p2=erp.save_product({'name':'Super Sonic','weight':'1','hours':'1'})
    o=erp.origin('Super Sonic','10 cm','00009',p2)
    erp.copy_costs(product,p2)
    assert erp.cost(p2)==erp.cost(product)
    assert erp.s.one('SELECT sku FROM origins WHERE id=?',(o,))['sku']=='00009'
    erp.set_color(p2,gold,'0')
    assert erp.cost(p2)['grams']=='25'


def test_sku_conflicts_reservations_retirement(erp,product):
    erp.reserve('00001')
    assert erp.reserve()=='00002'
    erp.retire('00002')
    assert erp.reserve()=='00003'
    o=erp.origin('Anúncio A','Sonic','00001',product)
    p2=erp.save_product({'name':'Super Sonic'})
    erp.origin('Anúncio B','Super Sonic','00001',p2)
    assert erp.conflicts()=={'00001'}
    with pytest.raises(ValueError):erp.retire('00001')
    erp.origin('Anúncio A','Sonic','00004',product,o)
    assert not erp.conflicts()
    erp.unlink(o)
    erp.retire('00004')
    with pytest.raises(ValueError):erp.origin('Outro','Sonic','00004',product)
    with pytest.raises(ValueError):erp.reserve('00002')


def test_sharing_and_no_ambiguous_auto_merge(erp,product):
    erp.origin('Anúncio 1','Sonic','001',product)
    erp.origin('Anúncio 2','Sonic','002',product)
    assert len(erp.s.rows('SELECT * FROM products'))==1
    assert len(erp.s.rows('SELECT * FROM origins WHERE product_id=?',(product,)))==2
    assert erp.suggestions('','Super Sonic')==[]
    silver=erp.save_product({'name':'Silver','model':'10 cm'})
    assert erp.suggestions('','SÍLVER - Hedgehog')[0]['id']==silver
    assert erp.suggestions('','Silver 20 cm')==[]
    erp.archive(product)
    assert erp.product(product)['archived']==1
    erp.archive(product)
    assert erp.product(product)['archived']==0


def test_empty_and_persistent_database(tmp_path):
    path=tmp_path/'db.sqlite3'
    s=Store(path)
    assert s.rows('SELECT * FROM products')==[]
    with s.transaction():s.db.execute("INSERT INTO products(name) VALUES(?)",('Novo',))
    s.close()
    s=Store(path)
    assert s.rows('SELECT * FROM products')[0]['name']=='Novo'
    s.close()


def test_transaction_rollback(erp):
    with pytest.raises(RuntimeError):
        with erp.s.transaction():
            erp.s.db.execute("INSERT INTO products(name) VALUES('teste')")
            raise RuntimeError('falha')
    assert erp.s.rows('SELECT * FROM products')==[]


def test_invalid_settings_do_not_persist(erp):
    old=erp.s.settings();data=dict(old);data['fee_percent']='100'
    with pytest.raises(ValueError):erp.save_settings(data)
    assert erp.s.settings()==old
