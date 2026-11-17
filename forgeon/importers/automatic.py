"""Reconhecimento de dados Shopee; resumo da loja nunca cria pedidos."""
from pathlib import Path
from datetime import date,datetime
from calendar import monthrange
from hashlib import sha256
from decimal import Decimal
import json,re
from .sheets import read_xlsx,detect,ALIASES,preview_orders,import_period,_write_orders
from ..business.numbers import norm,day,cents,decimal

BASES={'pedido feito':'pedido_feito','produto pago':'produto_pago'}
BASIS_LABELS={'pedido_feito':'Pedido Feito','produto_pago':'Produto Pago'}
METRICS={'revenue_cents':'Vendas (BRL)','without_shopee_cents':'Vendas Sem os Descontos da Shopee','orders_count':'Pedidos',
 'average_cents':'Vendas por Pedido','clicks':'Cliques Por Produto','visitors':'Visitantes','conversion_percent':'Taxa de Conversão de Pedidos',
 'cancel_count':'Pedidos Cancelados','cancel_cents':'Vendas Canceladas','return_count':'Pedidos Devolvidos / Reembolsados','return_cents':'Vendas Devolvidas / Reembolsadas'}

def _count(value):
    value=decimal(value,maximum='1000000000')
    if value!=value.to_integral_value():raise ValueError('Contagem gerencial precisa ser inteira.')
    return int(value)

def _range(value):
    match=re.fullmatch(r'\s*(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})\s*',str(value))
    if match:return day(match[1]),day(match[2])
    return None

def _filename_range(name):
    match=re.search(r'(20\d{6})[_-](20\d{6})',name)
    return tuple(datetime.strptime(v,'%Y%m%d').date().isoformat() for v in match.groups()) if match else None

def parse_shop(headers,rows,basis,filename):
    columns={key:next((h for h in headers if norm(h)==norm(label)),None) for key,label in METRICS.items()}
    if not columns['revenue_cents'] or not columns['orders_count']:raise ValueError('Resumo sem colunas de vendas e pedidos.')
    date_column=next((h for h in headers if norm(h)=='data'),None)
    if not date_column:raise ValueError('Resumo sem coluna Data.')
    ranges={_range(row.get(date_column)) for row in rows if _range(row.get(date_column))}
    if len(ranges)>1:raise ValueError('Mais de um total de período na mesma aba. Use o modo avançado para revisar.')
    overall=next(iter(ranges),None) or _filename_range(filename)
    if not overall or overall[1]<overall[0]:raise ValueError('Não foi possível identificar o período do resumo.')
    dates=[]
    for row in rows:
        value=row.get(date_column)
        if value in (None,'') or norm(value)=='data' or _range(value):continue
        dates.append(day(value))
    if len(set(dates))!=len(dates):raise ValueError('Datas repetidas na mesma base gerencial.')
    monthly=bool(dates) and all(value[8:]=='01' for value in dates) and (overall[0][:7]!=overall[1][:7] or overall[1][8:]!='01')
    result=[]
    for row in rows:
        value=row.get(date_column)
        if value in (None,'') or norm(value)=='data':continue
        interval=_range(value)
        if interval:start,end=interval;grain='period';key=start+':'+end
        else:
            start=day(value);grain='month' if monthly else 'day';key=start[:7] if monthly else start
            end=min(f'{start[:7]}-{monthrange(int(start[:4]),int(start[5:7]))[1]}',overall[1]) if monthly else start
            start=max(start,overall[0])
        if not overall[0]<=start<=end<=overall[1]:raise ValueError('Linha gerencial fora do período declarado.')
        metrics={}
        for name,column in columns.items():
            raw=row.get(column) if column else None
            if raw is None or str(raw).strip() in ('','-','--'):
                if name in ('revenue_cents','orders_count'):raise ValueError('Resumo com vendas/pedidos ausentes.')
                metrics[name]=None;continue
            if name.endswith('_cents'):metrics[name]=cents(raw)
            elif name=='conversion_percent':
                metrics[name]=str(decimal(str(raw).replace('%','')))
                if Decimal(metrics[name])>100:raise ValueError('Conversão gerencial maior que 100%.')
            else:metrics[name]=_count(raw)
        result.append({'basis':basis,'grain':grain,'period_key':key,'start':start,'end':end,'detail':metrics})
    if not result:raise ValueError('Resumo gerencial vazio.')
    return result

def inspect_file(path):
    path=Path(path);_,_,names=read_xlsx(path)
    if len(names)>16:raise ValueError('Importação automática limitada a 16 abas por arquivo.')
    orders=[];shop=[];warnings=[];loaded=0;found_bases=set()
    for name in names:
        headers,rows,_=read_xlsx(path,name);loaded+=len(rows)*len(headers)
        if loaded>4000000:raise ValueError('Arquivo excede o limite total da importação automática.')
        mapping=detect(headers,list(ALIASES))
        if all(mapping.get(k) for k in ('order_id','date','status','listing','qty','unit')):
            orders.append((name,rows,mapping));continue
        basis=BASES.get(norm(name))
        if basis and mapping.get('revenue') and mapping.get('orders_count'):
            if basis in found_bases:raise ValueError('Base gerencial repetida no mesmo arquivo.')
            found_bases.add(basis);shop.extend(parse_shop(headers,rows,basis,path.name))
    if orders and shop:raise ValueError('Arquivo mistura pedidos e resumo. Separe os formatos para revisão.')
    digest=sha256(path.read_bytes()).hexdigest()
    if len(orders)==1:
        sheet,rows,mapping=orders[0];prepared,warnings=preview_orders(rows,mapping,path.name);period=import_period(prepared,path.name)
        return {'kind':'orders','source_name':path.name,'source_hash':digest,'sheets':[sheet],'orders':prepared,'period':period,'warnings':warnings}
    if len(orders)>1:raise ValueError('Várias abas de pedidos reconhecidas. Revise no modo avançado para evitar duplicação.')
    if shop:
        period={'start':min(r['start'] for r in shop),'end':max(r['end'] for r in shop)}
        for basis in found_bases:
            total=next((r for r in shop if r['basis']==basis and r['grain']=='period'),None)
            details=[r for r in shop if r['basis']==basis and r['grain']!='period']
            if total and details and any(sum(r['detail'][k] for r in details)!=total['detail'][k] for k in ('revenue_cents','orders_count')):warnings.append('Total e linhas do período divergem na base '+BASIS_LABELS[basis]+'. São referências separadas, nunca somadas entre si.')
        return {'kind':'shop','source_name':path.name,'source_hash':digest,'sheets':[BASIS_LABELS[b] for b in sorted(found_bases)],'metrics':shop,'period':period,'warnings':warnings}
    raise ValueError('Formato não reconhecido. Use pedidos detalhados ou resumo com abas Pedido Feito/Produto Pago; mapeamento manual fica em Avançado.')

def _write_shop(s,plan):
    for row in plan['metrics']:
        old=s.one('SELECT start,end FROM shop_metrics WHERE basis=? AND grain=? AND period_key=?',(row['basis'],row['grain'],row['period_key']))
        if old and row['grain']!='period' and (old['end']>row['end'] or old['start']<row['start']):raise ValueError('Resumo novo cobre menos dias que o já salvo. O período mais completo foi preservado.')
        s.db.execute('INSERT INTO shop_metrics VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(basis,grain,period_key) DO UPDATE SET start=excluded.start,end=excluded.end,detail=excluded.detail,source_hash=excluded.source_hash,recorded=excluded.recorded',
          (row['basis'],row['grain'],row['period_key'],row['start'],row['end'],json.dumps(row['detail'],ensure_ascii=False),plan['source_hash'],datetime.now().isoformat(timespec='seconds')))
    s.log('importar_resumo_loja',{'linhas':len(plan['metrics']),'bases':sorted({r['basis'] for r in plan['metrics']})})

def commit_plans(erp,plans):
    if not plans:raise ValueError('Selecione ao menos uma planilha reconhecida.')
    snapshots={}
    for plan in plans:
        for order in plan.get('orders',[]):
            signature=json.dumps({k:v for k,v in order.items() if k!='partial'},sort_keys=True,ensure_ascii=False)
            if order['id'] in snapshots and snapshots[order['id']]!=signature:raise ValueError('Mesmo pedido com informações conflitantes em arquivos selecionados. Importe somente o arquivo mais recente desse pedido.')
            snapshots[order['id']]=signature
    backup=erp.s.backup();seen=set()
    with erp.s.transaction():
        for plan in plans:
            if plan['source_hash'] in seen:continue
            seen.add(plan['source_hash'])
            if plan['kind']=='orders':
                _write_orders(erp,plan['orders'],plan['period'],backup.name)
                erp.s.db.execute('UPDATE order_coverage SET source_hash=? WHERE start=? AND end=? AND kind=?',(plan['source_hash'],plan['period']['start'],plan['period']['end'],plan['period']['coverage_kind']))
            elif plan['kind']=='shop':_write_shop(erp.s,plan)
            else:raise ValueError('Tipo de importação desconhecido.')
            erp.s.db.execute('INSERT INTO import_history(source_hash,source_name,start,end,recorded,summary) VALUES(?,?,?,?,?,?)',(plan['source_hash'],plan['source_name'],plan['period']['start'],plan['period']['end'],datetime.now().isoformat(timespec='seconds'),json.dumps({'kind':plan['kind'],'records':len(plan.get('orders',plan.get('metrics',[])))},ensure_ascii=False)))
    return backup
