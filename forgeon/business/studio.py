"""Insumos e cadastros derivados de origens; referências não inventam receitas."""
from decimal import Decimal,ROUND_HALF_UP
from .numbers import decimal,cents,day,norm

def catalog_from_sales(erp):
    s=erp.s;count=0
    for origin in s.rows('SELECT * FROM origins WHERE active=1 AND product_id IS NULL'):
        pid=erp.match_product(origin['listing'],origin['variation'])
        if not pid:
            name=origin['variation'].strip() or origin['listing'].strip()
            # Identidade conservadora: anúncio + variação; SKU isolado não funde produtos.
            existing=s.one('SELECT id FROM products WHERE name=? AND model=?',(name,origin['listing']))
            pid=existing['id'] if existing else s.db.execute('INSERT INTO products(name,model,notes) VALUES(?,?,?)',(name,origin['listing'],'Identificado nas vendas. Vincule 3MF/G-code e revise custos antes de precificar.')).lastrowid
            count+=not bool(existing)
        s.db.execute('UPDATE origins SET product_id=? WHERE id=?',(pid,origin['id']))
        s.db.execute('UPDATE order_items SET product_id=? WHERE origin_id=? AND product_id IS NULL',(pid,origin['id']))
    if count:s.log('cadastros_das_vendas',{'produtos':count})
    return count

def buy(erp,name,category,unit,quantity,amount,freight,when):
    q=decimal(quantity)
    if q<=0 or not name.strip():raise ValueError('Informe o nome e quantidade positiva.')
    total=cents(amount);shipping=cents(freight)
    if category=='Ferramentas':
        erp.expense(when,'Ferramentas',f'{name.strip()} · {q} {unit} · frete incluído',str(Decimal(total+shipping)/100))
        return None
    price=str(Decimal(total+shipping)/q)
    with erp.s.transaction():
        old=erp.s.one('SELECT * FROM supplies WHERE name=?',(name.strip(),))
        if old and old['unit']!=unit:raise ValueError('Unidade diferente do cadastro existente; use outro nome para outra unidade.')
        erp.s.db.execute('INSERT INTO supplies(name,category,unit,unit_cents) VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET category=excluded.category',(name.strip(),category,unit,price))
        sid=erp.s.one('SELECT id FROM supplies WHERE name=?',(name.strip(),))['id']
        erp.s.db.execute('INSERT INTO supply_purchases(supply_id,date,quantity,amount_cents,freight_cents) VALUES(?,?,?,?,?)',(sid,day(when),str(q),total,shipping))
        latest=erp.s.one('SELECT * FROM supply_purchases WHERE supply_id=? ORDER BY date DESC,id DESC',(sid,))
        erp.s.db.execute('UPDATE supplies SET unit_cents=? WHERE id=?',(str(Decimal(latest['amount_cents']+latest['freight_cents'])/Decimal(latest['quantity'])),sid))
        erp.s.log('compra_insumo',{'insumo':sid,'valor_cents':total+shipping})
    return sid

def assign(erp,pid,sid,quantity):
    q=decimal(quantity);erp.product(pid)
    if not erp.s.one('SELECT id FROM supplies WHERE id=?',(sid,)):raise ValueError('Insumo não encontrado.')
    with erp.s.transaction():
        if q:erp.s.db.execute('INSERT INTO product_supplies VALUES(?,?,?) ON CONFLICT(product_id,supply_id) DO UPDATE SET quantity=excluded.quantity',(pid,sid,str(q)))
        else:erp.s.db.execute('DELETE FROM product_supplies WHERE product_id=? AND supply_id=?',(pid,sid))
        from .revisions import record_revision
        record_revision(erp,pid,'Consumo de insumo/embalagem por unidade')
        erp.s.log('insumo_produto',{'produto':pid,'insumo':sid,'quantidade':str(q)})

def product_extra(s,pid):
    return int(sum((Decimal(r['quantity'])*Decimal(r['unit_cents']) for r in s.rows('SELECT p.quantity,s.unit_cents FROM product_supplies p JOIN supplies s ON s.id=p.supply_id WHERE p.product_id=?',(pid,))),Decimal(0)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def needs(erp):
    result=[]
    for s in erp.s.rows('SELECT * FROM supplies ORDER BY name'):
        purchased=sum((Decimal(p['quantity']) for p in erp.s.rows('SELECT quantity FROM supply_purchases WHERE supply_id=?',(s['id'],))),Decimal(0));used=Decimal(0);open_need=Decimal(0)
        for row in erp.s.rows('SELECT i.qty,o.status,p.quantity FROM order_items i JOIN orders o ON o.id=i.order_id JOIN product_supplies p ON p.product_id=i.product_id WHERE p.supply_id=?',(s['id'],)):
            from ..importers.sheets import status_kind
            if status_kind(row['status'])=='cancelado':continue
            mass=Decimal(row['quantity'])*row['qty']
            if any(v in norm(row['status']) for v in ('enviar','to ship','process')):open_need+=mass
            else:used+=mass
        balance=purchased-used
        result.append({**s,'unit_price':f"R$ {Decimal(s['unit_cents'])/100:.4f}/{s['unit']}",'purchased':str(purchased),'estimated_used':str(used),'balance':str(balance),'needed':str(open_need),'buy':str(max(Decimal(0),open_need-balance))})
    return result

def filament_needs(erp):
    import json
    from ..importers.sheets import status_kind
    demand={};used={};unknown=0
    for item in erp.s.rows('SELECT i.*,o.status,u.detail usage_detail FROM order_items i JOIN orders o ON o.id=i.order_id LEFT JOIN item_usage u ON u.item_id=i.id'):
        if status_kind(item['status'])=='cancelado':continue
        recipe=json.loads(item['usage_detail'] or item['cost_detail'] or '{}')
        if not recipe.get('colors') and item['product_id']:recipe=erp.cost(item['product_id'])
        if not recipe.get('colors'):unknown+=item['qty'];continue
        target=demand if any(w in norm(item['status']) for w in ('enviar','to ship','process')) else used
        for color in recipe['colors']:target[color['filament_id']]=target.get(color['filament_id'],Decimal(0))+Decimal(color['grams'])*item['qty']
    result=[]
    for f in erp.s.rows('SELECT * FROM filaments ORDER BY material,color'):
        bought=sum((Decimal(r['grams']) for r in erp.s.rows('SELECT grams FROM purchases WHERE filament_id=?',(f['id'],))),Decimal(0));balance=bought-used.get(f['id'],Decimal(0));need=demand.get(f['id'],Decimal(0))
        result.append({**f,'balance':str(balance),'needed':str(need),'buy':str(max(Decimal(0),need-balance))})
    return result,unknown
