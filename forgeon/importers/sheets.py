"""Bounded XLSX reading, explicit header mapping and transactional imports."""
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from openpyxl import load_workbook
from ..business.numbers import norm, cents, day, quantity, decimal

ALIASES = {
 'order_id': ['ID do pedido', 'Número do pedido', 'Order ID', 'ID de pedido'],
 'date': ['Data de criação do pedido', 'Data de criação', 'Order Creation Date', 'Data do pedido', 'Data'],
 'status': ['Status do pedido', 'Order Status', 'Status'],
 'listing': ['Nome do produto', 'Product Name', 'Anúncio', 'Produto'],
 'variation': ['Nome da variação', 'Variation Name', 'Variação'],
 'sku': ['Nº de referência SKU', 'Número de referência SKU', 'SKU da variação', 'Variation SKU', 'SKU'],
 'qty': ['Quantidade', 'Quantity', 'Qtd'],
 'unit': ['Preço acordado', 'Preço com desconto', 'Deal Price', 'Preço unitário'],
 'gross': ['Valor total do pedido', 'Order Total', 'Total do pedido'],
 'subtotal':['Subtotal do produto'], 'buyer_total':['Valor Total'], 'buyer_shipping':['Taxa de envio pagas pelo comprador'],
 'market_total':['Total global'], 'seller_coupon':['Cupom do vendedor'], 'seller_coins':['Coin Cashback Voucher Amount Sponsored by Seller'],
 'expected_qty':['Número de produtos pedidos'],
 'return_qty':['Returned quantity','Quantidade devolvida'], 'return_status':['Status da Devolução / Reembolso'],
 'commission_gross':['Taxa de comissão bruta'], 'service_gross':['Taxa de serviço bruta'],
 'fees': ['Taxas totais', 'Taxas', 'Total Fees'],
 'commission': ['Taxa de comissão líquida', 'Taxa de comissão', 'Commission Fee'],
 'service': ['Taxa de serviço líquida', 'Taxa de serviço', 'Service Fee'],
 'transaction': ['Taxa de transação', 'Transaction Fee'],
 'refund': ['Valor do reembolso', 'Refund Amount', 'Reembolso'],
 'revenue': ['Vendas (BRL)', 'Vendas (R$)', 'Vendas', 'Receita', 'Revenue'],
 'orders_count': ['Pedidos', 'Orders', 'Quantidade de pedidos'],
}
LABELS = {'order_id':'ID do pedido','date':'Data','status':'Status','listing':'Produto/anúncio','variation':'Variação',
          'sku':'SKU','qty':'Quantidade','unit':'Preço unitário','gross':'Total do pedido (uma vez por pedido)',
          'fees':'Taxas totais (ou componentes abaixo)','commission':'Comissão','service':'Serviço','transaction':'Transação',
          'refund':'Reembolso efetivo','revenue':'Receita','orders_count':'Número de pedidos'}


LABELS.update({'expected_qty':'Unidades totais declaradas no pedido (checagem de itens completos)','subtotal':'Subtotal dos itens (já com desconto de preço)','buyer_total':'Total pago pelo comprador (referência)','buyer_shipping':'Frete pago pelo comprador (referência)','market_total':'Total global (referência, não somar como venda)','seller_coupon':'Cupom financiado pelo vendedor','seller_coins':'Moedas/cashback financiados pelo vendedor (R$)','return_qty':'Quantidade devolvida','return_status':'Status de devolução/reembolso','commission_gross':'Comissão bruta (referência)','service_gross':'Serviço bruto (referência)'})


def read_xlsx(path, sheet=None, header_row=None):
    path = Path(path)
    if path.suffix.lower() != '.xlsx' or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Aceitos somente XLSX de até 32 MB.')
    try:
        with ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > 4096 or sum(i.file_size for i in infos) > 128 * 1024 * 1024:
                raise ValueError('Planilha descompactada excede o limite de segurança.')
        wb = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    except (BadZipFile, KeyError):
        raise ValueError('Estrutura XLSX inválida.') from None
    try:
        ws = wb[sheet] if sheet else wb.active
        if (ws.max_column or 0) > 256 or (ws.max_row or 0) > 100001:
            raise ValueError('Limite: 256 colunas e 100 mil linhas.')
        # Some marketplace exporters incorrectly declare A1:A1 despite full XML rows.
        ws.reset_dimensions()
        raw = []
        cell_count = 0
        for number, row in enumerate(ws.iter_rows(), 1):
            if number > 100001 or len(row) > 256:
                raise ValueError('Planilha excede limites de leitura.')
            cell_count += len(row)
            if cell_count > 2000000:
                raise ValueError("Planilha excede 2 milhões de células; divida o arquivo por pedidos completos.")
            values = []
            for cell in row:
                if cell.data_type == 'f':
                    raise ValueError(f'Fórmula na célula {cell.coordinate}. Salve uma cópia somente com valores.')
                value = cell.value
                if isinstance(value,str) and len(value)>32767:
                    raise ValueError('Texto de célula excede o limite de segurança.')
                # Numeric SKUs with a simple zero-mask can be recovered; text is preferred.
                if isinstance(value, (int, float)) and cell.number_format and set(cell.number_format) == {'0'} and len(cell.number_format) > 1:
                    value = str(int(value)).zfill(len(cell.number_format))
                values.append(value)
            raw.append(values)
        if not raw:
            raise ValueError('Planilha vazia.')
        if header_row is None:
            known = {norm(a) for aliases in ALIASES.values() for a in aliases}
            header_row = max(range(min(30, len(raw))), key=lambda i: sum(norm(v) in known for v in raw[i] if v is not None))
        if header_row < 0 or header_row >= len(raw):
            raise ValueError('Linha de cabeçalho fora da planilha.')
        headers = [str(v).strip() if v is not None else f'Coluna {i+1}' for i, v in enumerate(raw[header_row])]
        if header_row < 0 or header_row >= len(raw):
            raise ValueError('Linha de cabeçalho fora da planilha.')
        seen_headers={}
        for index,header in enumerate(headers):
            seen_headers[header]=seen_headers.get(header,0)+1
            if seen_headers[header]>1:headers[index]=f'{header} [{seen_headers[header]}]'
        rows = [dict(zip(headers, r)) for r in raw[header_row+1:] if any(v is not None for v in r)]
        return headers, rows, list(wb.sheetnames)
    finally:
        wb.close()


def detect(headers, keys):
    result = {}
    for key in keys:
        result[key] = next((h for alias in ALIASES.get(key,[key]) for h in headers if norm(h)==norm(alias)), '')
    return result


def cell(row, mapping, key, default=''):
    value = row.get(mapping.get(key, ''))
    return default if value is None or value == '' else value


def status_kind(value):
    n = norm(value)
    if 'cancel' in n:
        return 'cancelado'
    if any(w in n for w in ('devol', 'reembols', 'return', 'refund')):
        return 'devolucao'
    return 'ativo'


def preview_orders(rows, mapping, filename='', partial=False):
    required = ['order_id','date','status','listing','qty','unit']
    if any(not mapping.get(k) for k in required):
        raise ValueError('Mapeie ID, data, status, produto, quantidade e preço unitário.')
    groups = defaultdict(list)
    warnings = []
    for number, row in enumerate(rows, 2):
        oid = str(cell(row,mapping,'order_id')).strip()
        if not oid:
            raise ValueError(f'Linha {number}: ID do pedido vazio.')
        groups[oid].append(row)
    if 'toship' in filename.lower():
        partial = True
        warnings.append('Order.toship contém somente pedidos A Enviar. Para o mês completo, importe Todos os pedidos/Order.all.')
    result = []
    for oid, members in groups.items():
        dates = {day(cell(r,mapping,'date')) for r in members}
        statuses = {str(cell(r,mapping,'status')).strip() for r in members}
        if len(dates) != 1 or len(statuses) != 1 or not all(statuses):
            raise ValueError(f'Pedido {oid}: datas ou status contraditórios.')
        def order_amount(key):
            amounts = {cents(cell(r,mapping,key,0)) for r in members if cell(r,mapping,key,'') != ''}
            if len(amounts) > 1:
                raise ValueError(f'Pedido {oid}: valores diferentes na coluna {LABELS[key]}. Revise a planilha.')
            return next(iter(amounts),0)
        items = {}
        for r in members:
            title = str(cell(r,mapping,'listing')).strip()
            variation = str(cell(r,mapping,'variation')).strip()
            sku = str(cell(r,mapping,'sku')).strip()
            if not title:
                raise ValueError(f'Pedido {oid}: produto vazio.')
            q = quantity(cell(r,mapping,'qty'))
            unit = cents(cell(r,mapping,'unit'))
            key = hashlib.sha256(json.dumps([title,variation,sku], ensure_ascii=False).encode()).hexdigest()
            if key in items:
                if items[key]['unit_cents'] != unit:
                    raise ValueError(f'Pedido {oid}: preços distintos para o mesmo item. Separe a identificação na planilha.')
                items[key]['qty'] += q
            else:
                items[key] = {'item_key':key,'title':title,'variation':variation,'original_sku':sku,'qty':q,'unit_cents':unit}
        if mapping.get('expected_qty'):
            expected={quantity(cell(r,mapping,'expected_qty')) for r in members if cell(r,mapping,'expected_qty','')!=''}
            if expected and (len(expected)!=1 or sum(i['qty'] for i in items.values())!=next(iter(expected))):raise ValueError(f'Pedido {oid}: quantidade não corresponde ao total declarado. Inclua todos os itens deste pedido.')
        fees = order_amount('fees') if mapping.get('fees') else sum(order_amount(k) for k in ('commission','service','transaction'))
        gross_present = bool(mapping.get('gross')) and any(cell(r,mapping,'gross','') != '' for r in members)
        fee_keys = ['fees'] if mapping.get('fees') else [k for k in ('commission','service','transaction') if mapping.get(k)]
        fees_present = bool(fee_keys) and all(any(cell(r,mapping,k,'') != '' for r in members) for k in fee_keys)
        item_total=sum(cents(cell(r,mapping,'subtotal',0)) if mapping.get('subtotal') and cell(r,mapping,'subtotal','')!='' else quantity(cell(r,mapping,'qty'))*cents(cell(r,mapping,'unit')) for r in members)
        discount=order_amount('seller_coupon')+order_amount('seller_coins')
        if discount>item_total:raise ValueError('Descontos do vendedor maiores que o subtotal dos itens.')
        if mapping.get('subtotal'):
            gross=item_total-discount
            gross_present=True
        else:gross = order_amount('gross') if gross_present else item_total
        financial={'items_cents':item_total,'seller_discount_cents':discount,**{key+'_cents':order_amount(key) for key in ('commission','service','transaction','commission_gross','service_gross','buyer_total','buyer_shipping','market_total')}}
        financial['basis']='itens_menos_cupom_vendedor' if mapping.get('subtotal') else 'total_mapeado'
        returned=[decimal(cell(r,mapping,'return_qty',0)) for r in members]
        if any(value!=value.to_integral_value() for value in returned):raise ValueError('Quantidade devolvida deve ser inteira.')
        financial['returned_qty']=sum(map(int,returned))
        financial['return_status']='; '.join(sorted({str(cell(r,mapping,'return_status')) for r in members if cell(r,mapping,'return_status')}))
        if status_kind(next(iter(statuses)))=='cancelado':gross=0
        incomplete = partial or not gross_present or not fees_present
        if financial['returned_qty'] or financial['return_status']:incomplete=True
        result.append({'id':oid,'date':next(iter(dates)),'status':next(iter(statuses)), 'gross_cents':gross,'fees_cents':fees,
                       'refund_cents':order_amount('refund'),'partial':int(incomplete),'items':list(items.values()),'financial':financial})
    if mapping.get('subtotal'):
        warnings.append('Receita de produtos = soma dos subtotais (desconto de preço já aplicado) menos cupom/moedas do vendedor. Frete, Valor Total e Total global são referências separadas. Usa comissão e serviço líquidos quando disponíveis.')
    elif not mapping.get('gross'):
        warnings.append('Total estimado pela soma dos itens; pode diferir do total do marketplace.')
    if not any(mapping.get(k) for k in ('fees','commission','service','transaction')):
        warnings.append('Taxas não identificadas; resultado marcado DADOS PARCIAIS.')
    warnings.append('O arquivo deve conter TODOS os itens de cada pedido listado. Totais e taxas são do pedido, sem multiplicar pelos itens.')
    warnings.append('SKUs numéricos sem máscara de zeros já perderam seus zeros no Excel; confira a prévia. Prefira células de texto.')
    return result, warnings


def import_orders(erp, orders, period=None):
    s = erp.s
    period=period or import_period(orders)
    backup = s.backup()
    with s.transaction():
        for order in orders:
            oid = order['id']
            old_items = {r['item_key']:r for r in s.rows('SELECT * FROM order_items WHERE order_id=?', (oid,))}
            s.db.execute('INSERT INTO orders(id,date,status,gross_cents,fees_cents,refund_cents,source,partial) VALUES(?,?,?,?,?,?,?,?) '
                         'ON CONFLICT(id) DO UPDATE SET date=excluded.date,status=excluded.status,gross_cents=excluded.gross_cents,fees_cents=excluded.fees_cents,refund_cents=excluded.refund_cents,partial=excluded.partial,updated=CURRENT_TIMESTAMP',
                         (oid,order['date'],order['status'],order['gross_cents'],order['fees_cents'],order['refund_cents'],'Shopee',int(bool(order['partial'] or period['partial']))))
            old_usage={r['item_key']:r for r in s.rows('SELECT i.item_key,u.detail,u.recorded FROM item_usage u JOIN order_items i ON i.id=u.item_id WHERE i.order_id=?',(oid,))}
            s.db.execute('INSERT INTO order_financials VALUES(?,?) ON CONFLICT(order_id) DO UPDATE SET detail=excluded.detail',(oid,json.dumps(order.get('financial',{}),ensure_ascii=False)))
            s.db.execute('DELETE FROM order_items WHERE order_id=?',(oid,))
            for i in order['items']:
                old = old_items.get(i['item_key'])
                if old:
                    origin_id, pid, cost, detail, at = (old[k] for k in ('origin_id','product_id','cost_cents','cost_detail','cost_at'))
                else:
                    origin = s.one("SELECT * FROM origins WHERE source='Shopee' AND listing=? AND variation=? AND sku=?", (i['title'],i['variation'],i['original_sku']))
                    if not origin:
                        matched=erp.match_product(i['title'],i['variation'])
                        origin_id = s.db.execute("INSERT INTO origins(source,listing,variation,sku,product_id) VALUES('Shopee',?,?,?,?)", (i['title'],i['variation'],i['original_sku'],matched)).lastrowid
                        if i['original_sku']:
                            s.db.execute("INSERT INTO sku_codes VALUES(?,'usado') ON CONFLICT(code) DO NOTHING", (i['original_sku'],))
                        pid = matched
                    else:
                        origin_id, pid = origin['id'], origin['product_id'] if origin['active'] else None
                        if pid is None and origin['active']:
                            pid=erp.match_product(i['title'],i['variation'])
                            if pid:s.db.execute('UPDATE origins SET product_id=? WHERE id=?',(pid,origin_id))
                    cost = detail = at = None
                    if pid:
                        calc = erp.cost(pid)
                        if not calc['missing']:
                            cost, detail, at = calc['total_cents'], json.dumps(calc, ensure_ascii=False), datetime.now().isoformat(timespec='seconds')
                cursor=s.db.execute('INSERT INTO order_items(order_id,item_key,origin_id,product_id,original_sku,title,variation,qty,unit_cents,cost_cents,cost_detail,cost_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                             (oid,i['item_key'],origin_id,pid,i['original_sku'],i['title'],i['variation'],i['qty'],i['unit_cents'],cost,detail,at))
                previous=old_usage.get(i['item_key'])
                usage=previous['detail'] if previous else detail
                recorded=previous['recorded'] if previous else at
                if usage is None and pid:
                    c=erp.cost(pid)
                    if decimal(c['grams'])>0 or decimal(c['hours'])>0:usage=json.dumps(c,ensure_ascii=False);recorded=datetime.now().isoformat(timespec='seconds')
                if usage:s.db.execute('INSERT INTO item_usage VALUES(?,?,?)',(cursor.lastrowid,usage,recorded or datetime.now().isoformat(timespec='seconds')))
        period=period or import_period(orders)
        for key,value in (('active_month',period['active_month']),('last_import_start',period['start']),('last_import_end',period['end'])):
            s.db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
        s.log('importar_pedidos', {'pedidos':len(orders),'backup':backup.name})
    return backup


def preview_stats(rows, mapping, start, end, partial):
    start, end = day(start), day(end)
    if end < start:
        raise ValueError('Período inválido.')
    if not mapping.get('revenue') or not mapping.get('listing'):
        raise ValueError('Mapeie anúncio e receita. Não misture linha de total com linhas de anúncios.')
    from calendar import monthrange
    from datetime import date
    first,last=date.fromisoformat(start),date.fromisoformat(end)
    partial = partial or first.day != 1 or first.year != last.year or first.month != last.month or last.day != monthrange(last.year,last.month)[1]
    result = []
    seen = set()
    for row in rows:
        listing = str(cell(row,mapping,'listing')).strip()
        if not listing:
            continue
        if norm(listing) in ('total','todos','todos os produtos','total geral'):
            raise ValueError('Remova a linha de total da cópia de importação para não somá-la aos anúncios.')
        if listing in seen:
            raise ValueError('Anúncio repetido no período: agregue antes de importar.')
        seen.add(listing)
        n = cell(row,mapping,'orders_count',0)
        count = int(n)
        if count < 0 or str(n).strip() not in (str(count), str(float(count))):
            raise ValueError('Número de pedidos inválido.')
        result.append({'start':start,'end':end,'listing':listing,'revenue_cents':cents(cell(row,mapping,'revenue')),'orders_count':count,'partial':int(partial)})
    if not result:
        raise ValueError('Nenhuma estatística encontrada.')
    return result


def import_stats(erp, rows):
    backup = erp.s.backup()
    with erp.s.transaction():
        for r in rows:
            overlapping = erp.s.one('SELECT id FROM stats WHERE listing=? AND start<=? AND end>=? AND NOT(start=? AND end=?)', (r['listing'],r['end'],r['start'],r['start'],r['end']))
            if overlapping:
                raise ValueError('Estatísticas sobrepostas para o mesmo anúncio. Use períodos sem sobreposição.')
            erp.s.db.execute('INSERT INTO stats(start,end,listing,revenue_cents,orders_count,partial) VALUES(?,?,?,?,?,?) '
                             'ON CONFLICT(source,start,end,listing) DO UPDATE SET revenue_cents=excluded.revenue_cents,orders_count=excluded.orders_count,partial=excluded.partial',
                             tuple(r[k] for k in ('start','end','listing','revenue_cents','orders_count','partial')))
        erp.s.log('importar_estatisticas', {'linhas':len(rows),'backup':backup.name})
    return backup


def import_period(orders,filename=''):
    import re
    from calendar import monthrange
    from datetime import date
    if not orders:raise ValueError('Arquivo sem pedidos.')
    start=min(o['date'] for o in orders);end=max(o['date'] for o in orders)
    match=re.search(r'(20\d{6})[_-](20\d{6})',filename)
    if match:
        declared_start=datetime.strptime(match[1],'%Y%m%d').date().isoformat()
        declared_end=datetime.strptime(match[2],'%Y%m%d').date().isoformat()
        if declared_start<=start<=end<=declared_end:start,end=declared_start,declared_end
    months=sorted({o['date'][:7] for o in orders})
    last=date.fromisoformat(end)
    partial=start[8:]!='01' or end[8:]!=str(monthrange(last.year,last.month)[1]) or 'toship' in filename.lower()
    return {'start':start,'end':end,'months':months,'active_month':months[-1],'partial':partial}
