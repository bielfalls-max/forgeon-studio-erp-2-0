"""Preferências, pendências e revisão de importação sem alterações implícitas."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json,platform,sqlite3
from .numbers import norm
from .production import store_item_snapshot
from ..importers.sheets import status_kind
from ..version import VERSION


def preference(s,key,default=None):
    row=s.one('SELECT value FROM preferences WHERE key=?',(key,))
    if not row:return default
    try:return json.loads(row['value'])
    except (ValueError,TypeError):return default


def set_preference(s,key,value):
    with s.transaction():s.db.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))


def pending(erp):
    result=[];s=erp.s
    for p in s.rows('SELECT * FROM products WHERE archived=0'):
        cost=erp.cost(p['id'])
        if cost['missing']:result.append({'type':'Cadastro de produto','reference':str(p['id']),'description':p['name']+' · '+', '.join(cost['missing']),'target':'Produtos'})
    for o in s.rows('SELECT * FROM origins WHERE active=1 AND product_id IS NULL'):
        result.append({'type':'Origem sem vínculo','reference':str(o['id']),'description':o['variation']+' · '+o['listing'],'target':'Catálogo e SKUs'})
    for sku in sorted(erp.conflicts()):result.append({'type':'Conflito de SKU','reference':sku,'description':'Mesmo código em produtos físicos diferentes','target':'Catálogo e SKUs'})
    for i in s.rows('SELECT i.*,o.status FROM order_items i JOIN orders o ON o.id=i.order_id WHERE i.cost_cents IS NULL'):
        if status_kind(i['status'])!='cancelado':result.append({'type':'Custo pendente','reference':i['order_id'],'description':i['variation'] or i['title'],'target':'Pedidos'})
    for f in s.rows('SELECT * FROM filaments WHERE kg_cents=0'):
        result.append({'type':'Revisar preço zero','reference':str(f['id']),'description':f['material']+' / '+f['color'],'target':'Custos e cores'})
    for j in s.rows("SELECT j.*,o.status FROM production_jobs j JOIN orders o ON o.id=j.order_id WHERE j.state<>'Cancelado'"):
        if status_kind(j['status'])=='cancelado':result.append({'type':'Pedido cancelado na produção','reference':str(j['id']),'description':'Revise o lote; consumo já baixado não retorna automaticamente.','target':'Produção'})
    return result


def apply_links(erp,links):
    """Todos os vínculos explícitos de uma revisão são aplicados em uma transação."""
    s=erp.s;s.backup()
    with s.transaction():
        for oid,pid in links:
            erp.product(pid)
            old=s.one('SELECT * FROM origins WHERE id=? AND active=1',(oid,))
            if not old:raise ValueError('Origem não encontrada/ativa.')
            s.db.execute('UPDATE origins SET product_id=? WHERE id=?',(pid,oid))
            s.db.execute('UPDATE order_items SET product_id=? WHERE origin_id=?',(pid,oid))
            for item in s.rows('SELECT * FROM order_items WHERE origin_id=?',(oid,)):store_item_snapshot(erp,item)
            s.log('vinculo_em_lote',{'origem':oid,'antes':old['product_id'],'depois':pid})
    return len(links)


def compare_import(s,orders,source=None):
    rows=[]
    for order in orders:
        old=s.one('SELECT * FROM orders WHERE id=?',(order['id'],))
        changes=[]
        if old:
            for key,label in [('status','Status'),('date','Data'),('gross_cents','Receita'),('fees_cents','Taxas'),('refund_cents','Reembolso')]:
                if old[key]!=order[key]:changes.append(label)
            before={r['item_key']:(r['qty'],r['unit_cents']) for r in s.rows('SELECT * FROM order_items WHERE order_id=?',(order['id'],))}
            after={r['item_key']:(r['qty'],r['unit_cents']) for r in order['items']}
            if before!=after:changes.append('Itens/quantidades/preços')
        rows.append({'id':order['id'],'action':'Novo' if old is None else ('Atualizado' if changes else 'Sem alteração comercial'),'changes':', '.join(changes),
                     'before_cents':old['gross_cents'] if old else None,'after_cents':order['gross_cents'],'items':len(order['items'])})
    duplicate=False
    if source:
        digest=sha256(Path(source).read_bytes()).hexdigest()
        duplicate=bool(s.one('SELECT id FROM import_history WHERE source_hash=?',(digest,)))
    return rows,duplicate


def record_import(s,path,period,rows):
    with s.transaction():
        s.db.execute('INSERT INTO import_history(source_hash,source_name,start,end,recorded,summary) VALUES(?,?,?,?,?,?)',
                     (sha256(Path(path).read_bytes()).hexdigest(),Path(path).name,period['start'],period['end'],datetime.now().isoformat(timespec='seconds'),
                      json.dumps({key:sum(r['action']==key for r in rows) for key in ('Novo','Atualizado','Sem alteração comercial')},ensure_ascii=False)))


def save_preset(s,name,filters):
    if not name.strip():raise ValueError('Informe um nome para o filtro.')
    with s.transaction():s.db.execute("INSERT INTO filter_presets(name,scope,detail) VALUES(?,'relatorios',?) ON CONFLICT(name) DO UPDATE SET detail=excluded.detail",(name.strip(),json.dumps(filters,ensure_ascii=False)))


def diagnostic(s):
    from importlib.metadata import version,PackageNotFoundError
    versions={}
    for name in ('PySide6','openpyxl','defusedxml'):
        try:versions[name]=version(name)
        except PackageNotFoundError:versions[name]='Não disponível nos metadados'
    try:s.validate(s.db);integrity='ok'
    except Exception as e:integrity=type(e).__name__
    return {'version':VERSION,'system':platform.system(),'system_release':platform.release(),'python':platform.python_version(),
            'sqlite':sqlite3.sqlite_version,'schema':s.db.execute('PRAGMA user_version').fetchone()[0],'integrity':integrity,
            'dependencies':versions,'counts':{t:s.one('SELECT count(*) n FROM '+t)['n'] for t in ('products','orders','order_items','filaments','production_jobs','stock_rolls','settlements')},
            'operations':s.rows('SELECT operation,count(*) quantity FROM audit GROUP BY operation ORDER BY operation')}


def global_search(erp,query):
    query=query.strip()
    if not query:return []
    match='%'+query+'%';s=erp.s;rows=[]
    for p in s.rows('SELECT DISTINCT p.id,p.name,p.model FROM products p LEFT JOIN origins o ON o.product_id=p.id WHERE p.name LIKE ? OR p.model LIKE ? OR o.sku LIKE ? LIMIT 100',(match,match,match)):
        rows.append({'type':'Produto','reference':str(p['id']),'description':p['name']+' / '+p['model'],'target':'Produtos'})
    for o in s.rows('SELECT DISTINCT o.id,o.date,o.status FROM orders o LEFT JOIN order_items i ON i.order_id=o.id WHERE o.id LIKE ? OR i.original_sku LIKE ? OR i.variation LIKE ? OR i.title LIKE ? LIMIT 100',(match,match,match,match)):
        rows.append({'type':'Pedido','reference':o['id'],'description':o['date']+' · '+o['status'],'target':'Pedidos'})
    return rows
