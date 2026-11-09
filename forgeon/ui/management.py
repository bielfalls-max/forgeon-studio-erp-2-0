from datetime import date
from decimal import Decimal
from pathlib import Path
from functools import wraps
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QPushButton,QDialogButtonBox,QComboBox,QLineEdit,QTabWidget,QHBoxLayout,QFileDialog,QMessageBox,QWidget,QTableWidget,QTableWidgetItem,QHeaderView)
from .widgets import Page,Table,Form,preview
from .visual import GlassCard,MetricCard
from .production import number_text,hours_text
from ..business.numbers import money,day,norm
from ..business import organization as org,workshop as shop,management as mgmt
from ..business.revisions import revisions
from ..importers.sheets import read_xlsx
from ..reports.xlsx import export,templates


def ui_action(fn):
    @wraps(fn)
    def call(self,*a,**k):
        try:return fn(self,*a,**k)
        except Exception as error:QMessageBox.warning(self,'FORGEON · Verifique os dados',str(error))
    return call


class ManagementMixin:
    def build_pending(self):
        p=Page('Pendências do estúdio','Reúna o que falta cadastrar e corrija a origem do problema sem perder pedidos ou custos congelados.')
        self.pending_query=QLineEdit();self.pending_query.setPlaceholderText('Buscar referência ou descrição');p.toolbar.addWidget(self.pending_query)
        self.pending_kind=QComboBox();self.pending_kind.addItem('Todas as pendências','')
        for kind in ('Cadastro de produto','Origem sem vínculo','Conflito de SKU','Custo pendente','Revisar preço zero','Pedido cancelado na produção'):self.pending_kind.addItem(kind,kind)
        p.toolbar.addWidget(self.pending_kind);p.button('Atualizar',self.refresh_pending,True);p.button('Abrir cadastro',self.open_pending);p.button('Revisar vínculos em lote',self.bulk_links)
        self.pending_label=QLabel();self.pending_label.setObjectName('badge');p.layout.addWidget(self.pending_label);self.pending_table=p.table()
        self.pending_query.textChanged.connect(self.refresh_pending);self.pending_kind.currentIndexChanged.connect(self.refresh_pending)
        return p,self.refresh_pending

    @ui_action
    def refresh_pending(self,*args):
        rows=org.pending(self.erp);q=norm(self.pending_query.text());kind=self.pending_kind.currentData()
        selected=[r for r in rows if (not kind or r['type']==kind) and q in norm(r['reference']+' '+r['description'])]
        self.pending_label.setText(f'{len(rows)} pendências encontradas · {len(selected)} no filtro · use Abrir cadastro para resolver')
        self.pending_table.fill(selected,[('type','Tipo'),('reference','Referência'),('description','Descrição'),('target','Onde resolver')],lambda r:r['type']=='Conflito de SKU')

    @ui_action
    def open_pending(self):self.open_reference(self.pending_table.selected())

    def open_reference(self,row):
        target=row['target'];reference=row['reference']
        if target=='Produtos':self.last_product_id=int(reference)
        self.nav.setCurrentRow(self.nav_titles.index(target))
        if target=='Catálogo e SKUs':
            self.sku_search.setText(reference if row['type']=='Conflito de SKU' else '')
            if row['type']!='Conflito de SKU':
                for index,item in enumerate(self.origins_table.records):
                    if str(item['id'])==reference:
                        for visual in range(self.origins_table.rowCount()):
                            if self.origins_table.records[self.origins_table.item(visual,0).data(Qt.ItemDataRole.UserRole)]['id']==item['id']:self.origins_table.selectRow(visual)
        if target=='Pedidos':self.order_status.setCurrentIndex(0);self.order_search.setText(reference)
        if target=='Produção':self.production_query.setText(reference)

    @ui_action
    def bulk_links(self):
        options=self.product_options()
        if not options:raise ValueError('Cadastre os produtos físicos antes de revisar os vínculos.')
        origins=self.s.rows('SELECT * FROM origins WHERE active=1 AND product_id IS NULL ORDER BY listing,variation')
        if not origins:self.info('Não há origens ativas sem vínculo.');return
        dialog=QDialog(self);dialog.setWindowTitle('Revisão explícita dos vínculos');dialog.resize(1100,650);layout=QVBoxLayout(dialog)
        note=QLabel('Escolha um produto físico por origem. Confira personagem, cor e tamanho. A confirmação é transacional; SKU original e custos congelados são preservados. Custos pendentes completos serão registrados com data atual.');note.setWordWrap(True);layout.addWidget(note)
        table=QTableWidget(len(origins),4);table.setHorizontalHeaderLabels(['Anúncio','Variação','SKU original','Produto físico (revisar)']);combos=[]
        for index,row in enumerate(origins):
            for col,key in enumerate(('listing','variation','sku')):
                item=QTableWidgetItem(row[key]);item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);table.setItem(index,col,item)
            combo=QComboBox();combo.addItem('Não alterar',None)
            for label,pid in options:combo.addItem(label,pid)
            guess=self.erp.match_product(row['listing'],row['variation'])
            if guess:combo.setCurrentIndex(combo.findData(guess))
            table.setCellWidget(index,3,combo);combos.append(combo)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(table)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            links=[(row['id'],combo.currentData()) for row,combo in zip(origins,combos) if combo.currentData() is not None]
            if not links:self.info('Nenhum vínculo selecionado.');return
            org.apply_links(self.erp,links);self.refresh();self.info(f'{len(links)} vínculos revisados. Conflitos de SKU continuam visíveis no catálogo, se houver.')

    def build_production(self):
        p=Page('Produção e reimpressões','Planeje lotes e registre etapas. Filamento reservado só é baixado quando você confirma Pronto ou registra uma perda.')
        self.production_query=QLineEdit();self.production_query.setPlaceholderText('Buscar lote, pedido ou produto');p.toolbar.addWidget(self.production_query)
        self.production_state=QComboBox();self.production_state.addItem('Todas as etapas','')
        for state in shop.STATES:self.production_state.addItem(state,state)
        p.toolbar.addWidget(self.production_state)
        p.button('Sincronizar A Enviar',self.sync_production,True);p.button('Novo lote',self.new_job);p.button('Mudar etapa / Pronto',self.job_state);p.button('Atualizar previsão',self.refresh_job_recipe);p.button('Registrar perda',self.new_loss);p.button('Estornar perda',self.reverse_loss)
        self.production_note=QLabel('Receitas de lotes são snapshots. Pedidos alterados/cancelados exigem revisão. Filtros selecionam lotes/necessidades; perdas mostram todo o histórico.');self.production_note.setWordWrap(True);self.production_note.setObjectName('badge');p.layout.addWidget(self.production_note)
        self.production_tabs=QTabWidget();self.jobs_table=Table();self.needs_table=Table();self.losses_table=Table()
        for title,table in [('Lotes',self.jobs_table),('Necessidades',self.needs_table),('Perdas e reimpressões',self.losses_table)]:self.production_tabs.addTab(table,title)
        p.layout.addWidget(self.production_tabs);p.button('Exportar produção',self.export_production)
        self.production_query.textChanged.connect(self.refresh_production);self.production_state.currentIndexChanged.connect(self.refresh_production)
        return p,self.refresh_production

    @ui_action
    def refresh_production(self,*args):
        rows=shop.jobs(self.erp);q=norm(self.production_query.text());state=self.production_state.currentData()
        selected=[r for r in rows if (not state or r['state']==state) and q in norm(f"{r['id']} {r['order_id'] or ''} {r['name']} {r['model']}")]
        self.jobs_table.fill(selected,[('id','Lote'),('order_id','Pedido'),('name','Produto'),('units','Unidades'),('state','Etapa'),('due','Prazo'),('grams','Filamento g'),('hours','Impressão h'),('pending','Revisão necessária'),('recipe_missing','Receita incompleta')],lambda r:bool(r['pending'] or r['recipe_missing']))
        grouped={}
        for r in selected:
            if r['state'] in ('Pronto','Cancelado'):continue
            bucket=grouped.setdefault(r['product_id'],{'product':r['name'],'qty':0,'grams':Decimal(0),'hours':Decimal(0),'lots':0})
            bucket['qty']+=r['units'];bucket['grams']+=Decimal(r['grams']);bucket['hours']+=Decimal(r['hours']);bucket['lots']+=1
        self.needs_table.fill([{**r,'grams':str(r['grams']),'hours':str(r['hours'])} for r in grouped.values()],[('product','Produto'),('lots','Lotes abertos'),('qty','Unidades a produzir'),('grams','Gramas previstas'),('hours','Horas previstas')])
        loss_rows=shop.losses(self.erp,'01/01/1900','31/12/9999')
        self.losses_table.fill(loss_rows,[('id','Evento'),('date','Data'),('job_id','Lote'),('product_name','Produto'),('grams','Gramas informadas'),('hours','Horas extras'),('value_cents','Custo modelado'),('reason','Motivo'),('voided','Estornado')])

    @ui_action
    def sync_production(self):count=shop.sync_jobs(self.erp);self.refresh_production();self.info(f'{count} lotes criados. Pedidos sem produto identificado continuam em Pendências.')

    @ui_action
    def new_job(self):
        if not self.product_options():raise ValueError('Cadastre um produto primeiro.')
        v=self.form('Novo lote avulso',[('pid','Produto',self.product_options()),('units','Unidades completas','1'),('due','Prazo (DD/MM/AAAA; opcional)','')],'Lote avulso não cria uma venda. Estoque será reservado pela receita; a baixa depende da confirmação de produção.')
        if v:shop.create_job(self.erp,v['pid'],v['units'],due=v['due'] or None);self.refresh_production()

    @ui_action
    def job_state(self):
        if self.production_tabs.currentIndex()!=0:raise ValueError('Selecione um lote na aba Lotes.')
        job=self.jobs_table.selected();options=[(s+(' · baixa de filamento' if s=='Pronto' else ''),s) for s in shop.STATES];options.sort(key=lambda x:x[1]!=job['state'])
        v=self.form('Etapa do lote',[('state','Nova etapa',options)],'Pronto baixa a massa da receita uma única vez. Cancelar não devolve material já consumido. Lote baixado não volta de etapa; use perda/reimpressão.')
        if v:
            if v['state']=='Pronto' and job['state']!='Pronto' and not self.ask('Confirmar lote produzido?','Confirmar unidades produzidas e baixar a massa prevista da receita? Não é leitura de sensor.'):return
            changed=shop.change_state(self.erp,job['id'],v['state']);self.refresh_production();self.info('Etapa registrada.' if changed else 'Este lote já está nessa etapa; não houve nova baixa.')

    @ui_action
    def refresh_job_recipe(self):
        if self.production_tabs.currentIndex()!=0:raise ValueError('Selecione um lote na aba Lotes.')
        job=self.jobs_table.selected()
        if self.ask('Atualizar previsão do lote?', 'Usar a receita atual e a quantidade atual do pedido? Somente lotes não iniciados e sem eventos podem ser atualizados.'):
            shop.refresh_job(self.erp,job['id']);self.refresh_production()

    @ui_action
    def new_loss(self):
        if not self.filament_options():raise ValueError('Cadastre um filamento primeiro.')
        options=[('Sem lote associado',None)]+[(f"#{j['id']} · {j['name']}",j['id']) for j in shop.jobs(self.erp)]
        v=self.form('Perda / reimpressão adicional',[('jid','Lote',options),('fid','Filamento',self.filament_options()),('grams','Gramas extras perdidas','0'),('hours','Horas extras (opcional)','0'),('reason','Motivo',''),('when','Data',date.today().strftime('%d/%m/%Y')),('already','Baixa de estoque',[('Dar baixa adicional',False),('Massa já baixada anteriormente',True)])],
            'O custo de referência é material + energia/máquina das horas extras. Ele reduz o resultado operacional, sem nova saída de caixa nem segunda compra. Não registre como perda material já incluído em outra perda.')
        if v:shop.record_loss(self.erp,v['fid'],v['grams'],v['hours'],v['reason'],v['when'],v['jid'],v['already']);self.refresh_production()

    @ui_action
    def reverse_loss(self):
        if self.production_tabs.currentIndex()!=2:raise ValueError('Selecione a aba Perdas e reimpressões e um evento.')
        event=self.losses_table.selected();v=self.form('Estornar perda',[('reason','Motivo do estorno','')],'O evento fica no histórico. Somente movimentos de estoque daquele evento são devolvidos; o custo modelado deixa de ser considerado.')
        if v:shop.void_loss(self.erp,event['id'],v['reason']);self.refresh_production()

    @ui_action
    def export_production(self):self.export_rows('Produção',[],{'Lotes':self.jobs_table.records,'Necessidades':self.needs_table.records,'Perdas':self.losses_table.records})

    def build_stock(self):
        p=Page('Estoque de filamentos','Saldo físico informado, reserva dos lotes e baixas confirmadas. Compras antigas não são presumidas como material disponível.')
        self.stock_query=QLineEdit();self.stock_query.setPlaceholderText('Buscar material, cor ou rolo');p.toolbar.addWidget(self.stock_query)
        p.button('Atualizar',self.refresh_stock,True);p.button('Cadastrar rolo/saldo físico',self.new_roll);p.button('Ajustar saldo medido',self.adjust_stock);p.button('Exportar estoque',self.export_stock)
        self.stock_note=QLabel();self.stock_note.setObjectName('badge');self.stock_note.setWordWrap(True);p.layout.addWidget(self.stock_note)
        self.stock_tabs=QTabWidget();self.material_stock=Table();self.roll_stock=Table();self.moves_stock=Table()
        for title,table in [('Materiais',self.material_stock),('Rolos/lotes',self.roll_stock),('Movimentações',self.moves_stock)]:self.stock_tabs.addTab(table,title)
        p.layout.addWidget(self.stock_tabs);self.stock_query.textChanged.connect(self.refresh_stock)
        return p,self.refresh_stock

    @ui_action
    def refresh_stock(self,*args):
        q=norm(self.stock_query.text());materials=shop.stock(self.erp);rolls=shop.rolls(self.erp)
        selected=[r for r in materials if q in norm(r['material']+' '+r['color'])]
        self.material_stock.fill(selected,[('material','Material'),('color','Cor'),('grams','Saldo g'),('reserved_grams','Reservado g'),('available_grams','Disponível após reservas g'),('shortage_grams','Falta g'),('minimum_grams','Alerta mínimo g'),('alert','Situação')],lambda r:r['alert']!='OK')
        self.roll_stock.fill([r for r in rolls if q in norm(r['label']+' '+r['material']+' '+r['color'])],[('id','Rolo/lote'),('label','Identificação'),('material','Material'),('color','Cor'),('grams','Saldo atual g'),('added','Entrada'),('purchase_id','Compra de origem')])
        moves=self.s.rows('SELECT m.*,r.label,f.material,f.color FROM stock_moves m JOIN stock_rolls r ON r.id=m.roll_id JOIN filaments f ON f.id=r.filament_id ORDER BY m.id DESC LIMIT 5000')
        self.moves_stock.fill([r for r in moves if q in norm(r['label']+' '+r['material']+' '+r['color'])],[('id','Movimento'),('date','Data'),('label','Rolo/lote'),('material','Material'),('color','Cor'),('delta_grams','Entrada/saída g'),('reason','Motivo'),('event_id','Evento produção')])
        unknown=sum(j['units'] for j in self.s.rows("SELECT units,recipe FROM production_jobs WHERE state IN('A produzir','Em impressão','Acabamento')") if not json.loads(j['recipe']).get('colors'))
        self.stock_note.setText(f'{len(rolls)} rolos/lotes cadastrados · {unknown} unidades em lotes sem cor definida · reservas não são baixas · massa por receita é uma estimativa até ajuste físico.')

    @ui_action
    def new_roll(self):
        if not self.filament_options():raise ValueError('Cadastre um filamento em Custos e cores.')
        v=self.form('Saldo físico do rolo/lote',[('fid','Filamento',self.filament_options()),('label','Identificação',''),('grams','Peso restante medido (g)','1000'),('when','Data de entrada',date.today().strftime('%d/%m/%Y')),('minimum','Alerta mínimo da cor (g)','100')],
                    'Este cadastro não cria uma compra nem despesa. Para uma compra nova, registre em Financeiro; ela criará um lote automaticamente.')
        if v:shop.register_roll(self.erp,v['fid'],v['label'],v['grams'],v['when'],v['minimum']);self.refresh_stock()

    @ui_action
    def adjust_stock(self):
        if self.stock_tabs.currentIndex()!=1:raise ValueError('Selecione um rolo na aba Rolos/lotes.')
        roll=self.roll_stock.selected();v=self.form('Corrigir saldo físico',[('grams','Peso restante medido (g)',roll['grams']),('reason','Motivo','')],'Registra a diferença como ajuste, sem alterar compras nem receitas. Não é uma entrada financeira.')
        if v:shop.adjust_roll(self.erp,roll['id'],v['grams'],v['reason']);self.refresh_stock()

    @ui_action
    def export_stock(self):self.export_rows('Estoque',[],{'Materiais':self.material_stock.records,'Rolos':self.roll_stock.records,'Movimentos':self.moves_stock.records})

    def build_simulator(self):
        p=Page('Simulador de preços','Teste cenários sem gravar no cadastro. Compare custo, preço sugerido e referência de vendas históricas.')
        self.sim_product=QComboBox();self.sim_product.setMinimumWidth(300);p.toolbar.addWidget(self.sim_product)
        p.button('Editar cenário',self.edit_scenario,True);p.button('Recalcular',self.calculate_scenario);p.button('Restaurar cenário do cadastro',self.reset_scenario);p.button('Exportar cenário',self.export_scenario)
        self.sim_scenarios={};self.sim_result=None
        row=QHBoxLayout();self.sim_cards=[]
        for title,caption in [('Custo simulado','Por unidade'),('Preço sugerido','Conforme o cenário'),('Diferença para cadastro','Alteração no preço sugerido'),('Retorno por hora','Lucro sugerido / horas conhecidas')]:
            card=MetricCard(title,caption);row.addWidget(card);self.sim_cards.append(card)
        p.layout.addLayout(row);self.sim_note=QLabel();self.sim_note.setWordWrap(True);self.sim_note.setObjectName('badge');p.layout.addWidget(self.sim_note)
        self.sim_table=p.table();self.sim_product.currentIndexChanged.connect(self.calculate_scenario)
        return p,self.refresh_simulator

    def refresh_simulator(self):
        current=self.sim_product.currentData();self.sim_product.blockSignals(True);self.sim_product.clear();self.sim_product.addItem('Selecione produto',None)
        for label,pid in self.product_options():self.sim_product.addItem(label,pid)
        if current:self.sim_product.setCurrentIndex(max(0,self.sim_product.findData(current)))
        elif self.sim_product.count()>1:self.sim_product.setCurrentIndex(1)
        self.sim_product.blockSignals(False);self.calculate_scenario()

    @ui_action
    def calculate_scenario(self,*args):
        pid=self.sim_product.currentData()
        if pid is None:
            self.sim_result=None;self.sim_note.setText('Cadastre um produto e complete peso, tempo e custos para simular.')
            for card in self.sim_cards:card.set_value('—')
            self.sim_table.fill([],[('component','Componente'),('base_cents','Cadastro'),('scenario_cents','Cenário')]);return
        args=self.sim_scenarios.get(pid,{})
        result=mgmt.simulator(self.erp,pid,**args);self.sim_result=result
        for card,value in zip(self.sim_cards,[money(result['scenario']['total_cents']),money(result['scenario']['suggested_cents']),money(result['difference_cents']),money(result['profit_hour_cents']) if result['profit_hour_cents'] is not None else 'Sem tempo']):card.set_value(value)
        rows=[]
        for key,label in [('material_cents','Filamento calculado'),('energy_cents','Energia'),('machine_cents','Máquina'),('manufacture_cents','Fabricação usada'),('packaging_cents','Embalagem'),('other_cents','Outros'),('total_cents','Custo total'),('fees_cents','Taxas sugeridas'),('profit_cents','Lucro sugerido'),('suggested_cents','Preço sugerido')]:rows.append({'component':label,'base_cents':result['base'][key],'scenario_cents':result['scenario'][key]})
        self.sim_table.fill(rows,[('component','Componente / unidade'),('base_cents','Cadastro'),('scenario_cents','Cenário')])
        avg=result['at_average'];note=f"{result['observed_units']} unidades em pedidos não cancelados. "
        if avg:note+=f"Preço médio dos itens: {money(avg['price_cents'])}. Com as taxas simuladas, lucro projetado nesse preço: {money(avg['profit_cents'])}. "
        note+='Nenhum parâmetro do cadastro foi alterado. Preço médio é antes de cupons do pedido; não é margem histórica comprovada.'
        if result['scenario']['manual']:note+=' Fabricação manual substitui material/energia/máquina; variação de filamento não muda esse valor manual.'
        if result['scenario']['missing']:note+=' DADOS PARCIAIS: '+', '.join(result['scenario']['missing'])
        self.sim_note.setText(note)

    @ui_action
    def edit_scenario(self):
        pid=self.sim_product.currentData()
        if pid is None:raise ValueError('Selecione um produto.')
        existing=self.sim_scenarios.get(pid,{});settings={**self.s.settings(),**existing.get('settings',{})};product=self.erp.product(pid)
        fields=[('filament_change','Variação do filamento % (-100 a 1000)',existing.get('filament_change','0')),
                ('packaging','Embalagem R$/un.',existing.get('packaging',str(Decimal(product['packaging_cents'])/100))),('other','Outros R$/un.',existing.get('other',str(Decimal(product['other_cents'])/100)))]
        for key,label in [('energy_kwh','Energia R$/kWh'),('power_w','Potência W'),('machine_hour','Máquina R$/h'),('fee_percent','Taxas %'),('fee_fixed','Taxa fixa R$/un.'),('profit_percent','Margem/acréscimo %')]:fields.append((key,label,settings[key]))
        modes=[('Margem sobre venda','margem'),('Acréscimo sobre custo','acrescimo')];modes.sort(key=lambda item:item[1]!=settings['pricing_mode']);fields.append(('pricing_mode','Método',modes))
        v=self.form('Cenário temporário',fields,'Somente simulação em memória. Valores do produto e configurações atuais não serão alterados.')
        if v:
            args={'filament_change':v.pop('filament_change'),'packaging':v.pop('packaging'),'other':v.pop('other'),'settings':v}
            mgmt.simulator(self.erp,pid,**args);self.sim_scenarios[pid]=args;self.calculate_scenario()

    def reset_scenario(self):
        self.sim_scenarios.pop(self.sim_product.currentData(),None);self.calculate_scenario()

    @ui_action
    def export_scenario(self):
        if not self.sim_result:raise ValueError('Selecione um produto para simular.')
        self.export_rows('Simulação',[],{'Comparação':self.sim_table.records,'Cenário':[{'produto':self.sim_product.currentText(),'parametros':json.dumps(self.sim_scenarios.get(self.sim_product.currentData(),{}),ensure_ascii=False),'nota':self.sim_note.text()}]})

    def build_receipts(self):
        p=Page('Repasses e conciliação','Registre valores efetivamente recebidos e vincule a pedidos. Não são novas vendas nem saldo bancário.')
        self.receipt_start=QLineEdit(date.today().replace(day=1).strftime('%d/%m/%Y'));self.receipt_end=QLineEdit(date.today().strftime('%d/%m/%Y'))
        self.receipt_order_start=QLineEdit(self.s.settings().get('last_import_start',date.today().replace(day=1).isoformat()));self.receipt_order_end=QLineEdit(self.s.settings().get('last_import_end',date.today().isoformat()))
        for label,widget in [('Recebidos de',self.receipt_start),('até',self.receipt_end),('Pedidos de',self.receipt_order_start),('até',self.receipt_order_end)]:widget.setMaximumWidth(125);p.toolbar.addWidget(QLabel(label));p.toolbar.addWidget(widget)
        p.button('Consultar',self.refresh_receipts,True);p.button('Novo/editar repasse',self.new_receipt);p.button('Vincular a pedido',self.link_payment);p.button('Remover vínculo',self.unlink_payment);p.button('Excluir repasse',self.delete_payment);p.button('Importar XLSX',self.import_payments);p.button('Modelos',self.save_templates);p.button('Exportar',self.export_receipts)
        self.receipt_note=QLabel();self.receipt_note.setObjectName('badge');self.receipt_note.setWordWrap(True);p.layout.addWidget(self.receipt_note)
        self.receipt_tabs=QTabWidget();self.receipt_table=Table();self.reconciliation_table=Table();self.receipt_links=Table()
        for title,table in [('Recebimentos',self.receipt_table),('Conciliação por pedido',self.reconciliation_table),('Vínculos de recebimentos',self.receipt_links)]:self.receipt_tabs.addTab(table,title)
        p.layout.addWidget(self.receipt_tabs)
        return p,self.refresh_receipts

    @ui_action
    def refresh_receipts(self):
        rows=mgmt.receipt_rows(self.erp,self.receipt_start.text(),self.receipt_end.text())
        self.receipt_table.fill(rows,[('id','Repasse'),('date','Recebido em'),('reference','Referência'),('amount_cents','Valor recebido'),('allocated_cents','Vinculado a pedidos'),('unallocated_cents','Ainda não vinculado'),('note','Observação')])
        self.reconciliation_table.fill(mgmt.reconciliation(self.erp,self.receipt_order_start.text(),self.receipt_order_end.text()),[('id','Pedido'),('date','Criado em'),('status','Status'),('expected_cents','Previsão após taxas/reembolso'),('received_cents','Recebimento vinculado'),('difference_cents','Diferença'),('reconciliation','Situação')],lambda r:abs(r['difference_cents'])>1)
        links=self.s.rows('SELECT l.*,r.reference,r.date FROM settlement_links l JOIN settlements r ON r.id=l.settlement_id ORDER BY r.date DESC')
        self.receipt_links.fill(links,[('settlement_id','Repasse'),('reference','Referência'),('date','Recebido em'),('order_id','Pedido'),('amount_cents','Valor vinculado')])
        self.receipt_note.setText(f"Recebido no período de recebimentos: {money(sum(r['amount_cents'] for r in rows))} · Não vinculado: {money(sum(r['unallocated_cents'] for r in rows))}. Datas dos pedidos e dos repasses têm filtros independentes. Vínculos mostram todo o histórico.")

    @ui_action
    def new_receipt(self):
        v=self.form('Repasse efetivamente recebido',[('when','Data do recebimento',date.today().strftime('%d/%m/%Y')),('reference','Referência única',''),('amount','Valor recebido R$','0'),('note','Observação gerencial','')],
                    'A mesma referência atualiza o repasse existente, sem duplicá-lo; vínculos são preservados. Informe depósito líquido realmente recebido, não o Total global da planilha de pedidos.')
        if v:mgmt.save_receipt(self.erp,**v);self.refresh_receipts()

    @ui_action
    def link_payment(self):
        rows=mgmt.receipt_rows(self.erp);orders=self.s.rows('SELECT id,date,status FROM orders ORDER BY date DESC,id')
        if not rows or not orders:raise ValueError('Cadastre um repasse e importe pedidos antes de conciliar.')
        v=self.form('Vincular parte do repasse',[('rid','Repasse',[(r['reference']+' · '+money(r['amount_cents']),r['id']) for r in rows]),('oid','Pedido',[(o['id']+' · '+o['status'],o['id']) for o in orders]),('amount','Valor vinculado R$','0')],
                    'A soma dos vínculos não pode ultrapassar o repasse. Você pode dividir um repasse entre vários pedidos ou um pedido entre repasses. O mesmo par atualiza o valor já vinculado.')
        if v:mgmt.link_receipt(self.erp,**v);self.refresh_receipts()

    @ui_action
    def unlink_payment(self):
        if self.receipt_tabs.currentIndex()!=2:raise ValueError('Selecione um vínculo na terceira aba.')
        link=self.receipt_links.selected()
        if self.ask('Remover vínculo?','O repasse e o pedido serão preservados. Apenas esta alocação será removida.'):
            mgmt.unlink_receipt(self.erp,link['settlement_id'],link['order_id']);self.refresh_receipts()

    @ui_action
    def delete_payment(self):
        if self.receipt_tabs.currentIndex()!=0:raise ValueError('Selecione um repasse na primeira aba.')
        receipt=self.receipt_table.selected()
        if self.ask('Excluir repasse?', 'Criar backup e excluir este recebimento e seus vínculos? Os pedidos e as vendas serão preservados.'):
            self.s.backup()
            with self.s.transaction():self.s.db.execute('DELETE FROM settlements WHERE id=?',(receipt['id'],));self.s.log('excluir_repasse',{'id':receipt['id']})
            self.refresh_receipts()

    @ui_action
    def import_payments(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar repasses no modelo gerencial','','Planilha (*.xlsx)')
        if not path:return
        h,rows,_=read_xlsx(path)
        required=['Data','Referência','Valor recebido R$']
        if not all(k in h for k in required):
            keys=required+['Pedido ID','Valor vinculado R$'];fields=[]
            for key in keys:
                opts=[('Não disponível','')]+[(header,header) for header in h];opts.sort(key=lambda item:norm(item[1])!=norm(key));fields.append((key,key,opts))
            mapping=self.form('Mapear relatório de recebimentos',fields,'Use apenas valores de recebimento efetivo. Não importe a planilha de pedidos como repasses. Os dois campos de vínculo são opcionais, mas devem ser preenchidos juntos.')
            if not mapping:return
            rows=[{key:row.get(mapping[key]) for key in keys} for row in rows]
        prepared=mgmt.prepare_receipts(rows)
        if preview(self,'Prévia de recebimentos',prepared,'Referência única atualiza sem duplicar. Vínculos ausentes no arquivo não são apagados; limites de alocação são validados em transação.'):
            count=mgmt.import_receipts(self.erp,prepared);self.refresh_receipts();self.info(f'{count} referências de recebimento registradas.')

    @ui_action
    def export_receipts(self):self.export_rows('Repasses',[],{'Recebimentos':self.receipt_table.records,'Conciliação':self.reconciliation_table.records,'Vínculos':self.receipt_links.records})

    @ui_action
    def search_everywhere(self):
        v=self.form('Buscar no estúdio',[('query','Pedido, SKU, produto ou variação','')])
        if not v:return
        rows=org.global_search(self.erp,v['query']);dialog=QDialog(self);dialog.setWindowTitle('Resultados da busca');dialog.resize(1000,560);layout=QVBoxLayout(dialog);table=Table();table.fill(rows,[('type','Tipo'),('reference','Referência'),('description','Descrição'),('target','Onde abrir')]);layout.addWidget(table)
        button=QPushButton('Abrir selecionado')
        def open_row():
            try:self.open_reference(table.selected());dialog.accept()
            except Exception as error:QMessageBox.warning(dialog,'Busca',str(error))
        button.clicked.connect(open_row);layout.addWidget(button);dialog.exec()

    @ui_action
    def show_recipe_history(self):
        if not self.product_options():raise ValueError('Cadastre um produto primeiro.')
        v=self.form('Histórico de receitas',[('pid','Produto',self.product_options())])
        if not v:return
        dialog=QDialog(self);dialog.setWindowTitle('Revisões do cadastro · custos dos pedidos preservados');dialog.resize(1050,600);layout=QVBoxLayout(dialog)
        table=Table();table.fill(revisions(self.erp,v['pid']),[('recorded','Registrado em'),('reason','Alteração'),('grams','Peso g/un.'),('hours','Horas/un.'),('total_cents','Custo de referência na revisão'),('colors','Cores/gramas')]);layout.addWidget(table)
        button=QPushButton('Fechar');button.clicked.connect(dialog.accept);layout.addWidget(button);dialog.exec()

    @ui_action
    def appearance_settings(self):
        current=org.preference(self.s,'appearance',{})
        v=self.form('Aparência e leitura',[('font','Fonte base (12 a 18 px)',str(current.get('font',13))),('opacity','Opacidade dos painéis (60 a 100%)',str(current.get('opacity',80))),('contrast','Contraste',[('Normal',False),('Alto contraste',True)]),('compact','Menu lateral',[('Expandido',False),('Recolhido',True)])],
                    'As mudanças são locais e não afetam dados ou cálculos. Modo foco continua disponível no menu lateral.')
        if v:
            from ..business.numbers import quantity
            font=quantity(v['font']);opacity=quantity(v['opacity'])
            if not 12<=font<=18 or not 60<=opacity<=100:raise ValueError('Fonte: 12 a 18. Opacidade: 60 a 100%.')
            org.set_preference(self.s,'appearance',{'font':font,'opacity':opacity,'contrast':v['contrast'],'compact':v['compact']});self.apply_appearance()

    def apply_appearance(self):
        from .widgets import STYLE
        config=org.preference(self.s,'appearance',{});font=max(12,min(18,int(config.get('font',13))))
        style=STYLE+f'\nQWidget {{ font-size: {font}px; }} QLabel#subtitle,QLabel#muted {{ font-size: {max(11,font-1)}px; }}'
        if config.get('contrast'):style+='\nQLineEdit,QComboBox,QTableWidget,QTextBrowser {background:#080f1a;color:#ffffff;border-color:#8195ae;} QLabel#muted,QLabel#subtitle{color:#d5e1f1;}'
        self.setStyleSheet(style);self.backdrop.glass_alpha=int(max(60,min(100,int(config.get('opacity',80))))*2.55)
        self.backdrop.set_focus(bool(config.get('contrast') or self.focus_toggle.isChecked()))
        self.set_sidebar_compact(bool(config.get('compact',False)),persist=False);self.backdrop.update()
        for card in self.findChildren(GlassCard):card.update()

    @ui_action
    def export_diagnostic(self):
        path,_=QFileDialog.getSaveFileName(self,'Salvar diagnóstico sem dados pessoais','diagnostico-forgeon.json','JSON (*.json)')
        if path:Path(path).write_text(json.dumps(org.diagnostic(self.s),ensure_ascii=False,indent=2),encoding='utf-8');self.info('Diagnóstico salvo localmente. Nenhum arquivo foi enviado automaticamente.')

    def set_sidebar_compact(self,compact,persist=True):
        self.sidebar.setFixedWidth(150 if compact else 224)
        self.brand_label.setVisible(not compact);self.tagline_label.setVisible(not compact)
        self.sidebar_footer.setText('Dados locais' if compact else 'SEU ESTÚDIO, EM ORDEM.\nDados locais · banco preservado')
        short=['Painel','Produtos','Cores','Preços','SKUs','Pedidos','Importar','Finanças','Relatórios','Ajustes','Atualizar','Pendências','Produção','Estoque','Simular','Repasses']
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for index,title in enumerate(self.nav_titles):
            self.nav.item(index).setText(short[index] if compact else title);self.nav.item(index).setToolTip(title)
        self.nav.setToolTip('Ctrl+F: buscar · F1: ajuda da aba')
        if persist:
            config=org.preference(self.s,'appearance',{});config['compact']=compact;org.set_preference(self.s,'appearance',config)

    def install_utilities(self):
        from PySide6.QtGui import QShortcut,QKeySequence
        from .help import show_help
        self.shortcuts=[]
        for key,callback in [('F1',lambda:show_help(self,self.nav_titles[self.stack.currentIndex()])),('Ctrl+F',self.search_everywhere),('Ctrl+N',lambda:self.edit_product()),('Ctrl+I',self.import_order_file)]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(callback);self.shortcuts.append(shortcut)
        for tabs in self.findChildren(QTabWidget):
            button=QPushButton('ⓘ');button.setObjectName('helpButton');button.setToolTip('Como usar esta subaba');button.clicked.connect(lambda checked=False,t=tabs:show_help(self,t.tabText(t.currentIndex())))
            tabs.setCornerWidget(button,Qt.Corner.TopRightCorner)
        for page in self.stack.findChildren(Page):
            for index,table in enumerate(page.findChildren(Table)):
                table.persistence=(self.s,page.page_title+':'+str(index))
        search=QPushButton('Buscar · Ctrl+F');search.clicked.connect(self.search_everywhere);self.sidebar.body.insertWidget(3,search)

    def build_report_filters(self,p):
        from .visual import FlowLayout
        layout=FlowLayout();p.layout.addLayout(layout)
        self.report_extra={}
        for key,label in [('sku','SKU'),('variation','Variação'),('material','Material'),('color','Cor')]:
            widget=QLineEdit();widget.setPlaceholderText(label);widget.setMaximumWidth(160);layout.addWidget(widget);self.report_extra[key]=widget
        self.report_coverage=QComboBox()
        for label,value in [('Toda cobertura',''),('Receitas completas','completos'),('Receitas pendentes','pendentes')]:self.report_coverage.addItem(label,value)
        layout.addWidget(self.report_coverage)
        self.report_presets=QComboBox();layout.addWidget(self.report_presets);self.reload_presets()
        for label,fn in [('Mês da data inicial',lambda:self.report_period('mes')),('1ª quinzena',lambda:self.report_period('primeira')),('2ª quinzena',lambda:self.report_period('segunda')),('Aplicar filtro salvo',self.load_report_preset),('Salvar filtro',self.save_report_preset),('Limpar filtros',self.clear_report_filters)]:
            button=QPushButton(label);button.clicked.connect(fn);layout.addWidget(button)
        note=QLabel('Cor/material selecionam itens que usam o filamento; os valores não são rateados entre cores. Desempenho e histórico mensal usam o período geral.');note.setWordWrap(True);p.layout.addWidget(note)

    def report_filters(self):return {**{k:w.text().strip() for k,w in self.report_extra.items()},'coverage':self.report_coverage.currentData()}

    def reload_presets(self):
        self.report_presets.clear();self.report_presets.addItem('Filtros salvos',None)
        for row in self.s.rows("SELECT * FROM filter_presets WHERE scope='relatorios' ORDER BY name"):self.report_presets.addItem(row['name'],json.loads(row['detail']))

    @ui_action
    def save_report_preset(self):
        v=self.form('Salvar filtro',[('name','Nome do filtro','')])
        if v:org.save_preset(self.s,v['name'],{**self.report_filters(),'product':self.report_product.currentData(),'status':self.report_status.currentData()});self.reload_presets()

    @ui_action
    def load_report_preset(self):
        saved=self.report_presets.currentData()
        if saved is None:return
        for k,w in self.report_extra.items():w.setText(saved.get(k,''))
        self.report_coverage.setCurrentIndex(max(0,self.report_coverage.findData(saved.get('coverage',''))));self.report_product.setCurrentIndex(max(0,self.report_product.findData(saved.get('product'))));self.report_status.setCurrentIndex(max(0,self.report_status.findData(saved.get('status',''))));self.update_report()

    def clear_report_filters(self):
        for w in self.report_extra.values():w.clear()
        self.report_coverage.setCurrentIndex(0);self.report_product.setCurrentIndex(0);self.report_status.setCurrentIndex(0);self.update_report()

    @ui_action
    def report_period(self,kind):
        from calendar import monthrange
        date_value=date.fromisoformat(day(self.report_start.text()));year,month=date_value.year,date_value.month;last=monthrange(year,month)[1]
        first=16 if kind=='segunda' else 1;end=15 if kind=='primeira' else last
        self.report_start.setText(f'{year:04}-{month:02}-{first:02}');self.report_end.setText(f'{year:04}-{month:02}-{end:02}');self.update_report()
