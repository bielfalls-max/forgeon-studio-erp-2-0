"""Filtros consistentes e atalhos para a fonte única dos custos."""
import json
from decimal import Decimal
from PySide6.QtWidgets import QLabel
from .filters import Filters
from .management import ui_action
from ..business.filtering import date_matches,item_matches,recipe_matches
from ..business.numbers import norm,money
from ..business import costs,workshop
from ..business.organization import preference

class RefinementMixin:
    def add_filters(self,page,name,**options):
        filters=Filters(self.erp,**options);setattr(self,name+'_filters',filters);page.layout.addWidget(filters)
        filters.changed.connect(lambda:self.apply_filter(name))
        return filters

    @ui_action
    def apply_filter(self,name):
        getattr(self,name+'_filters').values()
        callbacks={'pricing':self.update_pricing,'products':self.update_products,'orders':self.update_orders,'finance':self.update_finance,'materials':self.update_colors,'production':self.refresh_production,'stock':self.refresh_stock,'simulation':self.calculate_scenario}
        callbacks[name]()

    def material_filter_matches(self,row,filters):
        return (not filters.get('material') or norm(filters['material']) in norm(row['material'])) and (not filters.get('color') or norm(filters['color']) in norm(row['color']))

    def visible_products(self):
        filters=self.products_filters.values();q=norm(self.product_search.text())
        return [r for r in self.product_rows() if (self.show_archived.isChecked() or not r['archived']) and q in norm(r['name']+' '+r['model']+' '+r['skus']) and recipe_matches(self.erp.cost(r['id']),filters)]

    def priced_products(self):
        filters=self.pricing_filters.values()
        return [r for r in self.product_rows() if not r['archived'] and recipe_matches(self.erp.cost(r['id']),filters)]

    def order_filter_items(self,oid):
        return self.s.rows('SELECT i.*,u.detail usage_detail FROM order_items i LEFT JOIN item_usage u ON u.item_id=i.id WHERE order_id=?',(oid,))

    def filtered_order_items(self):
        filters=self.orders_filters.values()
        return [i for order in self.filtered_orders() for i in self.order_filter_items(order['id']) if item_matches(i,filters)]

    def filtered_expenses(self):
        filters=self.finance_filters.values();q=norm(self.finance_query.text())
        # Filament-only searches intentionally hide unassignable general expenses.
        return [r for r in self.s.rows('SELECT * FROM expenses ORDER BY date DESC,id DESC') if not filters.get('material') and not filters.get('color') and date_matches(r['date'],filters) and q in norm(r['category']+' '+r['description'])]

    def filtered_purchases(self):
        filters=self.finance_filters.values();q=norm(self.finance_query.text())
        return [r for r in self.purchase_rows() if date_matches(r['date'],filters) and self.material_filter_matches(r,filters) and q in norm(str(r['id'])+' '+r['material']+' '+r['color'])]

    def filtered_losses(self,filters,q='',state=''):
        rows=workshop.losses(self.erp,filters.get('start') or '1900-01-01',filters.get('end') or '9999-12-31',filters.get('product'))
        result=[]
        for row in rows:
            job=self.s.one('SELECT * FROM production_jobs WHERE id=?',(row['job_id'],)) if row['job_id'] else None
            filament=self.s.one('SELECT material,color FROM filaments WHERE id=?',(row['filament_id'],))
            oid=(job['order_id'] or 'Avulso') if job else ''
            if state and (not job or job['state']!=state):continue
            if norm(filters.get('order','')) not in norm(oid):continue
            if not self.material_filter_matches(filament,filters):continue
            if q not in norm(f"{row['id']} {row['job_id'] or ''} {oid} {row['product_name'] or ''} {row['reason']}"):continue
            result.append({**row,'material':filament['material'],'color':filament['color'],'order_id':oid})
        return result

    def current_material_costs(self):
        filters=self.materials_filters.values()
        return [row for row in costs.material_costs(self.erp) if self.material_filter_matches(row,filters)]

    def cost_review_text(self):
        reviewed=preference(self.s,'cost:settings',{})
        prefix=('Parâmetros revisados em '+reviewed['reviewed'][:10]) if reviewed else 'Estimativas iniciais editáveis: energia SP R$ 1,10/kWh; perdas 10%; mão de obra R$ 2/un. Confira em Editar custos e taxas e Perfis de impressoras.'
        return prefix+' · Alterações valem para novas estimativas; custos dos pedidos já congelados são preservados. Preços por kg ficam em Materiais → Cores e preços/kg.'

    @ui_action
    def use_purchase_cost(self):
        row=self.filament_table.selected()
        if row['purchase_id'] is None:raise ValueError('Registre uma compra deste filamento para obter seu preço pago por kg.')
        if self.ask('Usar custo pago como referência?',f"Atualizar {row['material']} / {row['color']} para {money(row['purchase_kg_cents'])}/kg, incluindo o frete da compra de {row['purchase_date']}? Custos congelados e receitas dos lotes existentes serão preservados."):
            costs.use_purchase(self.erp,row['id'],row['purchase_id']);self.update_colors()

    @ui_action
    def edit_priced_product(self):
        pid=self.pricing_product.currentData()
        if pid is None:raise ValueError('Selecione um produto para editar embalagem, outros custos, peso e tempo.')
        self.edit_product(pid)

    def open_pricing_scenario(self):
        pid=self.pricing_product.currentData();self.nav.setCurrentRow(14)
        if pid is not None:self.sim_product.setCurrentIndex(self.sim_product.findData(pid))

    def production_actions(self,index):
        self.production_stage_button.setVisible(index==0);self.production_recipe_button.setVisible(index==0);self.production_reverse_button.setVisible(index==2)

    @ui_action
    def edit_sku_format(self):
        settings=self.s.settings();value=self.form('Formato dos SKUs',[('width','Dígitos do próximo SKU',settings['sku_width'])],'Altera somente novos códigos; códigos existentes não são renumerados.')
        if value:
            from ..business.numbers import quantity
            width=quantity(value['width'])
            if width>16:raise ValueError('Largura do SKU: de 1 a 16.')
            with self.s.transaction():
                self.s.db.execute("UPDATE settings SET value=? WHERE key='sku_width'",(str(width),));self.s.log('formato_sku',{'digitos':width})
            self.refresh()

    def refresh_order_statuses(self):
        selected=self.order_status.currentData();self.order_status.blockSignals(True)
        while self.order_status.count()>4:self.order_status.removeItem(4)
        for row in self.s.rows('SELECT DISTINCT status FROM orders ORDER BY status'):self.order_status.addItem(row['status'],'texto:'+row['status'])
        self.order_status.setCurrentIndex(max(0,self.order_status.findData(selected)));self.order_status.blockSignals(False)

    def filtered_receipts(self):
        from ..business import management as mgmt
        from ..business.numbers import day
        start,end=day(self.receipt_start.text()),day(self.receipt_end.text())
        order_start,order_end=day(self.receipt_order_start.text()),day(self.receipt_order_end.text())
        if end<start or order_end<order_start:raise ValueError('Período de datas inválido.')
        oid=norm(self.receipts_filters.values().get('order',''));q=norm(self.receipt_search.text())
        all_links=self.s.rows('SELECT l.*,r.reference,r.date,r.note FROM settlement_links l JOIN settlements r ON r.id=l.settlement_id ORDER BY r.date DESC')
        rows=[]
        for row in mgmt.receipt_rows(self.erp,start,end):
            matching_orders=[link for link in all_links if link['settlement_id']==row['id'] and oid in norm(link['order_id'])]
            if (not oid or matching_orders) and q in norm(row['reference']+' '+row['note']):rows.append(row)
        visible_ids={row['id'] for row in rows}
        links=[link for link in all_links if link['settlement_id'] in visible_ids and oid in norm(link['order_id'])]
        reconciliation=[]
        for row in mgmt.reconciliation(self.erp,order_start,order_end):
            if oid not in norm(row['id']):continue
            if q and not any(link['order_id']==row['id'] and q in norm(link['reference']+' '+link['note']) for link in all_links):continue
            reconciliation.append(row)
        return rows,reconciliation,links

    @ui_action
    def compare_pricing_products(self):
        from PySide6.QtWidgets import QDialog,QVBoxLayout,QPushButton
        self.update_pricing();dialog=QDialog(self);dialog.setWindowTitle('Comparar custos e preços · filtros atuais');dialog.resize(1000,600);layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Selecione um produto para usar sua composição na precificação. Os valores são referências atuais, não custos históricos.'))
        parent=self.pricing_catalog.parentWidget();self.pricing_catalog.setParent(dialog);layout.addWidget(self.pricing_catalog);self.pricing_catalog.show()
        button=QPushButton('Usar produto selecionado');button.clicked.connect(dialog.accept);layout.addWidget(button)
        try:dialog.exec()
        finally:self.pricing_catalog.setParent(parent);self.pricing_catalog.hide()
