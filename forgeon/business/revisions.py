from datetime import datetime
import json


def record_revision(erp,pid,reason):
    data={'reason':reason,'product':erp.product(pid),'colors':erp.colors(pid),'cost':erp.cost(pid)}
    erp.s.db.execute('INSERT INTO recipe_revisions(product_id,recorded,detail) VALUES(?,?,?)',(pid,datetime.now().isoformat(timespec='seconds'),json.dumps(data,ensure_ascii=False)))


def revisions(erp,pid):
    rows=erp.s.rows('SELECT * FROM recipe_revisions WHERE product_id=? ORDER BY id DESC',(pid,))
    for r in rows:
        data=json.loads(r['detail']);c=data['cost'];r.update(reason=data['reason'],grams=c['grams'],hours=c['hours'],total_cents=c['total_cents'],colors='; '.join(x['color']+': '+x['grams']+' g' for x in c['colors']))
    return rows
