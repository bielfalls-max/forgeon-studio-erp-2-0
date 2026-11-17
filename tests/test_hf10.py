from forgeon.business.unification import automatic_repair

def test_legacy_models_from_ads_and_missing_notes_are_repaired(erp):
    for name,listing in [('Amy','Boneco Metal Sonic 16cm'),('Amy Rose','Boneco Sonic'),('Metal Sonic','Boneco A'),('Metal Sonic','Boneco B'),('Metal Sonic','Boneco C'),('Metal Sonic','Boneco D')]:
        pid=erp.save_product({'name':name,'model':listing});erp.origin(listing,name,'',pid)
    assert automatic_repair(erp)==4
    active=erp.s.rows('SELECT name,model FROM products WHERE archived=0 ORDER BY name')
    assert active==[{'name':'Amy Rose','model':'12 cm'},{'name':'Metal Sonic','model':'12 cm'}]
    assert automatic_repair(erp)==0

def test_reopening_repairs_existing_duplicates_without_button(erp):
    from forgeon.business.service import ERP
    for listing in ('A','B'):
        pid=erp.save_product({'name':'Shadow','model':listing});erp.origin(listing,'Shadow','',pid)
    ERP(erp.s)
    assert len(erp.s.rows('SELECT * FROM products WHERE archived=0'))==1

def test_explicit_sizes_remain_separate_when_repair_is_automatic(erp):
    for name in ('Sonic','Sonic 16cm','Shadow','Shadow 16cm'):
        pid=erp.save_product({'name':name,'model':'Anúncio 16cm'});erp.origin('Anúncio 16cm',name,'',pid)
    automatic_repair(erp)
    rows=erp.s.rows('SELECT name,model FROM products WHERE archived=0 ORDER BY name,model')
    assert {(p['name'],p['model']) for p in rows}=={('Sonic','12 cm'),('Sonic','16 cm'),('Shadow','12 cm'),('Shadow','16 cm')}

def test_alias_sales_from_different_ads_share_recipe_and_consumption(erp):
    from test_orders import load,row
    from forgeon.reports.finance import report
    pid=erp.save_product({'name':'Amy Rose','model':'12 cm','weight':'25','hours':'2'})
    load(erp,[{**row('A',title='Anúncio Sonic'),'variation':'Amy'},{**row('B',title='Anúncio Metal Sonic'),'variation':'Amy Rose'}])
    assert {r['product_id'] for r in erp.s.rows('SELECT product_id FROM order_items')}=={pid}
    assert report(erp,'01/11/2026','30/11/2026')['usage_total_grams']=='50'

def test_product_screen_hides_listing_metadata(app,erp):
    from forgeon.ui.main import MainWindow
    for listing in ('Boneco Metal Sonic','Boneco Silver'):
        pid=erp.save_product({'name':'Metal Sonic','model':listing});erp.origin(listing,'Metal Sonic','',pid)
    w=MainWindow(erp);w.nav.setCurrentRow(1)
    assert w.products_table.rowCount()==1
    keys=[key for key,label in w.products_table._columns]
    assert 'skus' not in keys and 'origins_count' not in keys
    assert w.products_table.records[0]['model']=='12 cm'
    w.close()
