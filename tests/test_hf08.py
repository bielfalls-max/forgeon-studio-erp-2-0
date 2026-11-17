from decimal import Decimal
from forgeon.business import studio
from forgeon.reports.finance import report
from forgeon.importers.automatic import inspect_file,commit_plans
from test_hf07 import make_orders

def test_import_populates_products_but_no_fake_recipe(erp,tmp_path):
    plan=inspect_file(make_orders(tmp_path));commit_plans(erp,[plan]);first=erp.s.rows('SELECT * FROM products');assert first and all(p['weight']=='0' for p in first)
    assert all(i['product_id'] for i in erp.s.rows('SELECT * FROM order_items'))
    commit_plans(erp,[plan]);assert erp.s.rows('SELECT * FROM products')==first
    assert report(erp,'01/10/2026','31/10/2026')['production_pending']

def test_supply_purchase_cash_and_consumption_are_not_double_cost(erp,product):
    sid=studio.buy(erp,'Caixa','Embalagem','un','10','20','5','06/11/2026')
    before=erp.cost(product)['total_cents'];studio.assign(erp,product,sid,'1');assert erp.cost(product)['total_cents']==before+250
    r=report(erp,'01/11/2026','30/11/2026');assert r['supplies_cents']==2500 and r['cash_cents']==-2500 and r['operating_cents']==0
    assert report(erp,'01/10/2026','31/10/2026')['purchases_cents']==0

def test_supply_history_and_usage_after_price_changes(erp,product):
    sid=studio.buy(erp,'Cola','Acabamento','g','100','10','0','01/11/2026');studio.assign(erp,product,sid,'2')
    from test_orders import load,row
    erp.origin('Sonic','10 cm','00001',product);load(erp,[row(status='A Enviar')]);old=erp.s.one('SELECT cost_cents FROM order_items')['cost_cents']
    studio.buy(erp,'Cola','Acabamento','g','100','20','0','10/11/2026');assert erp.s.one('SELECT cost_cents FROM order_items')['cost_cents']==old
    need=studio.needs(erp)[0];assert need['needed']=='2' and need['buy']=='0'


def test_fractional_cent_material_cost_is_not_rounded_before_usage(erp,product):
    sid=studio.buy(erp,'Cola fina','Acabamento','g','1000','5','0','01/11/2026');base=erp.cost(product)['total_cents'];studio.assign(erp,product,sid,'10')
    assert erp.cost(product)['total_cents']==base+5


def test_durable_tool_purchase_is_one_expense_in_month_with_freight(erp):
    studio.buy(erp,'Alicate','Ferramentas','un','1','30','5','05/11/2026');r=report(erp,'01/11/2026','30/11/2026')
    assert r['expenses_cents']==3500 and r['operating_cents']==-3500 and r['cash_cents']==-3500 and r['purchases_cents']==0
