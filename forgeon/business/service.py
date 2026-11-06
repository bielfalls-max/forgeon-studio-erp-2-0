import json
import re
from datetime import datetime
from .numbers import decimal, cents, quantity, day, norm
from .pricing import calculate


class ERP:
    def __init__(self, store):
        self.s = store

    def product(self, pid):
        p = self.s.one('SELECT * FROM products WHERE id=?', (pid,))
        if not p:
            raise ValueError('Produto não encontrado.')
        return p

    def colors(self, pid):
        return self.s.rows('SELECT c.*,f.material,f.color,f.kg_cents FROM product_colors c JOIN filaments f ON f.id=c.filament_id WHERE product_id=?', (pid,))

    def cost(self, pid):
        return calculate(self.product(pid), self.colors(pid), self.s.settings())

    def save_product(self, data, pid=None):
        name = str(data['name']).strip()
        if not name:
            raise ValueError('Informe o nome do produto.')
        values = (name, str(data.get('model', '')).strip(), str(decimal(data.get('weight', 0), 'Peso')),
                  str(decimal(data.get('hours', 0), 'Horas')), None if str(data.get('manual', '')).strip() == '' else cents(data['manual']),
                  cents(data.get('packaging', 0)), cents(data.get('other', 0)), str(data.get('notes', '')))
        with self.s.transaction():
            if pid:
                self.product(pid)
                self.s.db.execute('UPDATE products SET name=?,model=?,weight=?,hours=?,manual_cents=?,packaging_cents=?,other_cents=?,notes=? WHERE id=?', (*values, pid))
            else:
                pid = self.s.db.execute('INSERT INTO products(name,model,weight,hours,manual_cents,packaging_cents,other_cents,notes) VALUES(?,?,?,?,?,?,?,?)', values).lastrowid
            self.s.log('produto_salvo', {'id': pid})
        return pid

    def archive(self, pid):
        p = self.product(pid)
        with self.s.transaction():
            self.s.db.execute('UPDATE products SET archived=? WHERE id=?', (1 - p['archived'], pid))
            self.s.log('produto_arquivo', {'id': pid, 'arquivado': not p['archived']})

    def filament(self, material, color, kg, fid=None):
        if not material.strip() or not color.strip():
            raise ValueError('Informe material e cor.')
        with self.s.transaction():
            if fid:
                self.s.db.execute('UPDATE filaments SET material=?,color=?,kg_cents=? WHERE id=?', (material.strip(), color.strip(), cents(kg), fid))
            else:
                fid = self.s.db.execute('INSERT INTO filaments(material,color,kg_cents) VALUES(?,?,?)', (material.strip(), color.strip(), cents(kg))).lastrowid
            self.s.log('filamento_salvo', {'id': fid})
        return fid

    def set_color(self, pid, fid, grams):
        self.product(pid)
        grams = decimal(grams, 'Gramas')
        with self.s.transaction():
            if grams == 0:
                self.s.db.execute('DELETE FROM product_colors WHERE product_id=? AND filament_id=?', (pid, fid))
            else:
                self.s.db.execute('INSERT INTO product_colors VALUES(?,?,?) ON CONFLICT(product_id,filament_id) DO UPDATE SET grams=excluded.grams', (pid, fid, str(grams)))
            self.s.log('cor_produto', {'produto': pid, 'filamento': fid, 'gramas': str(grams)})

    def copy_costs(self, source, target):
        if source == target:
            raise ValueError('Escolha produtos diferentes.')
        p = self.product(source)
        self.product(target)
        with self.s.transaction():
            self.s.db.execute('UPDATE products SET weight=?,hours=?,manual_cents=?,packaging_cents=?,other_cents=? WHERE id=?',
                              (p['weight'], p['hours'], p['manual_cents'], p['packaging_cents'], p['other_cents'], target))
            self.s.db.execute('DELETE FROM product_colors WHERE product_id=?', (target,))
            self.s.db.execute('INSERT INTO product_colors SELECT ?,filament_id,grams FROM product_colors WHERE product_id=?', (target, source))
            self.s.log('copiar_custos', {'origem': source, 'destino': target})

    def save_settings(self, data):
        for key in ('filament_kg','energy_kwh','power_w','machine_hour','fee_percent','fee_fixed','profit_percent'):
            data[key] = str(decimal(data[key], key))
        width = quantity(data['sku_width'])
        if width > 16:
            raise ValueError('Largura do SKU: de 1 a 16.')
        data['sku_width'] = str(width)
        calculate({'weight':'1','hours':'1','manual_cents':None,'packaging_cents':0,'other_cents':0}, [], data)
        with self.s.transaction():
            self.s.db.executemany('UPDATE settings SET value=? WHERE key=?', [(str(v), k) for k, v in data.items() if k in self.s.settings()])
            self.s.log('configuracoes', {'alteradas': list(data)})

    def reserve(self, code=None):
        with self.s.transaction():
            if code is None:
                used = {int(r['code']) for r in self.s.rows('SELECT code FROM sku_codes') if re.fullmatch(r'[0-9]+', r['code'])}
                number = 1
                while number in used:
                    number += 1
                code = str(number).zfill(int(self.s.settings()['sku_width']))
            code = str(code).strip()
            if not code or len(code) > 120:
                raise ValueError('SKU deve conter de 1 a 120 caracteres.')
            if self.s.one('SELECT code FROM sku_codes WHERE code=?', (code,)):
                raise ValueError('Código já reservado, usado ou aposentado.')
            self.s.db.execute("INSERT INTO sku_codes VALUES(?,'reservado')", (code,))
            self.s.log('reservar_sku', {'sku': code})
        return code

    def retire(self, code):
        if self.s.one('SELECT id FROM origins WHERE sku=? AND active=1', (code,)):
            raise ValueError('Desvincule ou corrija as origens ativas antes de aposentar o código.')
        with self.s.transaction():
            self.s.db.execute("UPDATE sku_codes SET state='aposentado' WHERE code=?", (code,))
            self.s.log('aposentar_sku', {'sku': code})

    def origin(self, listing, variation, sku, pid=None, oid=None, source='Shopee'):
        if not listing.strip():
            raise ValueError('Informe o anúncio de origem.')
        sku = str(sku).strip()
        if len(sku) > 120:
            raise ValueError('SKU excede 120 caracteres.')
        if pid:
            self.product(pid)
        with self.s.transaction():
            old = self.s.one('SELECT * FROM origins WHERE id=?', (oid,)) if oid else None
            if sku and (not old or old['sku'] != sku or not old['active']):
                code = self.s.one('SELECT * FROM sku_codes WHERE code=?', (sku,))
                if code and code['state'] == 'aposentado':
                    raise ValueError('Código aposentado: escolha outro.')
                self.s.db.execute("INSERT INTO sku_codes VALUES(?,'usado') ON CONFLICT(code) DO UPDATE SET state='usado'", (sku,))
            if oid:
                self.s.db.execute('UPDATE origins SET listing=?,variation=?,sku=?,product_id=?,source=?,active=1 WHERE id=?', (listing.strip(), variation.strip(), sku, pid, source, oid))
            else:
                oid = self.s.db.execute('INSERT INTO origins(listing,variation,sku,product_id,source) VALUES(?,?,?,?,?)', (listing.strip(), variation.strip(), sku, pid, source)).lastrowid
            # Correct identification on existing orders; original SKU and frozen cost remain untouched.
            self.s.db.execute('UPDATE order_items SET product_id=? WHERE origin_id=?', (pid, oid))
            self.s.log('vinculo_origem', {'id': oid, 'anterior': old, 'produto': pid, 'sku': sku})
        return oid

    def unlink(self, oid):
        with self.s.transaction():
            self.s.db.execute('UPDATE origins SET active=0,product_id=NULL WHERE id=?', (oid,))
            # Order product IDs and costs are intentionally preserved on detachment.
            self.s.log('desvincular_origem', {'id': oid})

    def conflicts(self):
        return {r['sku'] for r in self.s.rows("SELECT sku FROM origins WHERE sku<>'' AND active=1 AND product_id IS NOT NULL GROUP BY sku HAVING count(DISTINCT product_id)>1")}

    def suggestions(self, listing, variation):
        # Advisory only. Exact normalized model/name or a cosmetic suffix is suggested, never merged.
        key = norm(variation or listing)
        result = []
        for p in self.s.rows('SELECT * FROM products WHERE archived=0'):
            candidate = norm(p['name'])
            exact = key == candidate
            cosmetic = key.split(' - ')[0] == candidate
            if exact or cosmetic:
                result.append(p)
        return result

    def expense(self, date, category, description, amount):
        if not category.strip():
            raise ValueError('Informe categoria.')
        with self.s.transaction():
            self.s.db.execute('INSERT INTO expenses(date,category,description,amount_cents) VALUES(?,?,?,?)', (day(date), category.strip(), description, cents(amount)))
            self.s.log('despesa', {'categoria': category})

    def purchase(self, date, fid, grams, amount, freight):
        grams = decimal(grams, 'Peso comprado')
        if grams <= 0:
            raise ValueError('Peso comprado deve ser positivo.')
        with self.s.transaction():
            self.s.db.execute('INSERT INTO purchases(date,filament_id,grams,amount_cents,freight_cents) VALUES(?,?,?,?,?)', (day(date), fid, str(grams), cents(amount), cents(freight)))
            self.s.log('compra_filamento', {'filamento': fid})

    def freeze_missing_costs(self):
        count = 0
        with self.s.transaction():
            for item in self.s.rows('SELECT * FROM order_items WHERE cost_cents IS NULL AND product_id IS NOT NULL'):
                cost = self.cost(item['product_id'])
                if cost['missing']:
                    continue
                self.s.db.execute('UPDATE order_items SET cost_cents=?,cost_detail=?,cost_at=? WHERE id=?',
                                  (cost['total_cents'], json.dumps(cost, ensure_ascii=False), datetime.now().isoformat(timespec='seconds'), item['id']))
                count += 1
            self.s.log('congelar_custos_pendentes', {'itens': count})
        return count
