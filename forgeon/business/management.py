"""Simulações e conciliação gerencial; não acessa bancos ou contas externas."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import json
from .numbers import decimal,cents,day,quantity
from .pricing import calculate,round_cents
from ..importers.sheets import status_kind


def simulator(erp,pid,settings=None,packaging=None,other=None,filament_change='0'):
    original=erp.product(pid);colors=erp.colors(pid);config=erp.s.settings();base=calculate(original,colors,config)
    changed=dict(config);changed.update(settings or {})
    try:change=Decimal(str(filament_change).replace(',','.'))
    except Exception:raise ValueError('Variação do filamento inválida.') from None
    if not change.is_finite() or change< -100 or change>1000:raise ValueError('Variação do filamento deve ficar entre -100% e 1000%.')
    factor=1+change/100;product=dict(original)
    if packaging is not None:product['packaging_cents']=cents(packaging)
    if other is not None:product['other_cents']=cents(other)
    revised=[{**c,'kg_cents':int((Decimal(c['kg_cents'])*factor).quantize(Decimal('1'),rounding=ROUND_HALF_UP))} for c in colors]
    if not colors:changed['filament_kg']=str(decimal(changed['filament_kg'])*factor)
    scenario=calculate(product,revised,changed)
    sales=[r for r in erp.s.rows('SELECT i.qty,i.unit_cents,o.status FROM order_items i JOIN orders o ON o.id=i.order_id WHERE i.product_id=?',(pid,)) if status_kind(r['status'])!='cancelado']
    units=sum(r['qty'] for r in sales);avg=int((Decimal(sum(r['qty']*r['unit_cents'] for r in sales))/units).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if units else None
    at_average=None
    if avg is not None:
        profit=Decimal(avg)/100*(1-decimal(changed['fee_percent'])/100)-decimal(changed['fee_fixed'])-Decimal(scenario['total_cents'])/100
        at_average={'price_cents':avg,'profit_cents':round_cents(profit),'margin_percent':str(profit/(Decimal(avg)/100)*100) if avg else None}
    return {'base':base,'scenario':scenario,'difference_cents':scenario['suggested_cents']-base['suggested_cents'],'observed_units':units,'at_average':at_average,
            'profit_hour_cents':round_cents(Decimal(scenario['profit_cents'])/100/Decimal(scenario['hours'])) if Decimal(scenario['hours'])>0 else None}


def receipt_rows(erp,start=None,end=None):
    where=' WHERE r.date BETWEEN ? AND ?' if start and end else '';args=(day(start),day(end)) if where else ()
    rows=erp.s.rows('SELECT r.*,coalesce(sum(l.amount_cents),0) allocated_cents FROM settlements r LEFT JOIN settlement_links l ON l.settlement_id=r.id'+where+' GROUP BY r.id ORDER BY r.date DESC,r.id DESC',args)
    for r in rows:r['unallocated_cents']=r['amount_cents']-r['allocated_cents']
    return rows


def _save_receipt(s,when,amount,reference,note):
    if not reference.strip():raise ValueError('Informe referência única do repasse.')
    amount=cents(amount)
    if amount<=0:raise ValueError('Repasse recebido deve ser positivo.')
    existing=s.one('SELECT * FROM settlements WHERE reference=?',(reference.strip(),))
    if existing:
        allocated=s.one('SELECT coalesce(sum(amount_cents),0) n FROM settlement_links WHERE settlement_id=?',(existing['id'],))['n']
        if allocated>amount:raise ValueError('O novo valor é menor que os vínculos existentes. Corrija os vínculos antes.')
        s.db.execute('UPDATE settlements SET date=?,amount_cents=?,note=? WHERE id=?',(day(when),amount,note,existing['id']))
        return existing['id']
    return s.db.execute('INSERT INTO settlements(date,amount_cents,reference,note) VALUES(?,?,?,?)',(day(when),amount,reference.strip(),note)).lastrowid


def save_receipt(erp,when,amount,reference,note=''):
    with erp.s.transaction():
        rid=_save_receipt(erp.s,when,amount,reference,note);erp.s.log('repasse_recebido',{'id':rid,'reference':reference});return rid


def _link_receipt(s,rid,oid,amount):
    receipt=s.one('SELECT * FROM settlements WHERE id=?',(rid,))
    if not receipt or not s.one('SELECT id FROM orders WHERE id=?',(oid,)):raise ValueError('Repasse ou pedido não encontrado.')
    amount=cents(amount)
    if amount<=0:raise ValueError('Valor conciliado deve ser positivo.')
    other=s.one('SELECT coalesce(sum(amount_cents),0) n FROM settlement_links WHERE settlement_id=? AND order_id<>?',(rid,oid))['n']
    if other+amount>receipt['amount_cents']:raise ValueError('A soma dos vínculos ultrapassa o valor recebido.')
    s.db.execute('INSERT INTO settlement_links VALUES(?,?,?) ON CONFLICT(settlement_id,order_id) DO UPDATE SET amount_cents=excluded.amount_cents',(rid,oid,amount))


def link_receipt(erp,rid,oid,amount):
    with erp.s.transaction():_link_receipt(erp.s,rid,oid,amount);erp.s.log('conciliar_repasse',{'repasse':rid,'pedido':oid,'amount':str(amount)})


def unlink_receipt(erp,rid,oid):
    with erp.s.transaction():
        erp.s.db.execute('DELETE FROM settlement_links WHERE settlement_id=? AND order_id=?',(rid,oid));erp.s.log('desvincular_repasse',{'repasse':rid,'pedido':oid})


def reconciliation(erp,start,end):
    rows=erp.s.rows('SELECT o.id,o.date,o.status,o.gross_cents,o.fees_cents,o.refund_cents,coalesce(sum(l.amount_cents),0) received_cents FROM orders o LEFT JOIN settlement_links l ON l.order_id=o.id WHERE o.date BETWEEN ? AND ? GROUP BY o.id ORDER BY o.date,o.id',(day(start),day(end)))
    for r in rows:
        expected=0 if status_kind(r['status'])=='cancelado' else r['gross_cents']-r['fees_cents']-r['refund_cents']
        r['expected_cents']=expected;r['difference_cents']=r['received_cents']-expected
        r['reconciliation']='Conciliado (estimativa)' if abs(r['difference_cents'])<=1 else ('Sem recebimento vinculado' if not r['received_cents'] else 'Diferença a revisar')
    return rows


def prepare_receipts(rows):
    result=[]
    for index,row in enumerate(rows,2):
        reference=str(row.get('Referência') or '').strip()
        if not reference:raise ValueError(f'Linha {index}: referência do repasse obrigatória.')
        amount=cents(row.get('Valor recebido R$'))
        if amount<=0:raise ValueError('Repasse deve ser positivo.')
        oid=str(row.get('Pedido ID') or '').strip();linked=cents(row.get('Valor vinculado R$') or 0)
        if bool(oid)!=(linked>0):raise ValueError('Pedido e valor vinculado devem ser preenchidos juntos.')
        result.append({'date':day(row.get('Data')),'reference':reference,'amount_cents':amount,'order_id':oid,'linked_cents':linked})
    if not result:raise ValueError('Planilha sem repasses.')
    grouped={}
    for row in result:
        old=grouped.setdefault(row['reference'],row)
        if old['date']!=row['date'] or old['amount_cents']!=row['amount_cents']:raise ValueError('Repasse repetido com data ou total contraditório.')
    pairs=[(r['reference'],r['order_id']) for r in result if r['order_id']]
    if len(pairs)!=len(set(pairs)):raise ValueError('Mesmo pedido repetido no mesmo repasse. Agregue o vínculo antes de importar.')
    return result


def import_receipts(erp,rows):
    erp.s.backup()
    with erp.s.transaction():
        for r in rows:
            rid=_save_receipt(erp.s,r['date'],str(Decimal(r['amount_cents'])/100),r['reference'],'Importado de XLSX')
            if r['order_id']:_link_receipt(erp.s,rid,r['order_id'],str(Decimal(r['linked_cents'])/100))
        erp.s.log('importar_repasses',{'linhas':len(rows)})
    return len({r['reference'] for r in rows})


def product_performance(erp,start,end,status=''):
    from ..reports.finance import report
    rows=[]
    for p in erp.s.rows('SELECT id,name,model FROM products ORDER BY name'):
        r=report(erp,start,end,p['id'],status)
        units=sum(i['qty'] for i in r['usage_items'])
        if not units:continue
        contribution=r['gross_cents']-r['fees_cents']-r['refunds_cents']-r['production_cents']-r['losses_cents']
        hours=Decimal(r['usage_total_hours']);incomplete=any(i['partial'] for i in r['usage_items']) or any(o['partial'] for o in r['orders'])
        rows.append({'product_id':p['id'],'product':p['name']+' / '+p['model'],'qty':units,'gross_cents':r['gross_cents'],
                     'production_cents':r['production_cents'],'contribution_cents':contribution,'hours':str(hours),
                     'profit_hour_cents':int((Decimal(contribution)/hours).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if hours else None,'partial':incomplete})
    return sorted(rows,key=lambda r:(r['partial'],-r['contribution_cents']))
