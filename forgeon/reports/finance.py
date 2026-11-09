from collections import defaultdict
from decimal import Decimal
import json
from ..business.numbers import day,norm
from ..importers.sheets import status_kind


def rounded_money(n):
    from decimal import ROUND_HALF_UP
    return int(Decimal(n).quantize(Decimal('1'),rounding=ROUND_HALF_UP))


def report(erp, start, end, product_id=None, status='', filters=None):
    start, end = day(start), day(end)
    if end < start:
        raise ValueError('Período inválido.')
    filters=filters or {}
    narrowed=product_id is not None or any(filters.get(k) for k in ('sku','variation','material','color','coverage'))
    def matches(i):
        if product_id is not None and i['product_id']!=product_id:return False
        if filters.get('sku') and norm(filters['sku']) not in norm(i['original_sku']):return False
        if filters.get('variation') and norm(filters['variation']) not in norm(i['variation']):return False
        d=json.loads(i.get('usage_detail') or i.get('cost_detail') or '{}')
        colors=d.get('colors',[])
        if filters.get('material') and not any(norm(filters['material']) in norm(c['material']) for c in colors):return False
        if filters.get('color') and not any(norm(filters['color']) in norm(c['color']) for c in colors):return False
        complete=i['product_id'] is not None and i['cost_cents'] is not None and Decimal(d.get('grams','0'))>0 and Decimal(d.get('hours','0'))>0
        if filters.get('coverage')=='completos' and not complete:return False
        if filters.get('coverage')=='pendentes' and complete:return False
        return True
    s = erp.s
    orders = s.rows('SELECT o.*,f.detail financial_detail FROM orders o LEFT JOIN order_financials f ON f.order_id=o.id WHERE date BETWEEN ? AND ? ORDER BY date,id',(start,end))
    gross = fees = refunds = production = 0
    pending = 0
    partial = False
    selected = []
    sold = defaultdict(lambda: {'qty':0,'revenue_cents':0})
    consumption = defaultdict(Decimal)
    daily = defaultdict(Decimal)
    usage_orders=[];usage_items=[];financial_rows=[]
    total_grams=Decimal(0);total_hours=Decimal(0);planned_grams=Decimal(0);sent_grams=Decimal(0);unknown_units=0;unknown_time_units=0
    for o in orders:
        if status:
            if status.startswith('texto:'):
                if norm(o['status'])!=norm(status[6:]):continue
            elif status_kind(o['status'])!=status:continue
        items = s.rows('SELECT i.*,p.name product_name,u.detail usage_detail,u.recorded usage_at FROM order_items i LEFT JOIN products p ON p.id=i.product_id LEFT JOIN item_usage u ON u.item_id=i.id WHERE order_id=?',(o['id'],))
        picked = [i for i in items if matches(i)]
        if not picked:
            continue
        selected.append(o)
        # Product filters allocate order totals by item sale value; sum of all shares is exact before rounding.
        basis = sum(i['qty']*i['unit_cents'] for i in items)
        share = Decimal(sum(i['qty']*i['unit_cents'] for i in picked)) / basis if narrowed and basis else Decimal(1)
        if narrowed and not basis:
            partial = True
        partial |= bool(o['partial'])
        kind = status_kind(o['status'])
        if kind == 'cancelado':
            continue  # costs for failed production must be entered as an expense
        gross += Decimal(o['gross_cents']) * share
        daily[o['date']] += Decimal(o['gross_cents']) * share
        fees += Decimal(o['fees_cents']) * share
        refunds += Decimal(o['refund_cents']) * share
        if kind == 'devolucao' and o['refund_cents'] == 0:
            partial = True
        financial=json.loads(o.get('financial_detail') or '{}')
        if financial.get('returned_qty') or financial.get('return_status'):partial=True
        financial_rows.append({'id':o['id'],'date':o['date'],'status':o['status'],'gross_cents':rounded_money(Decimal(o['gross_cents'])*share),
            'commission_cents':rounded_money(Decimal(financial.get('commission_cents',0))*share),'service_cents':rounded_money(Decimal(financial.get('service_cents',0))*share),
            'transaction_cents':rounded_money(Decimal(financial.get('transaction_cents',0))*share),'fees_cents':rounded_money(Decimal(o['fees_cents'])*share),
            'net_cents':rounded_money(Decimal(o['gross_cents']-o['fees_cents']-o['refund_cents'])*share),
            'buyer_shipping_cents':financial.get('buyer_shipping_cents'), 'buyer_total_cents':financial.get('buyer_total_cents'),'market_total_cents':financial.get('market_total_cents')})
        order_grams=Decimal(0);order_hours=Decimal(0);order_cost=0;order_unknown=0;known_usage=False;known_time=False
        for i in picked:
            product_label=i['product_name'] or f"{i['variation'] or i['title']} · sem receita ({i['title']})"
            sold[product_label]['qty']+=i['qty'];sold[product_label]['revenue_cents']+=i['qty']*i['unit_cents']
            detail=json.loads(i.get('usage_detail') or i.get('cost_detail') or '{}')
            grams=Decimal(detail.get('grams','0'));hours=Decimal(detail.get('hours','0'))
            known_grams=grams>0;known_hours=hours>0
            if not known_grams:unknown_units+=i['qty'];order_unknown+=i['qty'];partial=True
            else:
                known_usage=True;order_grams+=grams*i['qty'];total_grams+=grams*i['qty']
                if kind=='devolucao' or any(word in norm(o['status']) for word in ('enviado','entregue','conclu','complet','shipped','deliver')):sent_grams+=grams*i['qty']
                else:planned_grams+=grams*i['qty']
                if not detail.get('colors'):
                    consumption[(o['date'][:7], '1ª quinzena' if int(o['date'][8:10])<=15 else '2ª quinzena','Não especificado','Sem cor')]+=grams*i['qty']
                for c in detail.get('colors',[]):
                    consumption[(o['date'][:7], '1ª quinzena' if int(o['date'][8:10])<=15 else '2ª quinzena',c['material'],c['color'])]+=Decimal(c['grams'])*i['qty']
            if known_hours:known_time=True;order_hours+=hours*i['qty'];total_hours+=hours*i['qty']
            else:unknown_time_units+=i['qty']
            usage_items.append({'order_id':o['id'],'date':o['date'],'status':o['status'],'product':product_label,'variation':i['variation'],'listing':i['title'],'original_sku':i['original_sku'],'qty':i['qty'],
                'unit_grams':str(grams) if known_grams else None,'grams':str(grams*i['qty']) if known_grams else None,
                'unit_hours':str(hours) if known_hours else None,'hours':str(hours*i['qty']) if known_hours else None,
                'cost_cents':i['cost_cents'],'production_cents':i['cost_cents']*i['qty'] if i['cost_cents'] is not None else None,
                'snapshot_at':i.get('usage_at') or i.get('cost_at'),'partial':not known_grams or not known_hours or i['cost_cents'] is None})
            if i['cost_cents'] is None:pending+=1;partial=True
            else:production+=i['cost_cents']*i['qty'];order_cost+=i['cost_cents']*i['qty']
        usage_orders.append({'order_id':o['id'],'date':o['date'],'status':o['status'],'qty':sum(i['qty'] for i in picked),
            'grams':str(order_grams) if known_usage else None,'hours':str(order_hours) if known_time else None,'production_cents':order_cost if any(item['cost_cents'] is not None for item in picked) else None,
            'unknown_units':order_unknown,'partial':bool(order_unknown or any(i['cost_cents'] is None for i in picked))})
    expenses = s.rows('SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date',(start,end))
    purchases = s.rows('SELECT b.*,f.material,f.color FROM purchases b JOIN filaments f ON f.id=b.filament_id WHERE date BETWEEN ? AND ? ORDER BY date',(start,end))
    expense_total = sum(e['amount_cents'] for e in expenses)
    purchase_total = sum(p['amount_cents']+p['freight_cents'] for p in purchases)
    stats = s.rows('SELECT * FROM stats WHERE start<=? AND end>=? ORDER BY start,listing',(end,start))
    full_stats = [r for r in stats if r['start']>=start and r['end']<=end]
    stat_total = sum(r['revenue_cents'] for r in full_stats)
    if len(full_stats)!=len(stats) or any(r['partial'] for r in stats):
        partial = True
    if not selected or not stats or narrowed or status:
        partial = True
    # Stats are comparison only. They NEVER enter revenue or profits.
    if stats and abs(Decimal(stat_total)-Decimal(gross)) > 1:
        partial = True
    partial |= unknown_time_units>0
    from ..business.workshop import losses
    loss_rows=losses(erp,start,end,product_id)
    loss_total=sum(r['value_cents'] for r in loss_rows if not r['voided'])
    receipts=s.one('SELECT coalesce(sum(amount_cents),0) n FROM settlements WHERE date BETWEEN ? AND ?',(start,end))['n']
    def rounded(n):
        from decimal import ROUND_HALF_UP
        return int(Decimal(n).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return {'start':start,'end':end,'partial':bool(partial),'orders_count':len(selected),'pending_items':pending,
            'gross_cents':rounded(gross),'fees_cents':rounded(fees),'refunds_cents':rounded(refunds),
            'production_cents':production,'expenses_cents':expense_total,'purchases_cents':purchase_total,
            'operating_cents':rounded(gross-fees-refunds-production-expense_total-loss_total),
            'cash_cents':rounded(gross-fees-refunds-expense_total-purchase_total),
            'losses_cents':loss_total,'losses':loss_rows,'received_cents':receipts,'received_cash_cents':receipts-expense_total-purchase_total,
            'stats_cents':stat_total,'difference_cents':rounded(Decimal(stat_total)-Decimal(gross)),
            'usage_total_grams':str(total_grams),'usage_total_hours':str(total_hours),'planned_grams':str(planned_grams),'sent_grams':str(sent_grams),
            'unknown_usage_units':unknown_units,'unknown_time_units':unknown_time_units,'usage_orders':usage_orders,'usage_items':usage_items,'financial_rows':financial_rows,
            'sales_by_day':[{'date':date,'gross_cents':rounded(value)} for date,value in sorted(daily.items())],
            'best_sellers':[{'product':k,**v} for k,v in sorted(sold.items(),key=lambda kv:-kv[1]['qty'])],
            'consumption':[{'month':k[0],'fortnight':k[1],'material':k[2],'color':k[3],'grams':str(v)} for k,v in sorted(consumption.items())],
            'orders':selected,'expenses':expenses,'purchases':purchases,'stats':stats,
            'allocation':narrowed}


def monthly(erp):
    from calendar import monthrange
    months = {r['month'] for r in erp.s.rows("SELECT substr(date,1,7) month FROM orders UNION SELECT substr(date,1,7) FROM expenses UNION SELECT substr(date,1,7) FROM purchases UNION SELECT substr(start,1,7) FROM stats UNION SELECT substr(date,1,7) FROM production_events UNION SELECT substr(date,1,7) FROM settlements")}
    result = []
    for month in sorted(months):
        y,m = map(int,month.split('-'))
        r = report(erp,f'{month}-01',f'{month}-{monthrange(y,m)[1]}')
        result.append({'month':month, **{k:v for k,v in r.items() if k.endswith('_cents') or k=='partial'}})
    return result
