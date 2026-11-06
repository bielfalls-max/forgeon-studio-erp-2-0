from collections import defaultdict
from decimal import Decimal
import json
from ..business.numbers import day
from ..importers.sheets import status_kind


def report(erp, start, end, product_id=None, status=''):
    start, end = day(start), day(end)
    if end < start:
        raise ValueError('Período inválido.')
    s = erp.s
    orders = s.rows('SELECT * FROM orders WHERE date BETWEEN ? AND ? ORDER BY date,id',(start,end))
    gross = fees = refunds = production = 0
    pending = 0
    partial = False
    selected = []
    sold = defaultdict(lambda: {'qty':0,'revenue_cents':0})
    consumption = defaultdict(Decimal)
    for o in orders:
        if status and status_kind(o['status']) != status:
            continue
        items = s.rows('SELECT i.*,p.name product_name FROM order_items i LEFT JOIN products p ON p.id=i.product_id WHERE order_id=?',(o['id'],))
        picked = [i for i in items if product_id is None or i['product_id'] == product_id]
        if not picked:
            continue
        selected.append(o)
        # Product filters allocate order totals by item sale value; sum of all shares is exact before rounding.
        basis = sum(i['qty']*i['unit_cents'] for i in items)
        share = Decimal(sum(i['qty']*i['unit_cents'] for i in picked)) / basis if product_id is not None and basis else Decimal(1)
        if product_id is not None and not basis:
            partial = True
        partial |= bool(o['partial'])
        kind = status_kind(o['status'])
        if kind == 'cancelado':
            continue  # costs for failed production must be entered as an expense
        gross += Decimal(o['gross_cents']) * share
        fees += Decimal(o['fees_cents']) * share
        refunds += Decimal(o['refund_cents']) * share
        if kind == 'devolucao' and o['refund_cents'] == 0:
            partial = True
        for i in picked:
            sold[i['product_name'] or f"Não vinculado: {i['title']} / {i['variation']}"]['qty'] += i['qty']
            sold[i['product_name'] or f"Não vinculado: {i['title']} / {i['variation']}"]['revenue_cents'] += i['qty']*i['unit_cents']
            if i['cost_cents'] is None:
                pending += 1
                partial = True
                continue
            production += i['cost_cents']*i['qty']
            detail = json.loads(i['cost_detail'])
            # Material quantities remain physical consumption even when a manual manufacturing cost is used.
            if not detail['colors'] and Decimal(detail['grams']) > 0:
                consumption[(o['date'][:7], '1ª quinzena' if int(o['date'][8:10])<=15 else '2ª quinzena', 'Não especificado', 'Sem cor')] += Decimal(detail['grams'])*i['qty']
            for c in detail['colors']:
                consumption[(o['date'][:7], '1ª quinzena' if int(o['date'][8:10])<=15 else '2ª quinzena', c['material'], c['color'])] += Decimal(c['grams'])*i['qty']
    expenses = s.rows('SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date',(start,end))
    purchases = s.rows('SELECT b.*,f.material,f.color FROM purchases b JOIN filaments f ON f.id=b.filament_id WHERE date BETWEEN ? AND ? ORDER BY date',(start,end))
    expense_total = sum(e['amount_cents'] for e in expenses)
    purchase_total = sum(p['amount_cents']+p['freight_cents'] for p in purchases)
    stats = s.rows('SELECT * FROM stats WHERE start<=? AND end>=? ORDER BY start,listing',(end,start))
    full_stats = [r for r in stats if r['start']>=start and r['end']<=end]
    stat_total = sum(r['revenue_cents'] for r in full_stats)
    if len(full_stats)!=len(stats) or any(r['partial'] for r in stats):
        partial = True
    if not selected or not stats or product_id is not None or status:
        partial = True
    # Stats are comparison only. They NEVER enter revenue or profits.
    if stats and abs(Decimal(stat_total)-Decimal(gross)) > 1:
        partial = True
    def rounded(n):
        from decimal import ROUND_HALF_UP
        return int(Decimal(n).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return {'start':start,'end':end,'partial':bool(partial),'orders_count':len(selected),'pending_items':pending,
            'gross_cents':rounded(gross),'fees_cents':rounded(fees),'refunds_cents':rounded(refunds),
            'production_cents':production,'expenses_cents':expense_total,'purchases_cents':purchase_total,
            'operating_cents':rounded(gross-fees-refunds-production-expense_total),
            'cash_cents':rounded(gross-fees-refunds-expense_total-purchase_total),
            'stats_cents':stat_total,'difference_cents':rounded(Decimal(stat_total)-Decimal(gross)),
            'best_sellers':[{'product':k,**v} for k,v in sorted(sold.items(),key=lambda kv:-kv[1]['qty'])],
            'consumption':[{'month':k[0],'fortnight':k[1],'material':k[2],'color':k[3],'grams':str(v)} for k,v in sorted(consumption.items())],
            'orders':selected,'expenses':expenses,'purchases':purchases,'stats':stats,
            'allocation':product_id is not None}


def monthly(erp):
    from calendar import monthrange
    months = {r['month'] for r in erp.s.rows("SELECT substr(date,1,7) month FROM orders UNION SELECT substr(date,1,7) FROM expenses UNION SELECT substr(date,1,7) FROM purchases UNION SELECT substr(start,1,7) FROM stats")}
    result = []
    for month in sorted(months):
        y,m = map(int,month.split('-'))
        r = report(erp,f'{month}-01',f'{month}-{monthrange(y,m)[1]}')
        result.append({'month':month, **{k:v for k,v in r.items() if k.endswith('_cents') or k=='partial'}})
    return result
