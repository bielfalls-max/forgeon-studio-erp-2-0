"""Cópia de consumo por unidade, independente da identidade do produto."""
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
import json
from .numbers import decimal,cents


def copy_colors(erp,pid):
    product=erp.product(pid)
    colors=[{'material':c['material'],'color':c['color'],'grams':c['grams'],'kg':str(Decimal(c['kg_cents'])/100)} for c in erp.colors(pid)]
    if not colors:raise ValueError('O produto de origem ainda não tem cores e gramas cadastradas.')
    return {'source_id':pid,'name':product['name'],'model':product['model'],'hours':product['hours'],'colors':colors}


def paste_colors(erp,target,payload,colors,copy_hours=False):
    product=erp.product(target)
    if product['archived']:raise ValueError('Escolha um produto ativo como destino.')
    if target==payload['source_id']:raise ValueError('Escolha outra variação como destino da cópia.')
    checked=[]
    for c in colors:
        material=str(c['material']).strip();color=str(c['color']).strip()
        if not material or not color:raise ValueError('Informe material e cor em todas as linhas.')
        grams=decimal(c['grams'],'Gramas por unidade')
        if grams:checked.append((material,color,grams,cents(c['kg'])))
    if not checked:raise ValueError('Informe consumo maior que zero em pelo menos uma cor.')
    hours=str(decimal(payload['hours'],'Horas')) if copy_hours else product['hours']
    s=erp.s;s.backup()
    with s.transaction():
        grouped=defaultdict(Decimal)
        for material,color,grams,kg in checked:
            # Uma referência já cadastrada mantém seu preço; não muda outros produtos.
            s.db.execute('INSERT INTO filaments(material,color,kg_cents) VALUES(?,?,?) ON CONFLICT(material,color) DO NOTHING',(material,color,kg))
            fid=s.one('SELECT id FROM filaments WHERE material=? AND color=?',(material,color))['id'];grouped[fid]+=grams
        s.db.execute('DELETE FROM product_colors WHERE product_id=?',(target,))
        s.db.executemany('INSERT INTO product_colors VALUES(?,?,?)',[(target,fid,str(g)) for fid,g in grouped.items()])
        s.db.execute('UPDATE products SET weight=?,hours=? WHERE id=?',(str(sum(grouped.values(),Decimal(0))),hours,target))
        previous=s.one('SELECT detail FROM product_slices WHERE product_id=?',(target,))
        detail=json.loads(previous['detail']) if previous else {}
        detail['colors_copied_from']={'id':payload['source_id'],'name':payload['name'],'model':payload['model'],'hours':copy_hours}
        s.db.execute('INSERT INTO product_slices VALUES(?,?,?) ON CONFLICT(product_id) DO UPDATE SET detail=excluded.detail,recorded=excluded.recorded',
                     (target,json.dumps(detail,ensure_ascii=False),datetime.now().isoformat(timespec='seconds')))
        from .revisions import record_revision
        record_revision(erp,target,'Cores e gramas adaptadas de '+payload['name'])
        s.log('colar_cores',{'origem':payload['source_id'],'destino':target,'copiou_tempo':copy_hours})
    from .production import resolve_known_products
    return resolve_known_products(erp)
