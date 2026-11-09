"""Lotes, reservas e estoque de massa. Baixas só por confirmação do operador."""
from collections import defaultdict
from datetime import datetime,date
from decimal import Decimal
from uuid import uuid4
import json
from .numbers import decimal,quantity,day,cents
from .pricing import round_cents
from ..importers.sheets import status_kind

STATES=['A produzir','Em impressão','Acabamento','Pronto','Cancelado']


def roll_balance(s,rid):
    return sum((Decimal(r['delta_grams']) for r in s.rows('SELECT delta_grams FROM stock_moves WHERE roll_id=?',(rid,))),Decimal(0))


def add_roll(s,fid,label,grams,when=None,minimum='100',purchase_id=None):
    grams=decimal(grams);minimum=decimal(minimum)
    if not label.strip():raise ValueError('Informe identificação do rolo/lote.')
    if not s.one('SELECT id FROM filaments WHERE id=?',(fid,)):raise ValueError('Filamento não encontrado.')
    when=day(when or date.today())
    rid=s.db.execute('INSERT INTO stock_rolls(filament_id,label,added,minimum_grams,purchase_id) VALUES(?,?,?,?,?)',(fid,label.strip(),when,str(minimum),purchase_id)).lastrowid
    s.db.execute('INSERT INTO stock_moves(roll_id,date,delta_grams,reason,ref) VALUES(?,?,?,?,?)',(rid,when,str(grams),'Saldo inicial informado','inicial:'+str(rid)))
    s.log('rolo_cadastrado',{'rolo':rid,'gramas':str(grams)})
    return rid


def register_roll(erp,*args,**kwargs):
    with erp.s.transaction():return add_roll(erp.s,*args,**kwargs)


def adjust_roll(erp,rid,measured,reason):
    measured=decimal(measured)
    if not reason.strip():raise ValueError('Informe motivo do ajuste de saldo físico.')
    s=erp.s
    with s.transaction():
        if not s.one('SELECT id FROM stock_rolls WHERE id=?',(rid,)):raise ValueError('Rolo não encontrado.')
        difference=measured-roll_balance(s,rid)
        s.db.execute('INSERT INTO stock_moves(roll_id,date,delta_grams,reason,ref) VALUES(?,?,?,?,?)',(rid,day(date.today()),str(difference),reason.strip(),'ajuste:'+str(uuid4())))
        s.log('ajuste_estoque',{'rolo':rid,'saldo_informado':str(measured),'motivo':reason.strip()})


def recipe_materials(recipe,units=1):
    result=defaultdict(Decimal)
    for c in recipe.get('colors',[]):result[int(c['filament_id'])]+=Decimal(c['grams'])*units
    return dict(result)


def jobs(erp):
    result=[]
    for j in erp.s.rows('SELECT j.*,p.name,p.model,o.status order_status FROM production_jobs j JOIN products p ON p.id=j.product_id LEFT JOIN orders o ON o.id=j.order_id ORDER BY j.id DESC'):
        recipe=json.loads(j['recipe']);current=erp.s.one('SELECT qty,product_id FROM order_items WHERE order_id=? AND item_key=?',(j['order_id'],j['item_key'])) if j['order_id'] else None
        warnings=[]
        if j['order_id'] and (not current or current['qty']!=j['units'] or current['product_id']!=j['product_id']):warnings.append('Pedido/quantidade alterados; revisar lote')
        if j['order_status'] and status_kind(j['order_status'])=='cancelado':warnings.append('Pedido cancelado; revisar material já baixado')
        if not recipe.get('colors'):warnings.append('Sem cores/filamentos definidos')
        result.append({**j,'order_id':j['order_id'] or 'Avulso','grams':str(Decimal(recipe['grams'])*j['units']),'hours':str(Decimal(recipe['hours'])*j['units']),
                       'pending':'; '.join(warnings),'recipe_missing':', '.join(recipe.get('missing',[]))})
    return result


def create_job(erp,pid,units,order_id=None,item_key=None,due=None):
    units=quantity(units);erp.product(pid);recipe=erp.cost(pid)
    with erp.s.transaction():
        if order_id:
            order=erp.s.one('SELECT status FROM orders WHERE id=?',(order_id,))
            if not order or status_kind(order['status'])=='cancelado':raise ValueError('Pedido não disponível para produção.')
        jid=erp.s.db.execute("INSERT INTO production_jobs(order_id,item_key,product_id,units,state,recipe,created,due) VALUES(?,?,?,?,'A produzir',?,?,?)",
                            (order_id,item_key or str(uuid4()),pid,units,json.dumps(recipe,ensure_ascii=False),datetime.now().isoformat(timespec='seconds'),day(due) if due else None)).lastrowid
        erp.s.log('lote_criado',{'lote':jid,'produto':pid,'unidades':units})
    return jid


def sync_jobs(erp):
    count=0
    for i in erp.s.rows('SELECT i.*,o.status FROM order_items i JOIN orders o ON o.id=i.order_id WHERE i.product_id IS NOT NULL'):
        if status_kind(i['status'])!='ativo' or not any(word in i['status'].lower() for word in ('enviar','to ship','process','a produzir')):continue
        if not erp.s.one('SELECT id FROM production_jobs WHERE order_id=? AND item_key=?',(i['order_id'],i['item_key'])):
            create_job(erp,i['product_id'],i['qty'],i['order_id'],i['item_key']);count+=1
    return count


def refresh_job(erp,jid):
    j=erp.s.one('SELECT * FROM production_jobs WHERE id=?',(jid,))
    if not j or j['state']!='A produzir' or erp.s.one('SELECT id FROM production_events WHERE job_id=?',(jid,)):raise ValueError('Somente lote não iniciado e sem eventos pode atualizar a previsão.')
    current=erp.s.one('SELECT qty,product_id FROM order_items WHERE order_id=? AND item_key=?',(j['order_id'],j['item_key'])) if j['order_id'] else None
    if j['order_id'] and (not current or current['product_id'] is None):raise ValueError('Item do pedido removido ou sem produto; revise o vínculo antes de atualizar.')
    pid=current['product_id'] if current else j['product_id'];qty=current['qty'] if current else j['units'];recipe=erp.cost(pid)
    with erp.s.transaction():
        erp.s.db.execute('UPDATE production_jobs SET units=?,recipe=?,product_id=? WHERE id=?',(qty,json.dumps(recipe,ensure_ascii=False),pid,jid))
        erp.s.log('previsao_lote_atualizada',{'lote':jid,'unidades':qty})


def stock(erp):
    reserved=defaultdict(Decimal);unknown=0
    for j in erp.s.rows("SELECT recipe,units FROM production_jobs WHERE state IN('A produzir','Em impressão','Acabamento')"):
        recipe=json.loads(j['recipe'])
        if not recipe.get('colors'):unknown+=j['units']
        for fid,g in recipe_materials(recipe,j['units']).items():reserved[fid]+=g
    result=[]
    for f in erp.s.rows('SELECT * FROM filaments ORDER BY material,color'):
        rolls=erp.s.rows('SELECT * FROM stock_rolls WHERE filament_id=?',(f['id'],))
        balance=sum((roll_balance(erp.s,r['id']) for r in rolls),Decimal(0))
        threshold=max((Decimal(r['minimum_grams']) for r in rolls),default=Decimal(100))
        result.append({**f,'grams':str(balance),'reserved_grams':str(reserved[f['id']]),'available_grams':str(balance-reserved[f['id']]),
                       'shortage_grams':str(max(Decimal(0),reserved[f['id']]-balance)), 'minimum_grams':str(threshold),
                       'alert':'Sem saldo físico cadastrado' if not rolls else ('INSUFICIENTE' if balance<reserved[f['id']] else ('Saldo baixo' if balance<threshold else 'OK')),
                       'unknown_units':unknown})
    return result


def rolls(erp):
    rows=erp.s.rows('SELECT r.*,f.material,f.color FROM stock_rolls r JOIN filaments f ON f.id=r.filament_id ORDER BY r.id')
    for r in rows:r['grams']=str(roll_balance(erp.s,r['id']))
    return rows


def _consume(s,requirements,event_id,when,reason):
    for fid,g in requirements.items():
        candidates=s.rows('SELECT id FROM stock_rolls WHERE filament_id=? ORDER BY added,id',(fid,))
        if sum((roll_balance(s,r['id']) for r in candidates),Decimal(0))<g:raise ValueError(f'Estoque insuficiente para o filamento #{fid}. Cadastre/ajuste o saldo físico; não é permitido saldo negativo.')
    for fid,g in requirements.items():
        remaining=g
        for r in s.rows('SELECT id FROM stock_rolls WHERE filament_id=? ORDER BY added,id',(fid,)):
            used=min(remaining,roll_balance(s,r['id']))
            if used>0:
                s.db.execute('INSERT INTO stock_moves(roll_id,date,delta_grams,reason,ref,event_id) VALUES(?,?,?,?,?,?)',
                             (r['id'],when,str(-used),reason,f'evento:{event_id}:rolo:{r["id"]}',event_id));remaining-=used
            if remaining<=0:break


def change_state(erp,jid,state):
    if state not in STATES:raise ValueError('Etapa de produção inválida.')
    s=erp.s
    with s.transaction():
        j=s.one('SELECT * FROM production_jobs WHERE id=?',(jid,))
        if not j:raise ValueError('Lote não encontrado.')
        consumed=s.one("SELECT id FROM production_events WHERE job_id=? AND kind='consumo'",(jid,))
        if j['state']==state:return False
        if consumed and state not in ('Pronto','Cancelado'):raise ValueError('Lote já baixado não pode voltar de etapa. Registre reimpressão/perda separadamente.')
        if j['state']=='Cancelado':raise ValueError('Lote cancelado não é reaberto automaticamente; crie novo lote após revisar o pedido.')
        if state=='Pronto' and not consumed:
            if j['order_id']:
                order=s.one('SELECT status FROM orders WHERE id=?',(j['order_id'],));item=s.one('SELECT qty,product_id FROM order_items WHERE order_id=? AND item_key=?',(j['order_id'],j['item_key']))
                if status_kind(order['status'])=='cancelado' or not item or item['qty']!=j['units'] or item['product_id']!=j['product_id']:raise ValueError('Pedido cancelado/alterado. Revise o lote antes de confirmar.')
            recipe=json.loads(j['recipe']);requirements=recipe_materials(recipe,j['units'])
            if not requirements or recipe.get('missing'):raise ValueError('Complete a receita do lote (cores, peso, tempo e custos) e atualize a previsão antes de finalizar.')
            eid=s.db.execute("INSERT INTO production_events(job_id,kind,date,grams,hours,value_cents,detail) VALUES(?,'consumo',?,?,?,?,?)",
                (jid,day(date.today()),str(sum(requirements.values(),Decimal(0))),str(Decimal(recipe['hours'])*j['units']),recipe['total_cents']*j['units'],json.dumps({'recipe':recipe,'units':j['units']},ensure_ascii=False))).lastrowid
            _consume(s,requirements,eid,day(date.today()),'Baixa por receita confirmada do lote')
        s.db.execute('UPDATE production_jobs SET state=? WHERE id=?',(state,jid));s.log('etapa_producao',{'lote':jid,'antes':j['state'],'depois':state})
    return True


def record_loss(erp,fid,grams,hours,reason,when=None,jid=None,already_deducted=False):
    grams=decimal(grams);hours=decimal(hours)
    if grams<=0:raise ValueError('Informe gramas adicionais perdidos.')
    if not reason.strip():raise ValueError('Informe motivo da perda.')
    s=erp.s;f=s.one('SELECT * FROM filaments WHERE id=?',(fid,))
    if not f:raise ValueError('Filamento não encontrado.')
    settings=s.settings();material=grams/1000*Decimal(f['kg_cents'])/100
    modeled=hours*(decimal(settings['power_w'])/1000*decimal(settings['energy_kwh'])+decimal(settings['machine_hour']))
    value=round_cents(material+modeled);when=day(when or date.today())
    with s.transaction():
        eid=s.db.execute("INSERT INTO production_events(job_id,kind,date,grams,hours,value_cents,detail) VALUES(?,'perda',?,?,?,?,?)",
          (jid,when,str(grams),str(hours),value,json.dumps({'filament_id':fid,'reason':reason.strip(),'already_deducted':already_deducted,'material_cents':round_cents(material),'modeled_cents':round_cents(modeled)},ensure_ascii=False))).lastrowid
        if not already_deducted:_consume(s,{fid:grams},eid,when,'Perda/reimpressão informada pelo operador')
        s.log('perda_producao',{'evento':eid,'gramas':str(grams),'valor_cents':value})
    return eid


def void_loss(erp,eid,reason):
    if not reason.strip():raise ValueError('Informe motivo do estorno.')
    s=erp.s
    with s.transaction():
        event=s.one("SELECT * FROM production_events WHERE id=? AND kind='perda'",(eid,))
        if not event:raise ValueError('Selecione uma perda.')
        if event['voided']:return False
        for move in s.rows('SELECT * FROM stock_moves WHERE event_id=?',(eid,)):
            s.db.execute('INSERT INTO stock_moves(roll_id,date,delta_grams,reason,ref) VALUES(?,?,?,?,?)',
                (move['roll_id'],day(date.today()),str(-Decimal(move['delta_grams'])),'Estorno de perda: '+reason.strip(),'estorno:'+str(move['id'])))
        s.db.execute('UPDATE production_events SET voided=1 WHERE id=?',(eid,));s.log('estorno_perda',{'evento':eid,'motivo':reason.strip()})
    return True


def losses(erp,start,end,pid=None):
    rows=erp.s.rows("SELECT e.*,p.name product_name FROM production_events e LEFT JOIN production_jobs j ON j.id=e.job_id LEFT JOIN products p ON p.id=j.product_id WHERE e.kind='perda' AND e.date BETWEEN ? AND ?"+(' AND j.product_id=?' if pid is not None else ''),(day(start),day(end),pid) if pid is not None else (day(start),day(end)))
    for r in rows:
        d=json.loads(r['detail']);r['reason']=d['reason'];r['filament_id']=d['filament_id']
    return rows
