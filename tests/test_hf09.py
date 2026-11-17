from forgeon.business.unification import physical_key,proposals,apply
from forgeon.business.studio import catalog_from_sales
from test_orders import row,load

def draft(erp,name,listing):return erp.save_product({'name':name,'model':listing,'notes':'Identificado nas vendas. Receita pendente.'})

def test_character_and_size_are_separate():
    assert physical_key('super sonic,super sonic','Anúncio A',draft=True)==('super sonic','12')
    assert physical_key('SuperSonic','Anúncio B',draft=True)==('super sonic','12')
    assert physical_key('Sonic 16cm','Anúncio 12 cm',draft=True)==('sonic','16')
    assert physical_key('Shadow','Boneco 16 cm',draft=True) is None
    assert physical_key('Shadow','16 cm')==('shadow','16')
    assert physical_key('Sonic e Shadow','',draft=True) is None
    assert physical_key('Sonic','12cm e 16cm',draft=True) is None
    assert physical_key('Unknown','',draft=True) is None

def test_merge_links_orders_and_preserves_cost_snapshots(erp):
    a=draft(erp,'Super Sonic','Anúncio A');b=draft(erp,'super sonic,super sonic','Anúncio B')
    erp.origin('Anúncio A','Super Sonic','001',a);erp.origin('Anúncio B','super sonic,super sonic','002',b)
    load(erp,[row('A',title='Anúncio A',sku='001'),row('B',title='Anúncio B',sku='002')])
    # Explicit links ensure these existing records belong to the selected catalog.
    with erp.s.transaction():
        erp.s.db.execute('UPDATE order_items SET product_id=? WHERE order_id=?',(a,'A'));erp.s.db.execute('UPDATE order_items SET product_id=? WHERE order_id=?',(b,'B'))
    before=erp.s.rows('SELECT id,cost_cents,cost_detail,cost_at,original_sku FROM order_items ORDER BY id')
    assert apply(erp,proposals(erp))==1
    assert erp.s.rows('SELECT id,cost_cents,cost_detail,cost_at,original_sku FROM order_items ORDER BY id')==before
    assert len({r['product_id'] for r in erp.s.rows('SELECT * FROM order_items')})==1
    assert not proposals(erp)

def test_sizes_never_merge_and_new_origins_reuse_physical_product(erp):
    for listing,var in [('A','Sonic'),('B','Sonic'),('C','Sonic 16cm'),('D','Shadow'),('E','Shadow 16cm')]:erp.origin(listing,var,listing,None)
    with erp.s.transaction():catalog_from_sales(erp)
    assert len(erp.s.rows('SELECT * FROM products WHERE archived=0'))==4
    origins=erp.s.rows('SELECT * FROM origins ORDER BY id');assert origins[0]['product_id']==origins[1]['product_id'] and origins[1]['product_id']!=origins[2]['product_id']

def test_conflicting_recipes_are_blocked(erp):
    a=draft(erp,'Shadow','A');b=draft(erp,'Shadow','B')
    erp.save_product({'name':'Shadow','model':'A','weight':'100','hours':'1','notes':'Identificado nas vendas.'},a)
    erp.save_product({'name':'Shadow','model':'B','weight':'200','hours':'2','notes':'Identificado nas vendas.'},b)
    rows=proposals(erp);assert len(rows)==1 and not rows[0]['safe'] and apply(erp,rows)==0


def test_explicit_aliases_and_ambiguous_ranges():
    assert physical_key('Amy Rose','',draft=True)==('amy','12')
    assert physical_key('Knukles - Echidna','',draft=True)==('knuckles','12')
    assert physical_key('Sonic - Hedgehogg','',draft=True)==('sonic','12')
    assert physical_key('Sonic 16,0cm','',draft=True)==('sonic','16')
    assert physical_key('Sonic 160mm','',draft=True)==('sonic','16')
    assert physical_key('Shadow','Bonecos 12/16cm',draft=True) is None
    assert physical_key('Shadow 16cm','Bonecos 12/16cm',draft=True)==('shadow','16')
