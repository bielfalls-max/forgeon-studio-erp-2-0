import pytest
from forgeon.importers.sheets import preview_orders,import_orders,preview_stats,import_stats,detect
from forgeon.reports.finance import report

M={k:k for k in ('order_id','date','status','listing','variation','sku','qty','unit','gross','fees','refund')}


def row(oid='A',title='Sonic',sku='00001',qty='1',gross='50',status='Concluído',refund='0'):
    return dict(order_id=oid,date='06/11/2026',status=status,listing=title,variation='10 cm',sku=sku,qty=qty,unit='25',gross=gross,fees='5',refund=refund,**{'CPF':'CPF_PRIVADO_NAO_PERSISTIR','Telefone':'999','Endereço':'Privado'})


def load(erp,rows,partial=False):
    orders,_=preview_orders(rows,M,partial=partial)
    import_orders(erp,orders)
    return orders


def test_multi_item_reimport_partial_and_cost_snapshot(erp,product):
    erp.origin('Sonic','10 cm','00001',product)
    erp.origin('Silver','10 cm','00002',product)
    load(erp,[row(),row(title='Silver',sku='00002'),row(oid='B')])
    s=erp.s
    assert len(s.rows('SELECT * FROM orders'))==2
    assert len(s.rows('SELECT * FROM order_items'))==3
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['gross_cents']==10000
    assert r['fees_cents']==1000
    old=s.one('SELECT * FROM order_items WHERE order_id=? ORDER BY id',('A',))
    erp.save_product({'name':'Sonic','weight':'999','hours':'9'},product)
    load(erp,[row(),row(title='Silver',sku='00002')],partial=True)
    assert len(s.rows('SELECT * FROM orders'))==2
    assert len(s.rows('SELECT * FROM order_items'))==3
    item=s.one('SELECT * FROM order_items WHERE order_id=? ORDER BY id',('A',))
    assert item['cost_cents']==old['cost_cents']
    assert item['cost_at']==old['cost_at']
    assert s.one('SELECT * FROM orders WHERE id=?',('B',))
    assert 'CPF_PRIVADO_NAO_PERSISTIR' not in str(s.rows('SELECT * FROM audit'))
    assert 'Privado' not in str(s.rows('SELECT * FROM order_items'))


def test_detach_and_correction_keep_original_sku_and_orders(erp,product):
    o=erp.origin('Sonic','10 cm','00001',product)
    load(erp,[row()])
    old=erp.s.one('SELECT * FROM order_items')
    erp.origin('Sonic','10 cm','00999',product,o)
    assert erp.s.one('SELECT * FROM order_items')['original_sku']=='00001'
    erp.unlink(o)
    assert erp.s.one('SELECT * FROM order_items')['product_id']==product
    assert erp.s.one('SELECT * FROM order_items')['cost_cents']==old['cost_cents']
    load(erp,[row()])
    assert erp.s.one('SELECT * FROM order_items')['cost_cents']==old['cost_cents']


def test_cancellations_and_returns(erp,product):
    erp.origin('Sonic','10 cm','00001',product)
    load(erp,[row(oid='OK'),row(oid='CANCEL',status='Cancelado'),row(oid='RETURN',status='Devolução / reembolso',refund='50')])
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['gross_cents']==10000
    assert r['refunds_cents']==5000
    assert r['fees_cents']==1000
    assert r['production_cents']==2860
    assert r['operating_cents']==1140
    assert sum(int(c['grams']) for c in r['consumption'])==200


def test_stats_separate_and_reimport(erp):
    load(erp,[row()])
    stats=preview_stats([{'Anúncio':'Sonic','Receita':'50','Pedidos':1}],{'listing':'Anúncio','revenue':'Receita','orders_count':'Pedidos'},'01/11/2026','30/11/2026',False)
    import_stats(erp,stats);import_stats(erp,stats)
    assert len(erp.s.rows('SELECT * FROM stats'))==1
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['gross_cents']==5000 and r['stats_cents']==5000
    assert r['partial']  # missing product cost
    with pytest.raises(ValueError):
        import_stats(erp,preview_stats([{'Anúncio':'Sonic','Receita':'10'}],{'listing':'Anúncio','revenue':'Receita'},'01/11/2026','15/11/2026',True))
    assert len(erp.s.rows('SELECT * FROM stats'))==1


def test_import_failure_rolls_back_all_orders(erp):
    orders,_=preview_orders([row('A'),row('B')],M)
    orders[1]['items'][0]['qty']=0
    with pytest.raises(Exception):import_orders(erp,orders)
    assert erp.s.rows('SELECT * FROM orders')==[]
    assert erp.s.rows('SELECT * FROM origins')==[]
    assert len(list((erp.s.path.parent/'backups').glob('*.sqlite3')))==1


def test_toship_and_ambiguous_totals(erp):
    _,warnings=preview_orders([row()],M,'Order.toship.xlsx')
    orders,_=preview_orders([row()],M,'Order.toship.xlsx')
    assert orders[0]['partial']==1
    assert any('Order.all' in w for w in warnings)
    with pytest.raises(ValueError):preview_orders([row(),row(title='Silver',gross='100')],M)


def test_freeze_later_has_current_timestamp(erp,product):
    load(erp,[row()])
    assert erp.s.one('SELECT * FROM order_items')['cost_cents'] is None
    origin=erp.s.one('SELECT * FROM origins')
    erp.origin(origin['listing'],origin['variation'],origin['sku'],product,origin['id'])
    assert erp.freeze_missing_costs()==1
    item=erp.s.one('SELECT * FROM order_items')
    assert item['cost_at'] and item['cost_cents']==1430
    assert erp.freeze_missing_costs()==0


def test_purchase_not_double_counted(erp,product):
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row()])
    fid=erp.filament('PLA','Branco',90)
    erp.purchase('06/11/2026',fid,1000,90,10)
    erp.expense('06/11/2026','Aluguel','',10)
    r=report(erp,'01/11/2026','30/11/2026')
    assert r['operating_cents']==5000-500-1430-1000
    assert r['cash_cents']==5000-500-1000-10000


def test_consumption_uses_frozen_colors_by_fortnight(erp,product):
    fid=erp.filament('PLA','Vermelho',100);erp.set_color(product,fid,100)
    erp.origin('Sonic','10 cm','00001',product)
    a=row();b=row('B');b['date']='20/11/2026'
    load(erp,[a,b]);erp.set_color(product,fid,900)
    r=report(erp,'01/11/2026','30/11/2026')
    assert {c['fortnight'] for c in r['consumption']}=={'1ª quinzena','2ª quinzena'}
    assert all(c['grams']=='100' for c in r['consumption'])
