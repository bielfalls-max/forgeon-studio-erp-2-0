from datetime import date
from decimal import Decimal
from pathlib import Path
from functools import wraps
import html
import sqlite3
import json
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QLabel,QStackedWidget,
    QLineEdit,QPushButton,QDialog,QMessageBox,QFileDialog,QComboBox,QTextBrowser,QInputDialog,QCheckBox,QTabWidget,QGridLayout,QScrollArea,QApplication)
from .widgets import Page,Form,Table,preview,STYLE
from .visual import MountainBackdrop,GlassCard,MetricCard,ASSETS,app_icon
from .charts import ChartCard
from .updates import UpdatesPage
from ..version import VERSION,HOTFIX
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QPixmap,QTextDocument,QPdfWriter,QPageSize,QFont
from ..business.numbers import money,day
from ..business.labels import LABELS
from ..reports.finance import report,monthly
from ..reports.xlsx import export,templates
from ..importers.sheets import (read_xlsx,detect,LABELS as IMPORT_LABELS,preview_orders,import_orders,preview_stats,import_stats,status_kind)
from ..importers.slicing import read_slicing,per_unit
from ..importers import catalog


def guarded(fn):
    @wraps(fn)
    def run(self,*args,**kwargs):
        try:
            return fn(self,*args,**kwargs)
        except Exception as e:
            self.statusBar().showMessage('Operação não concluída',6000)
            QMessageBox.warning(self,'FORGEON • Verifique os dados',str(e))
    return run


def text(value):
    return html.escape(str(value))


class MainWindow(QMainWindow):
    def __init__(self,erp):
        super().__init__()
        self.erp=erp; self.s=erp.s
        self.setWindowTitle(f'FORGEON STUDIO • {VERSION} / {HOTFIX}');self.setWindowIcon(app_icon())
        self.resize(1440,900); self.setMinimumSize(1100,700)
        self.setStyleSheet(STYLE)
        root=MountainBackdrop(); self.backdrop=root; self.setCentralWidget(root); layout=QHBoxLayout(root); layout.setContentsMargins(16,16,0,14); layout.setSpacing(0)
        root.focus_mode=self.s.settings().get("appearance_focus","0")=="1"
        sidebar=GlassCard(); sidebar.setFixedWidth(224);sl=sidebar.body;sl.setContentsMargins(14,20,14,16)
        logo=QLabel();logo.setPixmap(QPixmap(str(ASSETS/'forgeon-dragon.png')).scaled(54,54,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        identity=QHBoxLayout();identity.addWidget(logo)
        names=QVBoxLayout();brand=QLabel('FORGEON');brand.setObjectName('brand');names.addWidget(brand)
        tagline=QLabel('STUDIO  /  ERP');tagline.setObjectName('muted');names.addWidget(tagline);identity.addLayout(names);sl.addLayout(identity)
        badge=QLabel(f'{VERSION}  ·  HF01');badge.setObjectName('badge');sl.addWidget(badge)
        self.nav=QListWidget();sl.addWidget(self.nav,1)
        self.focus_toggle=QCheckBox('Modo foco');self.focus_toggle.setChecked(root.focus_mode);self.focus_toggle.toggled.connect(self.toggle_focus);sl.addWidget(self.focus_toggle)
        footer=QLabel('SEU ESTÚDIO, EM ORDEM.\nDados locais · banco preservado');footer.setObjectName('muted');sl.addWidget(footer)
        layout.addWidget(sidebar)
        self.stack=QStackedWidget(); layout.addWidget(self.stack,1)
        self.refreshers=[]
        builders=[('Visão geral',self.build_dashboard),('Produtos',self.build_products),('Custos e cores',self.build_colors),
                  ('Precificação',self.build_pricing),('Catálogo e SKUs',self.build_skus),('Pedidos',self.build_orders),
                  ('Importações',self.build_imports),('Financeiro',self.build_finance),('Relatórios',self.build_reports),
                  ('Configurações',self.build_settings),('Atualizações',self.build_updates)]
        for title,builder in builders:
            page,refresh=builder(); self.nav.addItem(title); self.stack.addWidget(page); self.refreshers.append(refresh)
        self.nav.currentRowChanged.connect(self.change_page)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage(f'FORGEON {VERSION}  •  Gestão local  •  Internet somente quando você consulta ou baixa atualizações')

    @guarded
    def change_page(self,index):
        self.stack.setCurrentIndex(index); self.refreshers[index]()

    def refresh(self):
        self.refreshers[self.stack.currentIndex()]()
        self.statusBar().showMessage('Dados atualizados e salvos no banco local.',5000)

    def info(self,message):
        QMessageBox.information(self,'FORGEON STUDIO',str(message))

    def ask(self,title,message):
        return QMessageBox.question(self,title,message)==QMessageBox.StandardButton.Yes

    def form(self,title,fields,note=''):
        d=Form(title,fields,self,note)
        return d.values() if d.exec()==QDialog.DialogCode.Accepted else None

    def product_options(self,empty=False):
        options=[('Sem vínculo',None)] if empty else []
        return options+[(f"#{p['id']} • {p['name']} / {p['model']}"+(' [arquivado]' if p['archived'] else ''),p['id']) for p in self.s.rows('SELECT * FROM products ORDER BY name,model')]

    def filament_options(self):
        return [(f"{f['material']} / {f['color']} • {money(f['kg_cents'])}/kg",f['id']) for f in self.s.rows('SELECT * FROM filaments ORDER BY material,color')]

    def export_rows(self,title,rows,sheets=None):
        path,_=QFileDialog.getSaveFileName(self,'Exportar XLSX',f'{title}.xlsx','Planilha (*.xlsx)')
        if path:
            export(path,sheets or {title:rows}); self.info('Planilha exportada.')

    def build_dashboard(self):
        p=Page('Visão geral','Sua produção, vendas e custos em uma só vista. Os indicadores usam o banco local do estúdio.')
        self.dashboard_month=QLineEdit(date.today().strftime('%Y-%m'));self.dashboard_month.setFixedWidth(120)
        p.toolbar.addWidget(QLabel('Mês (AAAA-MM)'));p.toolbar.addWidget(self.dashboard_month)
        p.button('Atualizar painel',self.update_dashboard,True)
        p.button('Importar vendas',lambda:self.nav.setCurrentRow(6));p.button('Abrir relatórios',lambda:self.nav.setCurrentRow(8))
        scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();self.dashboard_grid=QGridLayout(content);self.dashboard_grid.setContentsMargins(0,0,0,0);self.dashboard_grid.setSpacing(14)
        scroll.setWidget(content);p.layout.addWidget(scroll,1)
        self.dashboard_badge=QLabel();self.dashboard_badge.setObjectName('badge');self.dashboard_grid.addWidget(self.dashboard_badge,0,0,1,4)
        self.metric_cards=[]
        for col,(label,caption) in enumerate([('Vendas brutas','Pedidos não cancelados no mês'),('Resultado operacional','Após taxas, produção e despesas'),('Caixa estimado','Referência gerencial, não saldo bancário'),('Pedidos no período','Inclui status filtrados no relatório')]):
            card=MetricCard(label,caption);self.metric_cards.append(card);self.dashboard_grid.addWidget(card,1,col)
        self.dashboard_chart=ChartCard('Vendas ao longo do mês','Valores brutos dos pedidos · passe o mouse sobre os pontos')
        self.dashboard_grid.addWidget(self.dashboard_chart,2,0,1,3)
        pending=GlassCard();title=QLabel('Prioridades do estúdio');title.setObjectName('sectionTitle');pending.body.addWidget(title)
        self.dashboard_pending=QLabel();self.dashboard_pending.setWordWrap(True);pending.body.addWidget(self.dashboard_pending,1)
        review=QPushButton('Revisar catálogo →');review.clicked.connect(lambda:self.nav.setCurrentRow(4));pending.body.addWidget(review)
        self.dashboard_grid.addWidget(pending,2,3)
        self.dashboard_best=ChartCard('Produtos em destaque','Unidades vendidas no período, incluindo devoluções')
        self.dashboard_grid.addWidget(self.dashboard_best,3,0,1,2)
        definitions=GlassCard();title=QLabel('Uma leitura clara dos números');title.setObjectName('sectionTitle');definitions.body.addWidget(title)
        self.dashboard=QLabel();self.dashboard.setWordWrap(True);self.dashboard.setObjectName('muted');definitions.body.addWidget(self.dashboard,1)
        self.dashboard_grid.addWidget(definitions,3,2,1,2)
        for col in range(4):self.dashboard_grid.setColumnStretch(col,1)
        return p,self.update_dashboard

    @guarded
    def update_dashboard(self):
        from calendar import monthrange
        month=self.dashboard_month.text();y,m=map(int,month.split('-'));last=monthrange(y,m)[1]
        r=report(self.erp,f'{y:04}-{m:02}-01',f'{y:04}-{m:02}-{last}')
        self.dashboard_badge.setText(('DADOS PARCIAIS  ·  ' if r['partial'] else 'FONTES CONCILIADAS  ·  ')+f'{m:02}/{y}  ·  Confira custos, vínculos e cobertura dos arquivos')
        values=[money(r['gross_cents']),money(r['operating_cents']),money(r['cash_cents']),str(r['orders_count'])]
        for index,(card,value) in enumerate(zip(self.metric_cards,values)):card.set_value(value,index in (1,2) and r['operating_cents' if index==1 else 'cash_cents']<0)
        origins=self.s.one('SELECT count(*) n FROM origins WHERE product_id IS NULL AND active=1')['n']
        products=self.s.one('SELECT count(*) n FROM products WHERE archived=0')['n']
        conflicts=len(self.erp.conflicts())
        self.dashboard_pending.setText(f"<p><b style='color:#f6bd94;font-size:23px'>{origins}</b><br>origens sem produto vinculado</p><p><b style='color:#f6bd94;font-size:23px'>{r['pending_items']}</b><br>itens sem custo congelado</p><p>{conflicts} conflitos de SKU · {products} produtos ativos</p>")
        self.dashboard_chart.line(r['sales_by_day']);self.dashboard_best.bars(r['best_sellers'],'product','qty')
        self.dashboard.setText(f"<p><b>Resultado operacional</b><br>Vendas menos reembolsos, taxas, produção e despesas. Compras de filamento não são descontadas novamente.</p><p><b>Caixa estimado</b><br>Considera compras e datas dos pedidos. Não representa saldo bancário ou repasses conciliados.</p><p><b>Cobertura das fontes</b><br>Resumo da loja: {money(r['stats_cents'])}<br>Diferença para pedidos: {money(r['difference_cents'])}</p><p>Estatísticas são uma comparação separada. Elas nunca são somadas como novas vendas.</p>")

    def build_products(self):
        p=Page('Produtos físicos','Uma linha por produto. Anúncios vinculados compartilham peso, cores, tempo e custo. Arquivar preserva os pedidos.')
        self.product_search=QLineEdit(); self.product_search.setPlaceholderText('Buscar por nome, modelo ou SKU'); self.product_search.textChanged.connect(lambda:self.update_products()); p.toolbar.addWidget(self.product_search)
        self.show_archived=QCheckBox('Incluir arquivados'); self.show_archived.stateChanged.connect(lambda:self.update_products()); p.toolbar.addWidget(self.show_archived)
        p.button('+ Produto',lambda:self.edit_product(),True); p.button('Editar',lambda:self.edit_product(self.products_table.selected()['id']))
        p.button('Arquivar / reativar',self.archive_product); p.button('Exportar',lambda:self.export_rows('Produtos',self.product_rows()))
        self.products_table=p.table(); self.products_table.doubleClicked.connect(lambda:self.edit_product(self.products_table.selected()['id']))
        return p,self.update_products

    def product_rows(self):
        result=[]
        for product in self.s.rows('SELECT * FROM products ORDER BY name,model'):
            pid=product['id']; c=self.erp.cost(pid)
            origins=self.s.rows('SELECT * FROM origins WHERE product_id=? AND active=1',(pid,))
            result.append({**product,'skus':', '.join(sorted({o['sku'] for o in origins if o['sku']})), 'origins_count':len(origins),
                           'colors':'; '.join(f"{x['material']} {x['color']}: {x['grams']} g" for x in c['colors']),
                           'weight':c['grams'],'total_cents':c['total_cents'],'suggested_cents':c['suggested_cents'],'pending':', '.join(c['missing']) or 'Completo'})
        return result

    @guarded
    def update_products(self):
        q=self.product_search.text().casefold()
        rows=[r for r in self.product_rows() if (self.show_archived.isChecked() or not r['archived']) and q in (r['name']+' '+r['model']+' '+r['skus']).casefold()]
        self.products_table.fill(rows,[('name','Produto'),('model','Modelo / tamanho'),('skus','SKUs'),('origins_count','Origens'),('colors','Cores / gramas por unidade'),('weight','Peso g'),('hours','Horas'),('total_cents','Custo'),('suggested_cents','Preço sugerido'),('pending','Pendências'),('archived','Arquivado')])

    @guarded
    def edit_product(self,pid=None):
        v=self.erp.product(pid) if pid else {'name':'','model':'','weight':'0','hours':'0','manual_cents':None,'packaging_cents':0,'other_cents':0,'notes':''}
        fields=[('name','Nome',v['name']),('model','Modelo / tamanho',v['model']),('weight','Peso (g)',v['weight']),('hours','Tempo de impressão (h)',v['hours']),
                ('manual','Fabricação manual (R$; vazio = calculada)','' if v['manual_cents'] is None else str(Decimal(v['manual_cents'])/100)),
                ('packaging','Embalagem (R$/un.)',str(Decimal(v['packaging_cents'])/100)),('other','Outros custos (R$/un.)',str(Decimal(v['other_cents'])/100)),('notes','Observações',v['notes'])]
        data=self.form('Editar produto' if pid else 'Novo produto físico',fields,
                       'Com cores cadastradas, o peso será a soma dos gramas. Custo manual substitui material + energia + máquina. Embalagem e outros são somados.')
        if data:
            self.erp.save_product(data,pid); self.refresh()

    @guarded
    def archive_product(self):
        self.erp.archive(self.products_table.selected()['id']); self.refresh()

    def build_colors(self):
        p=Page('Custos e cores','Preço do filamento por material/cor. Informe o consumo por unidade do produto; zero remove a cor. Custos históricos já congelados são preservados.')
        p.button('+ Filamento',lambda:self.edit_filament(),True); p.button('Editar filamento',lambda:self.edit_filament(self.filament_table.selected()['id']))
        p.button('Definir cor de produto',self.assign_color); p.button('Copiar custos e cores',self.copy_costs); p.button('Ler 3MF / G-code',self.slicing)
        self.filament_table=p.table(); self.product_colors_table=p.table()
        return p,self.update_colors

    @guarded
    def update_colors(self):
        self.filament_table.fill(self.s.rows('SELECT * FROM filaments ORDER BY material,color'),[('id','ID'),('material','Material'),('color','Cor'),('kg_cents','Preço por kg')])
        self.product_colors_table.fill(self.s.rows('SELECT p.id,p.name,p.model,f.material,f.color,c.grams FROM product_colors c JOIN products p ON p.id=c.product_id JOIN filaments f ON f.id=c.filament_id ORDER BY p.name,f.color'),[('id','Produto ID'),('name','Produto'),('model','Modelo'),('material','Material'),('color','Cor'),('grams','Gramas / unidade')])

    @guarded
    def edit_filament(self,fid=None):
        f=self.s.one('SELECT * FROM filaments WHERE id=?',(fid,)) if fid else {'material':'PLA','color':'','kg_cents':9000}
        v=self.form('Filamento',[('material','Material',f['material']),('color','Cor',f['color']),('kg','Preço por kg (R$)',str(Decimal(f['kg_cents'])/100))])
        if v:
            self.erp.filament(v['material'],v['color'],v['kg'],fid); self.refresh()

    @guarded
    def assign_color(self):
        if not self.product_options() or not self.filament_options():
            raise ValueError('Cadastre produto e filamento primeiro.')
        v=self.form('Consumo por unidade',[('pid','Produto',self.product_options()),('fid','Filamento',self.filament_options()),('grams','Gramas por unidade (zero remove)','0')])
        if v:
            self.erp.set_color(v['pid'],v['fid'],v['grams']); self.refresh()

    @guarded
    def copy_costs(self):
        if len(self.product_options())<2:
            raise ValueError('Cadastre pelo menos dois produtos.')
        v=self.form('Copiar custos e cores',[('source','Copiar de',self.product_options()),('target','Aplicar em',self.product_options())],
                    'Substitui peso, horas, fabricação manual, embalagem, outros e cores do destino. SKUs e custos históricos dos pedidos são preservados.')
        if v and self.ask('Substituir custos?','Aplicar os custos e cores do produto de origem no destino?'):
            self.erp.copy_costs(v['source'],v['target']); self.refresh()

    @guarded
    def slicing(self):
        if not self.product_options():
            raise ValueError('Cadastre o produto antes de ler o arquivo.')
        path,_=QFileDialog.getOpenFileName(self,'Metadados de fatiamento','','Fatiamento (*.3mf *.gcode *.gco)')
        if not path:return
        plates=read_slicing(path)
        v=self.form('Placa e quantidade',[('pid','Produto',self.product_options()),('plate','Placa',[(p['name'],i) for i,p in enumerate(plates)]),('units','Unidades deste produto na placa','1')],
                    'Use uma placa com apenas unidades deste produto. Em placas mistas, o consumo total não pode ser atribuído corretamente a um único produto.')
        if not v:return
        data=per_unit(plates[v['plate']],v['units']); pid=v['pid']
        if not preview(self,'Consumo por unidade',[{'metadado':'Horas','valor':data['hours'] or 'Não informado'}]+[{'metadado':c['label'],'valor':c['grams']+' g'} for c in data['colors']],
                       'Associe cada filamento ao cadastro na próxima etapa. Se houver consumo, as cores atuais serão substituídas. Horas ausentes serão preservadas.'):
            return
        assignments=[]
        for c in data['colors']:
            if not self.filament_options():
                raise ValueError('Cadastre os filamentos antes de aplicar o consumo por cor.')
            a=self.form('Associar filamento',[('fid',f"{c['label']} • {c['grams']} g",self.filament_options())])
            if not a:return
            assignments.append((a['fid'],Decimal(c['grams'])))
        totals={}
        for fid,g in assignments:totals[fid]=totals.get(fid,Decimal(0))+g
        self.s.backup()
        with self.s.transaction():
            if data['hours'] is not None:self.s.db.execute('UPDATE products SET hours=? WHERE id=?',(data['hours'],pid))
            if data['colors']:
                self.s.db.execute('DELETE FROM product_colors WHERE product_id=?',(pid,))
                self.s.db.executemany('INSERT INTO product_colors VALUES(?,?,?)',[(pid,fid,str(g)) for fid,g in totals.items()])
            self.s.log('metadados_fatiamento',{'produto':pid,'placa':data['name'],'unidades':v['units']})
        self.refresh(); self.info('Metadados aplicados por unidade. Nenhum comando de impressão foi executado.')

    def build_pricing(self):
        p=Page('Precificação transparente','Margem é lucro dividido pelo preço de venda. Acréscimo é lucro desejado sobre o custo, após as taxas configuradas.')
        self.pricing_product=QComboBox(); p.toolbar.addWidget(self.pricing_product)
        p.button('Calcular',self.update_price,True); p.button('Editar taxas e parâmetros',lambda:self.nav.setCurrentRow(9))
        self.price_detail=QTextBrowser(); p.layout.addWidget(self.price_detail)
        return p,self.update_pricing

    def update_pricing(self):
        current=self.pricing_product.currentData(); self.pricing_product.clear()
        for name,pid in self.product_options():self.pricing_product.addItem(name,pid)
        if current:self.pricing_product.setCurrentIndex(max(0,self.pricing_product.findData(current)))
        self.update_price()

    @guarded
    def update_price(self):
        pid=self.pricing_product.currentData()
        if pid is None:
            self.price_detail.setPlainText('Cadastre um produto para calcular sua composição de custo.'); return
        c=self.erp.cost(pid); settings=self.s.settings()
        lines=[('Filamento calculado',c['material_cents']),('Energia calculada',c['energy_cents']),('Máquina calculada',c['machine_cents']),
               ('Fabricação utilizada'+(' (manual)' if c['manual'] else ''),c['manufacture_cents']),('Embalagem',c['packaging_cents']),('Outros',c['other_cents']),
               ('Custo total por unidade',c['total_cents']),('Taxas no preço sugerido',c['fees_cents']),('Lucro no preço sugerido',c['profit_cents']),('Preço sugerido',c['suggested_cents'])]
        self.price_detail.setHtml('<h2>'+text(self.erp.product(pid)['name'])+'</h2><table width="85%">'+''.join(f'<tr><td style="padding:10px">{text(k)}</td><td style="color:#ffb574">{money(v)}</td></tr>' for k,v in lines)+
            f"</table><p>{text(c['grams'])} g • {text(c['hours'])} h • {text(', '.join(c['missing']) or 'Cadastro completo')}</p>"+
            f"<p>Modo: {text(settings['pricing_mode'])} • percentual: {text(settings['profit_percent'])}% • taxa: {text(settings['fee_percent'])}% + R$ {text(settings['fee_fixed'])}</p>"+
            '<p>Margem: preço = (custo + taxa fixa) / (1 − taxa percentual − margem).<br>Acréscimo: preço = (custo × (1 + acréscimo) + taxa fixa) / (1 − taxa percentual).</p>'+
            '<p>O custo manual substitui material, energia e máquina. Os três componentes calculados acima servem apenas para comparação quando há custo manual. Taxas são parâmetros que você deve revisar; não são regras atuais garantidas da Shopee.</p>')

    def build_skus(self):
        p=Page('Catálogo e vínculos de SKU','Vermelho indica o mesmo SKU em produtos diferentes. Corrija o vínculo ou código; os produtos nunca são unidos automaticamente.')
        self.sku_search=QLineEdit(); self.sku_search.setPlaceholderText('Buscar SKU, anúncio ou produto'); self.sku_search.textChanged.connect(lambda:self.update_skus()); p.toolbar.addWidget(self.sku_search)
        p.button('+ Origem',lambda:self.edit_origin(),True); p.button('Corrigir / vincular',lambda:self.edit_origin(self.origins_table.selected()['id']))
        p.button('Desvincular',self.unlink_origin); p.button('Reservar SKU',self.reserve_sku); p.button('Aposentar',self.retire_sku)
        p.button('Exportar',lambda:self.export_rows('Catálogo',[],{'Origens':self.origin_rows(),'Códigos':self.s.rows('SELECT * FROM sku_codes ORDER BY code')}))
        self.origins_table=p.table(); self.sku_codes_table=p.table()
        return p,self.update_skus

    def origin_rows(self):
        conflicts=self.erp.conflicts()
        rows=self.s.rows('SELECT o.*,p.name product_name,p.model FROM origins o LEFT JOIN products p ON p.id=o.product_id ORDER BY o.sku,o.listing')
        for r in rows:r['conflict']='CONFLITO' if r['sku'] in conflicts else ''
        return rows

    @guarded
    def update_skus(self):
        q=self.sku_search.text().casefold()
        rows=[r for r in self.origin_rows() if q in ' '.join(str(r.get(k) or '') for k in ('sku','listing','variation','product_name','model')).casefold()]
        self.origins_table.fill(rows,[('id','Origem ID'),('sku','SKU (texto)'),('product_name','Produto físico'),('model','Modelo'),('listing','Anúncio'),('variation','Variação'),('active','Ativa'),('conflict','Conflito')],lambda r:bool(r['conflict']))
        self.sku_codes_table.fill([r for r in self.s.rows('SELECT * FROM sku_codes ORDER BY code') if q in r['code'].casefold()],[('code','Código reservado / utilizado'),('state','Situação')])

    @guarded
    def edit_origin(self,oid=None):
        old=self.s.one('SELECT * FROM origins WHERE id=?',(oid,)) if oid else {'listing':'','variation':'','sku':'','product_id':None,'source':'Shopee'}
        options=self.product_options(True)
        options.sort(key=lambda x:x[1]!=old['product_id'])
        suggestions=self.erp.suggestions(old['listing'],old['variation']) if oid else []
        note='Vincular é uma decisão manual. Confira personagem, modelo e tamanho. Corrigir o vínculo atualiza a identificação dos pedidos, preservando SKU original e custo já congelado.'
        if suggestions: note+=' Sugestões para revisão: '+', '.join(p['name']+' / '+p['model'] for p in suggestions)
        v=self.form('Origem de anúncio',[('source','Canal',old['source']),('listing','Anúncio',old['listing']),('variation','Variação',old['variation']),('sku','SKU (texto)',old['sku']),('pid','Produto físico',options)],note)
        if v:
            self.erp.origin(v['listing'],v['variation'],v['sku'],v['pid'],oid,v['source']); self.refresh()
            if v['sku'] in self.erp.conflicts():self.info('Conflito de SKU registrado e destacado em vermelho. Corrija o código ou vínculo; não una produtos diferentes.')

    @guarded
    def unlink_origin(self):
        oid=self.origins_table.selected()['id']
        if self.ask('Desvincular origem?','Desativar esta origem? Os pedidos mantêm sua identificação e seus custos históricos.'):
            self.erp.unlink(oid); self.refresh()

    @guarded
    def reserve_sku(self):
        v=self.form('Reservar SKU',[('code','Código manual (vazio = próximo numérico)','')],
                    'Códigos usados e aposentados nunca são reutilizados automaticamente. O próximo numérico ignora também equivalentes com outros zeros à esquerda.')
        if v:
            code=self.erp.reserve(v['code'] or None); self.refresh(); self.info('Reservado: '+code)

    @guarded
    def retire_sku(self):
        code=self.sku_codes_table.selected()['code']
        if self.ask('Aposentar SKU?',f'O código {code} ficará permanentemente indisponível para novas atribuições.'):
            self.erp.retire(code); self.refresh()

    def build_orders(self):
        p=Page('Pedidos','Cada pedido possui seu próprio total e várias linhas de itens. Reimportações preservam custos já congelados para os itens identificados.')
        self.order_search=QLineEdit(); self.order_search.setPlaceholderText('Buscar ID, status ou SKU original'); self.order_search.textChanged.connect(lambda:self.update_orders()); p.toolbar.addWidget(self.order_search)
        self.order_status=QComboBox()
        for label,value in [('Todos os status',''),('Ativos','ativo'),('Cancelados','cancelado'),('Devoluções / reembolsos','devolucao')]:self.order_status.addItem(label,value)
        self.order_status.currentIndexChanged.connect(lambda:self.update_orders()); p.toolbar.addWidget(self.order_status)
        p.button('Ver itens',self.order_details,True); p.button('Corrigir status / reembolso',self.edit_order); p.button('Congelar custos pendentes',self.freeze_costs)
        p.button('Exportar',lambda:self.export_rows('Pedidos',[],{'Pedidos':self.filtered_orders(),'Itens':self.s.rows('SELECT * FROM order_items ORDER BY order_id,id')}))
        self.orders_table=p.table()
        return p,self.update_orders

    def filtered_orders(self):
        q=self.order_search.text().casefold(); kind=self.order_status.currentData()
        rows=self.s.rows('SELECT o.*,count(i.id) items,sum(CASE WHEN i.cost_cents IS NULL THEN 1 ELSE 0 END) missing FROM orders o LEFT JOIN order_items i ON i.order_id=o.id GROUP BY o.id ORDER BY date DESC,id')
        result=[]
        for r in rows:
            skus=' '.join(x['original_sku'] for x in self.s.rows('SELECT original_sku FROM order_items WHERE order_id=?',(r['id'],)))
            if q in (r['id']+' '+r['status']+' '+skus).casefold() and (not kind or status_kind(r['status'])==kind):result.append(r)
        return result

    @guarded
    def update_orders(self):
        self.orders_table.fill(self.filtered_orders(),[('id','ID do pedido'),('date','Data'),('status','Status'),('items','Itens'),('gross_cents','Total'),('fees_cents','Taxas'),('refund_cents','Reembolso'),('missing','Itens sem custo'),('partial','Dados parciais')])

    @guarded
    def order_details(self):
        oid=self.orders_table.selected()['id']
        rows=self.s.rows('SELECT i.*,p.name product_name FROM order_items i LEFT JOIN products p ON p.id=i.product_id WHERE order_id=?',(oid,))
        d=QDialog(self); d.setWindowTitle('Pedido '+oid); d.resize(1160,650); layout=QVBoxLayout(d)
        layout.addWidget(QLabel('Custo por unidade congelado na data indicada. Alterações de cadastro não recalculam esse valor.'))
        table=Table(); table.fill(rows,[('title','Anúncio original'),('variation','Variação'),('original_sku','SKU original'),('product_name','Produto associado'),('qty','Quantidade'),('unit_cents','Preço unitário'),('cost_cents','Custo congelado / un.'),('cost_at','Congelado em')]); layout.addWidget(table)
        detail=QTextBrowser(); detail.setMaximumHeight(180); layout.addWidget(detail)
        table.itemSelectionChanged.connect(lambda:detail.setPlainText(json.dumps(json.loads(table.selected()['cost_detail']),indent=2,ensure_ascii=False) if table.selected()['cost_detail'] else 'Sem custo congelado.'))
        button=QPushButton('Fechar'); button.clicked.connect(d.accept); layout.addWidget(button); d.exec()

    @guarded
    def edit_order(self):
        o=self.orders_table.selected()
        v=self.form('Correção de pedido',[('status','Status',o['status']),('fees','Taxas efetivas totais (R$)',str(Decimal(o['fees_cents'])/100)),('refund','Reembolso efetivo (R$)',str(Decimal(o['refund_cents'])/100))],
                    'Cancelados ficam fora das vendas e do custo operacional. Devoluções mantêm custo de produção, e o reembolso reduz a receita. Taxas devem refletir o valor efetivamente retido.')
        if not v:return
        from ..business.numbers import cents
        if not v['status']:raise ValueError('Status obrigatório.')
        fees,refund=cents(v['fees']),cents(v['refund'])
        self.s.backup()
        with self.s.transaction():
            self.s.db.execute('UPDATE orders SET status=?,fees_cents=?,refund_cents=?,updated=CURRENT_TIMESTAMP WHERE id=?',(v['status'],fees,refund,o['id']))
            self.s.log('corrigir_pedido',{'id':o['id'],'antes':{k:o[k] for k in ('status','fees_cents','refund_cents')},'depois':v})
        self.refresh()

    @guarded
    def freeze_costs(self):
        if self.ask('Congelar custos pendentes?','Gravar o custo atual dos produtos completos nos itens sem custo? A data de congelamento será agora, não a data histórica da venda. Custos já congelados serão preservados.'):
            self.s.backup(); count=self.erp.freeze_missing_costs(); self.refresh(); self.info(f'{count} itens receberam custo congelado com data atual.')

    def build_imports(self):
        p=Page('Importação com revisão','Os arquivos são lidos como dados. Nenhuma alteração é feita antes da confirmação da prévia.')
        p.button('Pedidos Shopee XLSX',self.import_order_file,True); p.button('Estatísticas da loja',self.import_stats_file); p.button('Cadastros / despesas',self.import_catalog); p.button('Modelos vazios',self.save_templates)
        browser=QTextBrowser(); p.layout.addWidget(browser)
        browser.setHtml('''<h2>Importe a fonte certa para cada finalidade</h2><h3>Pedidos detalhados</h3>
        <p>Selecione a aba e a linha de cabeçalho. Revise o mapeamento de colunas, confira SKUs, valores e todos os itens do pedido antes de confirmar.</p>
        <p><b>Order.toship cobre somente A Enviar.</b> Para cobertura mensal, use Todos os pedidos / Order.all. Um arquivo parcial não apaga os demais pedidos do mês.</p>
        <p>O arquivo deve conter todos os itens de cada ID presente. Total e taxas pertencem ao pedido; não são multiplicados pela quantidade de itens.</p>
        <h3>Estatísticas mensais</h3><p>Selecione o período exato do arquivo e informe se cobre apenas parte do mês. Importe linhas de anúncios, sem a linha de total.
        Estatísticas não criam pedidos, SKUs nem produtos físicos. A comparação considera receita bruta dos pedidos no mesmo período, que pode usar critérios diferentes do marketplace.</p>
        <h3>Cadastros</h3><p>Use os modelos vazios. Produtos, filamentos e despesas são novos registros; uma reimportação desses cadastros não é idempotente. Revise duplicidades. Pedidos e estatísticas possuem atualização por chave.</p>
        <h3>Proteção de dados</h3><p>CPF, nome de comprador, endereço e telefone não são mapeados nem gravados. A prévia de pedidos exibe apenas os campos de gestão.</p>
        <p>Não são aceitas fórmulas. Para planilhas com fórmulas, salve uma cópia somente com valores. Zeros de SKUs armazenados como números sem máscara não podem ser recuperados com certeza.</p>''')
        return p,lambda:None

    def choose_sheet(self,path):
        # Sheet names are discovered first; the final read uses an explicit header row.
        from openpyxl import load_workbook
        from zipfile import ZipFile
        path=Path(path)
        if path.stat().st_size>32*1024*1024:raise ValueError('XLSX excede 32 MB.')
        with ZipFile(path) as z:
            if len(z.infolist())>4096 or sum(i.file_size for i in z.infolist())>128*1024*1024:raise ValueError('XLSX excede limites de estrutura.')
        wb=load_workbook(path,read_only=True,data_only=False,keep_links=False)
        names=wb.sheetnames; wb.close()
        v=self.form('Aba e cabeçalho',[('sheet','Aba',[(n,n) for n in names]),('header','Linha do cabeçalho (1 = primeira)','1')],
                    'Se houver título ou instruções antes da tabela, informe a linha em que começam os nomes das colunas.')
        if not v:return None
        from ..business.numbers import quantity
        return read_xlsx(path,v['sheet'],quantity(v['header'])-1)[:2]

    def mapping(self,headers,keys):
        automatic=detect(headers,keys)
        fields=[]
        for key in keys:
            options=[('Não importar / não disponível','')]+[(h,h) for h in headers]
            options.sort(key=lambda x:x[1]!=automatic[key])
            fields.append((key,IMPORT_LABELS[key],options))
        return self.form('Mapear colunas',fields,'Selecione colunas do arquivo. Taxas: escolha o total OU os componentes. Total, taxas e reembolso são valores por pedido, repetidos nas linhas de itens.')

    @guarded
    def import_order_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Pedidos Shopee','','Planilha (*.xlsx)')
        if not path:return
        loaded=self.choose_sheet(path)
        if not loaded:return
        headers,rows=loaded; mapping=self.mapping(headers,['order_id','date','status','listing','variation','sku','qty','unit','gross','fees','commission','service','transaction','refund'])
        if not mapping:return
        partial=self.ask('Cobertura do arquivo','O arquivo contém apenas uma parte dos pedidos do período (por exemplo, somente A Enviar)?')
        orders,warnings=preview_orders(rows,mapping,Path(path).name,partial)
        flat=[]
        for o in orders:
            for i in o['items']:
                candidates=self.erp.suggestions(i['title'],i['variation'])
                flat.append({**{k:v for k,v in o.items() if k!='items'},**i,'sugestao_revisao':'; '.join(p['name']+' / '+p['model'] for p in candidates)})
        if not orders:raise ValueError('Nenhum pedido encontrado.')
        if preview(self,'Prévia de pedidos • nenhum vínculo será criado automaticamente',flat,'\n'.join(warnings)):
            backup=import_orders(self.erp,orders); self.info(f'{len(orders)} pedidos importados.\nBackup anterior: {backup}\nRevise as origens sem vínculo em Catálogo e SKUs.')

    @guarded
    def import_stats_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Estatísticas mensais','','Planilha (*.xlsx)')
        if not path:return
        loaded=self.choose_sheet(path)
        if not loaded:return
        headers,rows=loaded; mapping=self.mapping(headers,['listing','revenue','orders_count'])
        if not mapping:return
        v=self.form('Cobertura das estatísticas',[('start','Início (DD/MM/AAAA)',date.today().replace(day=1).strftime('%d/%m/%Y')),('end','Fim (DD/MM/AAAA)',date.today().strftime('%d/%m/%Y')),
                     ('partial','Cobertura',[('Parcial',True),('Mês completo',False)])], 'Informe as datas efetivamente cobertas. Não inclua uma linha de total junto aos anúncios.')
        if not v:return
        prepared=preview_stats(rows,mapping,v['start'],v['end'],v['partial'])
        if preview(self,'Prévia de estatísticas',prepared,'Resumo separado: estes valores NÃO serão adicionados às vendas detalhadas.'):
            backup=import_stats(self.erp,prepared); self.info(f'Estatísticas gravadas. Backup: {backup}')

    @guarded
    def import_catalog(self):
        v=self.form('Tipo de modelo',[('kind','Importação',[('Produtos (novos)','produtos'),('Filamentos (novos)','filamentos'),('Despesas (novas)','despesas')])],
                    'Use os modelos gerados pelo aplicativo. Esta importação adiciona registros: verifique duplicidades antes de confirmar.')
        if not v:return
        path,_=QFileDialog.getOpenFileName(self,'Importar modelo preenchido','','Planilha (*.xlsx)')
        if not path:return
        loaded=self.choose_sheet(path)
        if not loaded:return
        _,rows=loaded; prepared=catalog.prepare(rows,v['kind'])
        if preview(self,'Prévia • '+v['kind'],prepared,'Novos registros. Não use para editar cadastros existentes.'):
            backup=catalog.commit(self.erp,prepared,v['kind']); self.info(f'Importação concluída. Backup: {backup}')

    @guarded
    def save_templates(self):
        folder=QFileDialog.getExistingDirectory(self,'Salvar modelos vazios')
        if folder:templates(folder); self.info('Modelos XLSX vazios e instruções salvos na pasta escolhida.')

    def build_finance(self):
        p=Page('Financeiro','Compras de filamento são saída de caixa para estoque; consumo na fabricação compõe o resultado. Não são descontados juntos no resultado operacional.')
        p.button('+ Despesa',self.add_expense,True); p.button('+ Compra de filamento',self.add_purchase); p.button('Editar lançamento',self.edit_financial); p.button('Excluir lançamento',self.delete_financial)
        p.button('Exportar',lambda:self.export_rows('Financeiro',[],{'Despesas':self.s.rows('SELECT * FROM expenses ORDER BY date'),'Compras':self.purchase_rows()}))
        self.finance_tabs=QTabWidget(); p.layout.addWidget(self.finance_tabs)
        self.expenses_table=Table(); self.purchases_table=Table()
        self.finance_tabs.addTab(self.expenses_table,'Despesas'); self.finance_tabs.addTab(self.purchases_table,'Compras de filamento')
        return p,self.update_finance

    def purchase_rows(self):
        return self.s.rows('SELECT b.*,f.material,f.color FROM purchases b JOIN filaments f ON f.id=b.filament_id ORDER BY date DESC,b.id DESC')

    @guarded
    def update_finance(self):
        self.expenses_table.fill(self.s.rows('SELECT * FROM expenses ORDER BY date DESC,id DESC'),[('id','ID'),('date','Data'),('category','Categoria'),('description','Descrição'),('amount_cents','Valor')])
        self.purchases_table.fill(self.purchase_rows(),[('id','ID'),('date','Data'),('material','Material'),('color','Cor'),('grams','Peso comprado (g)'),('amount_cents','Valor'),('freight_cents','Frete')])

    @guarded
    def add_expense(self):
        v=self.form('Nova despesa',[('date','Data',date.today().strftime('%d/%m/%Y')),('category','Categoria',''),('description','Descrição',''),('amount','Valor (R$)','0')])
        if v:
            self.erp.expense(**v); self.refresh()

    @guarded
    def add_purchase(self):
        if not self.filament_options():raise ValueError('Cadastre um filamento em Custos e cores.')
        v=self.form('Compra de filamento',[('date','Data',date.today().strftime('%d/%m/%Y')),('fid','Filamento',self.filament_options()),('grams','Peso comprado (g)','1000'),('amount','Valor do material (R$)','0'),('freight','Frete (R$)','0')],
                    'A compra não altera automaticamente o preço de referência por kg. Revise esse preço em Custos e cores. Nenhum custo histórico é recalculado.')
        if v:self.erp.purchase(**v); self.refresh()

    @guarded
    def edit_financial(self):
        from ..business.numbers import cents,decimal
        is_purchase=self.finance_tabs.currentIndex()==1
        r=(self.purchases_table if is_purchase else self.expenses_table).selected()
        fields=[('date','Data',day(r['date']))]
        if is_purchase:
            options=self.filament_options(); options.sort(key=lambda x:x[1]!=r['filament_id'])
            fields += [('fid','Filamento',options),('grams','Peso comprado (g)',r['grams']),('amount','Material (R$)',str(Decimal(r['amount_cents'])/100)),('freight','Frete (R$)',str(Decimal(r['freight_cents'])/100))]
        else:
            fields += [('category','Categoria',r['category']),('description','Descrição',r['description']),('amount','Valor (R$)',str(Decimal(r['amount_cents'])/100))]
        v=self.form('Editar lançamento',fields)
        if not v:return
        d=day(v['date']); amount=cents(v['amount'])
        if is_purchase:
            grams=decimal(v['grams']); freight=cents(v['freight'])
            if not grams:raise ValueError('Peso comprado deve ser positivo.')
        elif not v['category']:raise ValueError('Categoria obrigatória.')
        with self.s.transaction():
            if is_purchase:self.s.db.execute('UPDATE purchases SET date=?,filament_id=?,grams=?,amount_cents=?,freight_cents=? WHERE id=?',(d,v['fid'],str(grams),amount,freight,r['id']))
            else:self.s.db.execute('UPDATE expenses SET date=?,category=?,description=?,amount_cents=? WHERE id=?',(d,v['category'],v['description'],amount,r['id']))
            self.s.log('editar_lancamento',{'tipo':'compra' if is_purchase else 'despesa','id':r['id'],'antes':r,'depois':v})
        self.refresh()

    @guarded
    def delete_financial(self):
        purchase=self.finance_tabs.currentIndex()==1
        r=(self.purchases_table if purchase else self.expenses_table).selected()
        if self.ask('Excluir lançamento?',f"Excluir o lançamento #{r['id']}? Será criado backup e registro no histórico."):
            self.s.backup()
            with self.s.transaction():
                if purchase:self.s.db.execute('DELETE FROM purchases WHERE id=?',(r['id'],))
                else:self.s.db.execute('DELETE FROM expenses WHERE id=?',(r['id'],))
                self.s.log('excluir_lancamento',{'tipo':'compra' if purchase else 'despesa','anterior':r})
            self.refresh()

    def build_reports(self):
        p=Page('Relatórios e conciliação','Filtros por período, produto e status. Custos são os congelados nos itens; ausências são sinalizadas como DADOS PARCIAIS.')
        self.report_start=QLineEdit(date.today().replace(day=1).strftime('%d/%m/%Y')); self.report_start.setMaximumWidth(115)
        self.report_end=QLineEdit(date.today().strftime('%d/%m/%Y')); self.report_end.setMaximumWidth(115)
        p.toolbar.addWidget(QLabel('De')); p.toolbar.addWidget(self.report_start); p.toolbar.addWidget(QLabel('até')); p.toolbar.addWidget(self.report_end)
        self.report_product=QComboBox(); p.toolbar.addWidget(self.report_product)
        self.report_status=QComboBox()
        for label,value in [('Todos os status',''),('Ativos','ativo'),('Cancelados','cancelado'),('Devoluções','devolucao')]:self.report_status.addItem(label,value)
        p.toolbar.addWidget(self.report_status)
        p.button('Consultar',self.update_report,True); p.button('Exportar XLSX',self.export_report);p.button('Exportar PDF',self.export_report_pdf)
        self.report_tabs=QTabWidget(); p.layout.addWidget(self.report_tabs)
        self.report_browser=QTextBrowser(); self.best_table=Table(); self.consumption_table=Table(); self.monthly_table=Table(); self.stats_table=Table()
        for label,widget in [('Resultado',self.report_browser),('Mais vendidos',self.best_table),('Consumo',self.consumption_table),('Histórico mensal',self.monthly_table),('Estatísticas de anúncios',self.stats_table)]:self.report_tabs.addTab(widget,label)
        graph_scroll=QScrollArea();graph_scroll.setWidgetResizable(True);graph_content=QWidget();grid=QGridLayout(graph_content);grid.setSpacing(14)
        self.report_charts=[ChartCard('Vendas por dia','Vendas brutas · filtros atuais'),ChartCard('Composição dos custos','Produção, taxas, despesas e reembolsos · sem compras para estoque'),ChartCard('Produtos mais vendidos','Unidades do período · filtros atuais'),ChartCard('Consumo por material e cor','Gramas dos custos congelados · filtros atuais')]
        for index,card in enumerate(self.report_charts):grid.addWidget(card,index//2,index%2)
        graph_scroll.setWidget(graph_content);self.report_tabs.addTab(graph_scroll,'Gráficos')
        remove=QPushButton('Excluir linha de estatísticas selecionada (com backup)'); remove.clicked.connect(self.delete_stat); p.layout.addWidget(remove);remove.hide();self.report_tabs.currentChanged.connect(lambda index:remove.setVisible(index==4))
        return p,self.refresh_reports

    def refresh_reports(self):
        current=self.report_product.currentData(); self.report_product.clear(); self.report_product.addItem('Todos os produtos',None)
        for name,pid in self.product_options():self.report_product.addItem(name,pid)
        if current:self.report_product.setCurrentIndex(max(0,self.report_product.findData(current)))
        self.update_report()

    def current_report(self):
        return report(self.erp,self.report_start.text(),self.report_end.text(),self.report_product.currentData(),self.report_status.currentData())

    @guarded
    def update_report(self):
        r=self.current_report()
        labels={'gross_cents':'Vendas brutas','refunds_cents':'Reembolsos efetivos','fees_cents':'Taxas retidas','production_cents':'Produção (custos congelados)',
                'expenses_cents':'Despesas gerais do período','purchases_cents':'Compras de filamento + frete (somente caixa)','operating_cents':'Resultado operacional',
                'cash_cents':'Caixa estimado','stats_cents':'Estatísticas — comparação separada','difference_cents':'Estatísticas menos pedidos brutos'}
        self.report_browser.setHtml(f"<h2 style='color:#ffb574'>{'DADOS PARCIAIS' if r['partial'] else 'Fontes conciliadas no período'}</h2><p>{r['orders_count']} pedidos · {r['pending_items']} itens sem custo</p>"+
            '<table width="90%">'+''.join(f'<tr><td style="padding:9px">{v}</td><td>{money(r[k])}</td></tr>' for k,v in labels.items())+'</table>'+
            '<p>Resultado = vendas − reembolsos − taxas − produção − despesas. Compra de filamento não é novamente descontada do resultado.</p>'+
            '<p>Caixa estimado = vendas − reembolsos − taxas − despesas − compras de filamento. É uma aproximação com datas de pedidos e lançamentos, sem conciliação de repasses, sem todas as saídas de embalagem/energia e sem saldo inicial. Não é saldo bancário.</p>'+
            '<p>Cancelados são excluídos de vendas e produção; produção perdida deve ser lançada como despesa. Devoluções mantêm o custo de produção: não se presume retorno ao estoque. Preencha o reembolso efetivo; valor ausente causa DADOS PARCIAIS.</p>'+
            '<p>Filtro por produto rateia total, taxas e reembolso pelo valor dos itens. Despesas e compras continuam gerais do período; não se trata de lucro líquido isolado do produto. Histórico mensal abrange todos os produtos e status, sem esses filtros.</p>'+
            '<p>Estatísticas são agrupadas por anúncio e período. Períodos que cruzam o filtro não são rateados: constam na aba de estatísticas, mas não no total comparável. Contagem de pedidos por anúncio não equivale a pedidos únicos da loja.</p>')
        self.report_charts[0].caption.setText(('DADOS PARCIAIS · ' if r['partial'] else '')+'Vendas brutas · filtros atuais')
        self.report_charts[0].line(r['sales_by_day'])
        self.report_charts[1].donut([('Produção',r['production_cents']),('Taxas',r['fees_cents']),('Despesas',r['expenses_cents']),('Reembolsos',r['refunds_cents'])])
        self.report_charts[2].bars(r['best_sellers'],'product','qty')
        consumption={}
        for item in r['consumption']:
            key=item['material']+' / '+item['color'];consumption[key]=consumption.get(key,Decimal(0))+Decimal(item['grams'])
        self.report_charts[3].bars([{'color':key,'grams':str(value)} for key,value in sorted(consumption.items(),key=lambda item:-item[1])],'color','grams','g')
        self.best_table.fill(r['best_sellers'],[('product','Produto físico / origem sem vínculo'),('qty','Unidades (inclui devoluções)'),('revenue_cents','Valor dos itens, antes de reembolsos')])
        self.consumption_table.fill(r['consumption'],[('month','Mês'),('fortnight','Quinzena'),('material','Material'),('color','Cor'),('grams','Consumo g')])
        self.monthly_table.fill(monthly(self.erp),[('month','Mês'),('gross_cents','Vendas'),('production_cents','Produção'),('expenses_cents','Despesas'),('operating_cents','Resultado'),('cash_cents','Caixa estimado'),('partial','Dados parciais')])
        self.stats_table.fill(r['stats'],[('start','Início'),('end','Fim'),('listing','Anúncio (não é produto físico)'),('revenue_cents','Receita resumo'),('orders_count','Pedidos por anúncio'),('partial','Parcial')])

    @guarded
    def export_report(self):
        r=self.current_report()
        summary=[{'indicador':LABELS.get(k,k),'valor':money(v) if k.endswith('_cents') else str(v)} for k,v in r.items() if not isinstance(v,list)]
        self.export_rows('Relatório',[],{'Resumo':summary,'Mais vendidos':r['best_sellers'],'Consumo':r['consumption'],'Mensal':monthly(self.erp),'Estatísticas':r['stats'],'Pedidos':r['orders'],'Despesas':r['expenses'],'Compras':r['purchases']})

    def build_settings(self):
        p=Page('Configurações e proteção dos dados','Parâmetros locais, backup consistente e histórico de operações. Este aplicativo usa apenas o banco novo do ERP 2.0.')
        p.button('Editar parâmetros',self.edit_settings,True); p.button('Criar backup',self.backup); p.button('Restaurar backup',self.restore); p.button('Verificar integridade',self.integrity)
        p.button('Histórico',self.audit)
        self.settings_browser=QTextBrowser(); p.layout.addWidget(self.settings_browser)
        return p,self.update_settings

    @guarded
    def update_settings(self):
        labels={'filament_kg':'Filamento padrão R$/kg (sem cores)','energy_kwh':'Energia R$/kWh','power_w':'Potência W','machine_hour':'Máquina R$/h',
                'fee_percent':'Taxa percentual %','fee_fixed':'Taxa fixa R$','pricing_mode':'Modo','profit_percent':'Margem / acréscimo %','sku_width':'Dígitos do próximo SKU'}
        self.settings_browser.setHtml('<h2>Parâmetros de precificação</h2><table>'+''.join(f'<tr><td style="padding:10px">{text(labels.get(k,k))}</td><td>{text(v)}</td></tr>' for k,v in self.s.settings().items() if k in labels)+'</table>'+
            '<h3>Taxas configuráveis</h3><p>Os valores iniciais de taxas são zero; revise as condições do seu canal. Não se assume regra atual da Shopee.</p>'+
            f'<h3>Armazenamento</h3><p>{text(self.s.path)}</p><p>Backups automáticos antes de importações ficam na subpasta backups. Faça também cópias em outra mídia.</p>'+
            '<p>O banco inicia vazio. Restauração aceita somente a identidade e a versão de esquema deste projeto. Antes de restaurar, o banco atual é preservado. O aplicativo bloqueia uma segunda instância no mesmo banco.</p>'+
            '<h3>Instalação transparente</h3><p>Sem atualização automática, scripts remotos, ofuscação ou alterações na instalação anterior. A reescrita não garante ausência de ameaças. Testes funcionais não são análise antivírus. Consulte a documentação de dependências e segurança no projeto.</p>')

    @guarded
    def edit_settings(self):
        s=self.s.settings()
        labels={'filament_kg':'Filamento padrão R$/kg','energy_kwh':'Energia R$/kWh','power_w':'Potência da impressora (W)','machine_hour':'Uso da máquina R$/h',
                'fee_percent':'Taxas percentuais %','fee_fixed':'Taxa fixa R$/unidade','profit_percent':'Margem ou acréscimo %','sku_width':'Dígitos do SKU numérico'}
        fields=[(k,label,s[k]) for k,label in labels.items()]
        modes=[('Margem sobre venda','margem'),('Acréscimo sobre custo','acrescimo')]; modes.sort(key=lambda x:x[1]!=s['pricing_mode'])
        fields.append(('pricing_mode','Método',modes))
        v=self.form('Parâmetros',fields,'Margem + taxas deve ser inferior a 100%. Taxa fixa é aplicada por unidade na sugestão; pedidos usam as taxas efetivas importadas.')
        if v:self.erp.save_settings(v); self.refresh()

    @guarded
    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Backup novo',f'forgeon2-{date.today()}.sqlite3','SQLite (*.sqlite3)')
        if path:
            result=self.s.backup(path); self.info(f'Backup criado e integridade verificada:\n{result}')

    @guarded
    def restore(self):
        path,_=QFileDialog.getOpenFileName(self,'Restaurar backup compatível','','SQLite (*.sqlite3)')
        if path and self.ask('Restaurar banco?','Substituir os dados atuais pelos do backup? Antes será preservada uma cópia consistente do banco atual.'):
            saved=self.s.restore(path); self.refresh(); self.info(f'Banco restaurado. Banco anterior preservado em:\n{saved}')

    @guarded
    def integrity(self):
        self.s.validate(self.s.db); self.info('Verificações SQLite de integridade e chaves estrangeiras concluídas sem erros.')

    @guarded
    def audit(self):
        d=QDialog(self); d.setWindowTitle('Histórico de operações'); d.resize(1100,650); layout=QVBoxLayout(d)
        t=Table(); t.fill(self.s.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 2000'),[('date','Data/hora'),('operation','Operação'),('detail','Detalhes')]); layout.addWidget(t)
        b=QPushButton('Fechar'); b.clicked.connect(d.accept); layout.addWidget(b); d.exec()


    @guarded
    def delete_stat(self):
        if self.report_tabs.currentIndex()!=4:
            raise ValueError('Selecione a aba Estatísticas de anúncios e uma linha primeiro.')
        r=self.stats_table.selected()
        if self.ask('Excluir estatística?', 'Excluir apenas esta linha do resumo? Pedidos detalhados não serão alterados.'):
            self.s.backup()
            with self.s.transaction():
                self.s.db.execute('DELETE FROM stats WHERE id=?',(r['id'],))
                self.s.log('excluir_estatistica',r)
            self.update_report()


    def build_updates(self):
        self.updates_page=UpdatesPage(self)
        return self.updates_page,lambda:None

    @guarded
    def toggle_focus(self,enabled):
        self.backdrop.set_focus(enabled)
        with self.s.transaction():
            self.s.db.execute("INSERT INTO settings(key,value) VALUES('appearance_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('1' if enabled else '0',))

    @guarded
    def export_report_pdf(self):
        r=self.current_report()
        path,_=QFileDialog.getSaveFileName(self,'Exportar relatório PDF','relatorio-forgeon.pdf','Documento PDF (*.pdf)')
        if not path:return
        document=QTextDocument();document.setDefaultFont(QFont('Segoe UI',10))
        html_text=f"<h1>FORGEON STUDIO · Relatório gerencial</h1><p>Versão {VERSION} · {date.fromisoformat(r['start']).strftime('%d/%m/%Y')} a {date.fromisoformat(r['end']).strftime('%d/%m/%Y')}</p><p>Produto: {text(self.report_product.currentText())} · Status: {text(self.report_status.currentText())}</p><h2>{'DADOS PARCIAIS' if r['partial'] else 'Fontes conciliadas no período'}</h2>"
        html_text+='<table width="100%" border="0" cellspacing="8">'
        for key,label in [('gross_cents','Vendas brutas'),('refunds_cents','Reembolsos'),('fees_cents','Taxas'),('production_cents','Produção congelada'),('expenses_cents','Despesas'),('operating_cents','Resultado operacional'),('cash_cents','Caixa estimado')]:
            html_text+=f'<tr><td>{label}</td><td>{money(r[key])}</td></tr>'
        html_text+='</table><p>Caixa estimado não é saldo bancário. Estatísticas não são somadas às vendas. Custos ausentes geram dados parciais. Despesas gerais permanecem do período mesmo com filtro por produto.</p><h2>Produtos mais vendidos</h2><table cellspacing="8">'
        for item in r['best_sellers'][:12]:html_text+=f"<tr><td>{text(item['product'])}</td><td>{item['qty']} un.</td><td>{money(item['revenue_cents'])}</td></tr>"
        html_text+='</table><h2>Gráficos do período</h2>'
        current=self.report_tabs.currentIndex();self.report_tabs.setCurrentIndex(5);QApplication.processEvents()
        for index,card in enumerate(self.report_charts):
            resource=QUrl(f'forgeon-chart-{index}')
            document.addResource(QTextDocument.ResourceType.ImageResource,resource,card.grab().toImage())
            html_text+=f'<p><img src="forgeon-chart-{index}" width="630" height="310"></p>'
        self.report_tabs.setCurrentIndex(current)
        document.setHtml('<body style="color:#142238">'+html_text+'</body>')
        writer=QPdfWriter(path);writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4));writer.setResolution(96);writer.setTitle('FORGEON STUDIO · Relatório gerencial');document.print_(writer)
        self.info('Relatório PDF exportado com filtros, indicadores e gráficos.')

    def closeEvent(self,event):
        if hasattr(self,'updates_page') and self.updates_page.task and self.updates_page.task.isRunning():
            self.updates_page.task.cancel.set()
            if not self.updates_page.task.wait(16000):
                event.ignore();self.statusBar().showMessage('Aguarde a consulta/download terminar para fechar.');return
        super().closeEvent(event)
