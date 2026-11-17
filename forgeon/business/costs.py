"""Referências editáveis e preços pagos; nenhum preço de mercado é presumido."""
from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP
import json
from .organization import preference

def stamp(s,key,detail):
    value={'reviewed':datetime.now().astimezone().isoformat(timespec='seconds'),**detail}
    s.db.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))

def material_costs(erp):
    result=[]
    for filament in erp.s.rows('SELECT * FROM filaments ORDER BY material,color'):
        purchase=erp.s.one('SELECT * FROM purchases WHERE filament_id=? ORDER BY date DESC,id DESC LIMIT 1',(filament['id'],))
        reference=preference(erp.s,'cost:filament:'+str(filament['id']),{})
        result.append({**filament,'reviewed':reference.get('reviewed') or 'Referência não revisada nesta versão',
            'purchase_date':purchase['date'] if purchase else None,'purchase_id':purchase['id'] if purchase else None,
            'purchase_kg_cents':int((Decimal(purchase['amount_cents']+purchase['freight_cents'])*1000/Decimal(purchase['grams'])).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if purchase else None})
    return result

def use_purchase(erp,fid,purchase_id):
    purchase=erp.s.one('SELECT * FROM purchases WHERE id=? AND filament_id=?',(purchase_id,fid))
    if not purchase:raise ValueError('Compra do filamento não encontrada.')
    price=int((Decimal(purchase['amount_cents']+purchase['freight_cents'])*1000/Decimal(purchase['grams'])).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    erp.s.backup()
    with erp.s.transaction():
        erp.s.db.execute('UPDATE filaments SET kg_cents=? WHERE id=?',(price,fid))
        stamp(erp.s,'cost:filament:'+str(fid),{'source':'Compra confirmada','purchase_id':purchase_id,'kg_cents':price})
        erp.s.log('preco_por_compra',{'filamento':fid,'compra':purchase_id,'kg_cents':price})
    return price
