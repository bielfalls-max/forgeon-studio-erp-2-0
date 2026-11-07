"""Cadastro de receitas e ligação conservadora entre variação e produto físico."""
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
import json,re
from .numbers import norm,decimal,cents,quantity


def identity(value):
    text=re.sub(r'([a-z])([A-Z])',r'\1 \2',str(value))
    text=norm(text).replace('_',' ')
    text=re.sub(r'\s*[-–—]\s*hedgehog\s*$','',text)
    parts=[part.strip() for part in text.split(',')]
    if len(parts)>1 and len(set(parts))==1:text=parts[0]
    return ' '.join(text.split())


def match_product(erp,listing,variation):
    # A marketplace listing title may contain a different character from its variation.
    # Never use the parent SKU, a substring or a fuzzy name to hide that difference.
    key=identity(variation or listing)
    candidates=[]
    products=erp.s.rows('SELECT * FROM products WHERE archived=0')
    plain=[p for p in products if identity(p['name'])==key]
    if len(plain)>1 and any(p['model'].strip() for p in plain):return None
    for p in products:
        name=identity(p['name'])
        expected=identity(p['name']+' '+p['model']) if p['model'].strip() else name
        if key==expected:candidates.append(p['id'])
    return candidates[0] if len(candidates)==1 else None


def store_item_snapshot(erp,item,freeze_cost=True):
    s=erp.s
    if not item['product_id']:return False
    calc=erp.cost(item['product_id']);now=datetime.now().isoformat(timespec='seconds')
    previous=s.one('SELECT * FROM item_usage WHERE item_id=?',(item['id'],))
    if previous and item['cost_cents'] is None and json.loads(previous['detail']).get('missing') and not calc['missing']:
        s.db.execute('UPDATE item_usage SET detail=?,recorded=? WHERE item_id=?',(json.dumps(calc,ensure_ascii=False),now,item['id']))
    if not previous:
        original=item.get('cost_detail')
        data=original or json.dumps(calc,ensure_ascii=False)
        if original or decimal(calc['grams'])>0 or decimal(calc['hours'])>0:
            s.db.execute('INSERT INTO item_usage VALUES(?,?,?)',(item['id'],data,item.get('cost_at') or now))
    if freeze_cost and item['cost_cents'] is None and not calc['missing']:
        s.db.execute('UPDATE order_items SET cost_cents=?,cost_detail=?,cost_at=? WHERE id=?',(calc['total_cents'],json.dumps(calc,ensure_ascii=False),now,item['id']))
        return True
    return False


def resolve_known_products(erp):
    s=erp.s;linked=frozen=0
    with s.transaction():
        for origin in s.rows('SELECT * FROM origins WHERE active=1 AND product_id IS NULL'):
            pid=match_product(erp,origin['listing'],origin['variation'])
            if pid is None:continue
            s.db.execute('UPDATE origins SET product_id=? WHERE id=?',(pid,origin['id']))
            s.db.execute('UPDATE order_items SET product_id=? WHERE origin_id=? AND product_id IS NULL',(pid,origin['id']))
            linked+=1
        for item in s.rows('SELECT * FROM order_items WHERE product_id IS NOT NULL'):
            frozen+=int(store_item_snapshot(erp,item))
        s.log('resolver_cadastros',{'origens':linked,'custos_preenchidos_agora':frozen})
    return linked,frozen


def save_sliced_product(erp,name,model,recipe,colors,packaging='0',other='0',pid=None):
    if not name.strip():raise ValueError('Informe o nome físico do produto.')
    grams=sum((decimal(c['grams'],'Gramas') for c in colors),Decimal(0))
    if not colors or grams<=0:raise ValueError('O arquivo não informou consumo compatível por cor. Preencha manualmente sem inventar gramas.')
    hours=decimal(recipe['hours']) if recipe['hours'] is not None else None
    packaging,other=cents(packaging),cents(other)
    checked=[]
    for color in colors:
        material=str(color['material']).strip();label=str(color['color']).strip()
        if not material or not label:raise ValueError('Informe material e nome de cada cor.')
        checked.append((material,label,cents(color['kg']),str(decimal(color['grams']))))
    s=erp.s;s.backup()
    with s.transaction():
        if pid:
            previous=erp.product(pid)
            s.db.execute('UPDATE products SET name=?,model=?,weight=?,hours=?,packaging_cents=?,other_cents=? WHERE id=?',
                         (name.strip(),model.strip(),str(grams),str(hours) if hours is not None else previous['hours'],packaging,other,pid))
            s.db.execute('DELETE FROM product_colors WHERE product_id=?',(pid,))
        else:
            pid=s.db.execute('INSERT INTO products(name,model,weight,hours,packaging_cents,other_cents) VALUES(?,?,?,?,?,?)',
                            (name.strip(),model.strip(),str(grams),str(hours or 0),packaging,other)).lastrowid
        grouped=defaultdict(Decimal)
        for material,label,kg,g in checked:
            s.db.execute('INSERT INTO filaments(material,color,kg_cents) VALUES(?,?,?) ON CONFLICT(material,color) DO UPDATE SET kg_cents=excluded.kg_cents',(material,label,kg))
            fid=s.one('SELECT id FROM filaments WHERE material=? AND color=?',(material,label))['id'];grouped[fid]+=decimal(g)
        s.db.executemany('INSERT INTO product_colors VALUES(?,?,?)',[(pid,fid,str(g)) for fid,g in grouped.items()])
        detail={key:recipe.get(key) for key in ('name','hours','plates','units','source_name','warnings')}
        s.db.execute('INSERT INTO product_slices VALUES(?,?,?) ON CONFLICT(product_id) DO UPDATE SET detail=excluded.detail,recorded=excluded.recorded',
                     (pid,json.dumps(detail,ensure_ascii=False),datetime.now().isoformat(timespec='seconds')))
        s.log('produto_do_fatiador',{'produto':pid,'placas':recipe.get('plates',[]),'unidades_completas':recipe.get('units',1)})
    linked,frozen=resolve_known_products(erp)
    return pid,linked,frozen
