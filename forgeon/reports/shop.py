"""Comparação de fontes: dados gerenciais não entram na receita operacional."""
from datetime import date,timedelta
import json
from ..business.numbers import day
from ..importers.sheets import status_kind
from ..importers.automatic import BASIS_LABELS


def covered(s,start,end):
    cursor=date.fromisoformat(start);finish=date.fromisoformat(end)
    for row in s.rows("SELECT start,end FROM order_coverage WHERE kind='all' AND end>=? AND start<=? ORDER BY start,end",(start,end)):
        first,last=date.fromisoformat(row['start']),date.fromisoformat(row['end'])
        if first>cursor:return False
        if last>=cursor:cursor=last+timedelta(days=1)
        if cursor>finish:return True
    return False


def canonical(s,start,end):
    rows=s.rows('SELECT * FROM shop_metrics WHERE start<=? AND end>=? ORDER BY basis,start,grain',(end,start))
    chosen=[]
    for row in rows:
        if row['grain']=='period' and any(r['basis']==row['basis'] and r['grain']!='period' and r['start']<=row['end'] and r['end']>=row['start'] for r in rows):continue
        if row['grain']=='day' and any(r['basis']==row['basis'] and r['grain']=='month' and r['start']<=row['start']<=r['end'] and start<=r['start'] and r['end']<=end for r in rows):continue
        if row['grain']=='month' and not(start<=row['start'] and row['end']<=end) and any(r['basis']==row['basis'] and r['grain']=='day' and row['start']<=r['start']<=row['end'] for r in rows):continue
        if row['grain']=='period' and any(r['basis']==row['basis'] and r['grain']=='period' and r['start']>=row['start'] and r['end']<=row['end'] and (r['start'],r['end'])!=(row['start'],row['end']) for r in rows):continue
        chosen.append(row)
    nonoverlap=[]
    for row in sorted(chosen,key=lambda r:(r['basis'],not(start<=r['start'] and r['end']<=end),{'day':0,'month':1,'period':2}[r['grain']],r['start'],r['end'])):
        if not any(r['basis']==row['basis'] and r['start']<=row['end'] and r['end']>=row['start'] for r in nonoverlap):nonoverlap.append(row)
    return sorted(nonoverlap,key=lambda r:(r['start'],r['basis']))


def comparison(erp,start,end):
    start,end=day(start),day(end);s=erp.s;result=[]
    rows=canonical(s,start,end)
    if not rows:return []
    orders=s.rows('SELECT o.*,f.detail financial_detail FROM orders o LEFT JOIN order_financials f ON f.order_id=o.id')
    for order in orders:order['financial']=json.loads(order['financial_detail'] or '{}')
    for row in rows:
        detail=json.loads(row['detail']);aligned=start<=row['start'] and row['end']<=end
        selected=[];estimated=False
        for order in orders:
            financial=order['financial'];date_value=financial.get('paid_date') if row['basis']=='produto_pago' else order['date']
            if date_value and row['start']<=date_value<=row['end']:
                selected.append(order);estimated|='items_cents' not in financial
        raw=sum(o['financial'].get('items_cents',o['gross_cents'])-o['financial'].get('seller_discount_cents',0) for o in selected)
        count=len(selected);full=covered(s,row['start'],row['end']) and row['basis']=='pedido_feito' and aligned and not estimated
        difference=raw-detail['revenue_cents'] if aligned and selected else None
        if not aligned:state='Período do resumo cruza o filtro; não rateado'
        elif not selected:state='Sem pedidos detalhados deste período'
        elif raw==detail['revenue_cents'] and count==detail['orders_count']:state='Valores conferem' if full else 'Valores conferem na amostra; revisar cobertura'
        else:state='Diferença a revisar; não altera vendas'
        result.append({**detail,'basis':BASIS_LABELS[row['basis']],'basis_key':row['basis'],'start':row['start'],'end':row['end'],'grain':row['grain'],
            'detail_orders':count if aligned and selected else None,'detail_cents':raw if aligned and selected else None,'comparison_cents':difference,
            'coverage':'Order.all cobre a criação no intervalo' if full else ('Por pagamento; pode faltar pedido criado fora do intervalo' if row['basis']=='produto_pago' else 'Cobertura detalhada incompleta/desconhecida'),
            'state':state,'aligned':aligned})
    return result


def totals(rows):
    result=[]
    for basis in ('pedido_feito','produto_pago'):
        aligned=[r for r in rows if r['basis_key']==basis and r['aligned']]
        if aligned:result.append({'basis':BASIS_LABELS[basis],'start':min(r['start'] for r in aligned),'end':max(r['end'] for r in aligned),
            'revenue_cents':sum(r['revenue_cents'] for r in aligned),'orders_count':sum(r['orders_count'] for r in aligned),'periods':len(aligned)})
    return result


def reconciled(rows,start,end):
    cursor=date.fromisoformat(start);finish=date.fromisoformat(end)
    made=sorted((r for r in rows if r['basis_key']=='pedido_feito' and r['aligned']),key=lambda r:r['start'])
    for row in made:
        if row['state']!='Valores conferem' or date.fromisoformat(row['start'])>cursor:return False
        cursor=max(cursor,date.fromisoformat(row['end'])+timedelta(days=1))
    return cursor>finish
