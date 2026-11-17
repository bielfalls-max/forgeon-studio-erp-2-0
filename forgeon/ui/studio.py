from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import QLabel,QPushButton,QHBoxLayout,QGridLayout
from .widgets import Page,Table
from .visual import GlassCard,MetricCard
from .charts import ChartCard
from .management import ui_action
from ..business import studio
from ..business.numbers import money,cents
from ..reports.finance import report,monthly

class StudioMixin:
    def build_supplies(self):
        p=Page('Materiais e compras','Filamento, caixas, plástico bolha, cola e ferramentas. Compras entram no gasto do mês; consumo por produto entra na precificação.')
        p.button('Comprar insumo / embalagem',self.buy_supply,True);p.button('Comprar filamento',self.add_purchase);p.button('Vincular consumo ao produto',self.assign_supply);p.button('Despesa / utensílio',self.add_expense)
        self.add_filters(p,'supplies',dates=True,date_label='Data das compras')
        self.supplies_summary=QLabel();self.supplies_summary.setWordWrap(True);p.layout.addWidget(self.supplies_summary)
        self.filament_needs_table=p.table();self.supplies_table=p.table();self.supply_purchases_table=p.table()
        return p,self.refresh_supplies

    @ui_action
    def refresh_supplies(self):
        filaments,unknown=studio.filament_needs(self.erp)
        self.filament_needs_table.fill(filaments,[('material','Filamento'),('color','Cor'),('balance','Saldo estimado g'),('needed','Pedidos abertos g'),('buy','Comprar g · estimativa')])
        filters=self.supplies_filters.values()
        from ..business.filtering import date_matches
        self.supplies_table.fill(studio.needs(self.erp),[('name','Material'),('category','Categoria'),('unit','Unidade'),('unit_price','Custo/un. com frete'),('balance','Saldo estimado'),('needed','Para pedidos abertos'),('buy','Comprar · estimado')])
        rows=[r for r in self.s.rows('SELECT p.*,s.name,s.unit FROM supply_purchases p JOIN supplies s ON s.id=p.supply_id ORDER BY date DESC,id DESC') if date_matches(r['date'],filters)]
        self.supply_purchases_table.fill(rows,[('date','Compra'),('name','Material'),('quantity','Quantidade'),('unit','Unidade'),('amount_cents','Material R$'),('freight_cents','Frete R$')])
        self.supplies_summary.setText('Compras no filtro: '+money(sum(r['amount_cents']+r['freight_cents'] for r in rows))+f'. {unknown} unidades vendidas sem receita de filamento. Saldo e sugestão usam compras cadastradas menos consumo estimado das vendas e vínculos por produto. Cadastre o saldo inicial como compra somente se ela ainda não foi lançada; valores históricos devem usar a data real.')

    @ui_action
    def buy_supply(self):
        value=self.form('Compra de material / embalagem',[('name','Nome (ex.: caixa 15×15 ou cola)',''),('category','Categoria',[('Embalagem','Embalagem'),('Cola / acabamento','Acabamento'),('Consumível','Consumível'),('Utensílio / ferramenta (despesa)','Ferramentas')]),('unit','Unidade',[('Unidades','un'),('Gramas','g'),('Metros','m'),('Mililitros','ml')]),('quantity','Quantidade comprada','1'),('amount','Valor total dos itens R$','0'),('freight','Frete desta compra R$','0'),('when','Data',date.today().strftime('%d/%m/%Y'))], 'Informe o frete só uma vez, rateado se a nota tiver outros itens. Ferramenta durável entra em Despesa / utensílio. Depois vincule quanto cada produto usa para calcular o custo unitário.')
        if value:studio.buy(self.erp,**value);self.refresh_supplies()

    @ui_action
    def assign_supply(self):
        options=[(r['name']+' / '+r['unit'],r['id']) for r in self.s.rows('SELECT * FROM supplies ORDER BY name')]
        if not options or not self.product_options():raise ValueError('Cadastre uma compra de insumo e um produto primeiro.')
        value=self.form('Consumo por produto',[('pid','Produto',self.product_options()),('sid','Material',options),('quantity','Quantidade por unidade vendida','1')], 'Ex.: 1 caixa, 0,5 metro de bolha, 2 gramas de cola. Zero remove o vínculo. Este custo soma aos Outros do produto: retire qualquer valor manual que já represente o mesmo material. Pedidos congelados ficam preservados.')
        if value:studio.assign(self.erp,**value);self.refresh_supplies()

    @ui_action
    def friendly_price(self):
        pid=self.pricing_product.currentData()
        if pid is None:raise ValueError('Escolha um produto primeiro.')
        cost=self.erp.cost(pid)
        if cost['missing']:raise ValueError('Complete a receita do produto em Produtos → Editar / 3MF. Falta: '+', '.join(cost['missing']))
        value=self.form('Por quanto posso vender?',[('price','Preço que pretende cobrar R$',str(Decimal(cost['suggested_cents'])/100))], 'O custo completo já inclui os insumos vinculados, embalagem, outros, filamento, energia e máquina. Taxas usadas: as configuradas em Custos e taxas.')
        if value:
            price=cents(value['price']);settings=self.s.settings();fee=int((Decimal(price)*Decimal(settings['fee_percent'])/100+Decimal(settings['fee_fixed'])*100).quantize(Decimal('1')));profit=price-fee-cost['total_cents']
            self.info(f"Preço: {money(price)}\nCusto completo: {money(cost['total_cents'])}\nTaxas estimadas: {money(fee)}\nSobra por unidade: {money(profit)}\nMargem: {Decimal(profit)/price*100 if price else 0:.1f}%\nAntes das despesas gerais. Referência calculada com seus custos cadastrados.")

    def install_financial_filters(self):
        from .filters import Filters
        self.chart_filters=[]
        for index,card in enumerate(self.report_charts):
            fields=Filters(self.erp,dates=True,product=True);card.body.insertWidget(1,fields);self.chart_filters.append(fields)
            fields.changed.connect(lambda i=index:self.refresh_financial_chart(i))

    @ui_action
    def refresh_financial_chart(self,index):
        filters=self.chart_filters[index].values();r=report(self.erp,filters.get('start') or self.report_start.text(),filters.get('end') or self.report_end.text(),filters.get('product'))
        card=self.report_charts[index]
        if index==0:card.line(r['sales_by_day'])
        elif index==1:card.donut([('Produção',r['production_cents']),('Taxas',r['fees_cents']),('Despesas',r['expenses_cents']),('Perdas',r['losses_cents'])])
        elif index==2:card.bars(r['best_sellers'],'product','qty')
        else:card.bars(self.monthly_spending(r),'month','amount_cents','R$')
        card.caption.setText('Período deste gráfico · '+r['start']+' a '+r['end']+(' · Dados parciais' if r['partial'] else ''))

    def monthly_spending(self,r):
        values={}
        for row in r['expenses']+r['purchases']+r['supply_purchases']:
            month=row['date'][:7];values[month]=values.get(month,0)+row['amount_cents']+row.get('freight_cents',0)
        return [{'month':key,'amount_cents':value} for key,value in sorted(values.items())]

    @ui_action
    def unify_products(self):
        from ..business.unification import proposals,apply
        from PySide6.QtWidgets import QDialog,QVBoxLayout,QDialogButtonBox
        rows=proposals(self.erp)
        if not rows:self.info('O catálogo já foi normalizado automaticamente. Não há grupos repetidos compatíveis pendentes. Tamanhos/variantes desconhecidos precisam de revisão pelo cadastro.');return
        d=QDialog(self);d.setWindowTitle('Unificar produtos por nome e tamanho');d.resize(1050,600);layout=QVBoxLayout(d)
        note=QLabel('Padrão informado: personagens reconhecidos sem tamanho explícito usam 12 cm. Tamanhos explícitos (ex.: 16 cm) permanecem separados. Sonic, Super Sonic, Metal Sonic e Shadow são produtos distintos. Só grupos sem receitas/custos conflitantes serão unificados; origens e pedidos são preservados e haverá backup.');note.setWordWrap(True);layout.addWidget(note)
        table=Table();table.fill(rows,[('name','Boneco'),('size','Tamanho'),('count','Cadastros encontrados'),('target','Cadastro mantido'),('sources','Cadastros arquivados'),('status','Revisão')]);layout.addWidget(table)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Unificar grupos compatíveis');buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(any(r['safe'] for r in rows));buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);layout.addWidget(buttons)
        if d.exec()==QDialog.DialogCode.Accepted:
            count=apply(self.erp,rows);self.refresh();self.info(f'{count} cadastros repetidos arquivados e vinculados ao produto físico. Receitas conflitantes ficaram para revisão. Pedidos e custos históricos preservados.')
