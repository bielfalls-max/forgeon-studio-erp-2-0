"""Produto físico por nome/variante e tamanho; anúncios não definem a identidade."""
import re,json
from datetime import datetime
from decimal import Decimal
from .numbers import norm
from .production import identity

CHARACTERS={'sonic','shadow','silver','tails','knuckles','amy','rouge','blaze','cream','metal sonic','super sonic','super shadow','super silver','mephiles','eggman'}

def physical_key(name,model='',*,draft=False):
    value=identity(name);value=re.sub(r'[_.]+',' ',value);value=re.sub(r'\s+',' ',value).strip()
    value=re.sub(r'(?<=\d),(?=\d)','.',value)
    chunks=[v.strip() for v in value.split(',')]
    if len(chunks)>1:
        if len(set(chunks))!=1:return None
        value=chunks[0]
    sizes=re.findall(r'(?<!\d)(\d+(?:[.,]\d+)?)\s*(cm|mm|centimetros?)(?!\w)',value)
    model_text=norm(model)
    # Um anúncio pode ter vários personagens, mas o tamanho do anúncio só é usado
    # quando não contradiz o tamanho explicitamente informado na variação.
    size_text=value if sizes else model_text
    if re.search(r'\d+\s*(?:/|a|ate|-)\s*\d+\s*(?:cm|mm)',size_text):return None
    if not sizes:sizes=re.findall(r'(?<!\d)(\d+(?:[.,]\d+)?)\s*(cm|mm|centimetros?)(?!\w)',model_text)
    sizes={format((Decimal(n.replace(',','.'))/(10 if unit=='mm' else 1)).normalize(),'f') for n,unit in sizes}
    if len(sizes)>1:return None
    if draft and not re.search(r'\d\s*(?:cm|mm|centimetros?)',value) and sizes and not re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*(?:cm|mm)\s*',model_text) and sizes!={'12'}:return None
    clean=re.sub(r'(?<!\d)\d+(?:[.,]\d+)?\s*(?:cm|mm|centimetros?)(?!\w)','',value).strip(' -–()')
    clean=re.sub(r'\s+',' ',clean)
    # Nomes desconhecidos não recebem tamanho ou equivalência presumida.
    clean=re.sub(r'\s*-?\s*hedgehogg?\s*$','',clean).strip()
    aliases={'amy rose':'amy','knukles echidna':'knuckles','knukles - echidna':'knuckles','knuckles - echidna':'knuckles','kuckles':'knuckles','knukles':'knuckles'}
    clean=aliases.get(clean,clean)
    compact=re.sub(r'[\s-]','',clean)
    canonical=next((c for c in CHARACTERS if c.replace(' ','')==compact),None)
    if not canonical:return None
    size=next(iter(sizes),'12')
    if not draft and model_text and not re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*cm\s*',model_text):return None
    return canonical,size

def is_draft(product):return product.get('notes','').startswith('Identificado nas vendas.')

def key_string(key):return json.dumps(key,ensure_ascii=False)

def lookup(erp,listing,variation):
    if not variation.strip():return None
    key=physical_key(variation,'',draft=True)
    if not key:return None
    row=erp.s.one('SELECT p.* FROM product_identities i JOIN products p ON p.id=i.product_id WHERE i.identity_key=? AND p.archived=0',(key_string(key),))
    if row and product_key(erp,row)==key:return row['id']
    candidates=[]
    for product in erp.s.rows('SELECT * FROM products WHERE archived=0'):
        k=product_key(erp,product)
        if k==key:candidates.append(product['id'])
    return candidates[0] if len(candidates)==1 else None

def fingerprint(s,p):
    colors=s.rows('SELECT filament_id,grams FROM product_colors WHERE product_id=? ORDER BY filament_id',(p['id'],))
    supplies=s.rows('SELECT supply_id,quantity FROM product_supplies WHERE product_id=? ORDER BY supply_id',(p['id'],))
    meaningful=bool(colors or supplies or any(Decimal(str(p[k] or 0)) for k in ('weight','hours','manual_cents','packaging_cents','other_cents')))
    def n(v):return str(Decimal(str(v or 0)).normalize())
    signature=tuple(n(p[k]) for k in ('weight','hours','packaging_cents','other_cents'))+(None if p['manual_cents'] is None else p['manual_cents'],json.dumps([(c['filament_id'],n(c['grams'])) for c in colors]),json.dumps([(c['supply_id'],n(c['quantity'])) for c in supplies]))
    return meaningful,signature

def proposals(erp):
    groups={};result=[]
    for p in erp.s.rows('SELECT * FROM products WHERE archived=0 ORDER BY id'):
        key=product_key(erp,p)
        if key:groups.setdefault(key,[]).append(p)
    for key,products in groups.items():
        if len(products)<2:continue
        known=[p for p in products if fingerprint(erp.s,p)[0]]
        signatures={fingerprint(erp.s,p)[1] for p in known}
        target=(known or products)[0]
        result.append({'key':key_string(key),'name':display_name(key[0]),'size':key[1]+' cm','target':target['id'],'sources':[p['id'] for p in products if p['id']!=target['id']],
            'count':len(products),'status':'Revisar receitas/custos diferentes' if len(signatures)>1 else 'Pode unificar','safe':len(signatures)<=1})
    return result

def apply(erp,rows):
    rows=[r for r in rows if r['safe']]
    if not rows:return 0
    s=erp.s;s.backup();count=0
    with s.transaction():
        valid={r['key']:r for r in proposals(erp)}
        for requested in rows:
            row=valid.get(requested['key'])
            if not row or not row['safe'] or row['target']!=requested['target'] or row['sources']!=requested['sources']:raise ValueError('O catálogo mudou; atualize a revisão antes de unificar.')
            target=row['target'];key=json.loads(row['key'])
            for source in row['sources']:
                s.db.execute('UPDATE product_merges SET target_id=? WHERE target_id=?',(target,source))
                for table in ('origins','order_items','production_jobs'):s.db.execute('UPDATE '+table+' SET product_id=? WHERE product_id=?',(target,source))
                s.db.execute('UPDATE products SET archived=1 WHERE id=?',(source,))
                s.db.execute('INSERT INTO product_merges VALUES(?,?,?,?)',(source,target,datetime.now().isoformat(timespec='seconds'),json.dumps({'identity':key})))
                count+=1
            # Receita e revisões originais ficam preservadas; target é o cadastro com dados.
            s.db.execute('UPDATE products SET name=?,model=? WHERE id=?',(display_name(key[0]),key[1]+' cm',target))
            s.db.execute('INSERT INTO product_identities VALUES(?,?) ON CONFLICT(identity_key) DO UPDATE SET product_id=excluded.product_id',(row['key'],target))
            s.log('unificar_produtos',row)
    return count


def product_key(erp,product):
    model=product['model']
    from_sales=is_draft(product) or bool(erp.s.one('SELECT id FROM origins WHERE product_id=? AND listing=?',(product['id'],model)))
    # Título do anúncio não é modelo físico, nem prova a medida de uma variação.
    if from_sales and not re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*(?:cm|mm)\s*',norm(model)):model=''
    return physical_key(product['name'],model,draft=from_sales)


def automatic_repair(erp):
    rows=proposals(erp)
    count=apply(erp,rows)
    # Normaliza também os grupos com um cadastro, sem alterar grupos conflitantes.
    groups={}
    for p in erp.s.rows('SELECT * FROM products WHERE archived=0'):
        key=product_key(erp,p)
        if key:groups.setdefault(key,[]).append(p)
    changes=[(key,ps[0]) for key,ps in groups.items() if len(ps)==1 and (ps[0]['name']!=display_name(key[0]) or ps[0]['model']!=key[1]+' cm')]
    if changes:
        if not count:erp.s.backup()
        with erp.s.transaction():
            for key,p in changes:
                erp.s.db.execute('UPDATE products SET name=?,model=? WHERE id=?',(display_name(key[0]),key[1]+' cm',p['id']))
                erp.s.db.execute('INSERT INTO product_identities VALUES(?,?) ON CONFLICT(identity_key) DO UPDATE SET product_id=excluded.product_id',(key_string(key),p['id']))
            erp.s.log('normalizar_catalogo_fisico',{'produtos':len(changes)})
    if count:erp.resolve_known_products()
    return count


def display_name(name):return 'Amy Rose' if name=='amy' else name.title()
