"""Uma prévia para arquivos reconhecidos, sem mapeamento repetitivo."""
from pathlib import Path
from datetime import date
from PySide6.QtWidgets import QFileDialog,QDialog,QVBoxLayout,QLabel,QPushButton,QDialogButtonBox
from .widgets import Table
from .management import ui_action
from ..importers.automatic import inspect_file,commit_plans,BASIS_LABELS
from ..business.organization import compare_import



class AutomaticImportMixin:
    @ui_action
    def import_automatic_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Importar pedidos e resumo da loja (pode selecionar os dois)','','Planilhas (*.xlsx)')
        if paths:self.review_automatic([inspect_file(path) for path in paths])

    def review_automatic(self,plans):
        rows=[];warnings=[]
        for plan in plans:
            warnings.extend(plan['warnings']);period=plan['period']
            if plan['kind']=='orders':
                compared,duplicate=compare_import(self.s,plan['orders'])
                counts={key:sum(r['action']==key for r in compared) for key in ('Novo','Atualizado','Sem alteração comercial')}
                rows.append({'arquivo':plan['source_name'],'tipo':'Pedidos detalhados','abas':', '.join(plan['sheets']),'start':period['start'],'end':period['end'],'registros':len(plan['orders']),'revisão':f"{counts['Novo']} novos; {counts['Atualizado']} alterados; {counts['Sem alteração comercial']} inalterados"})
            else:
                for basis in sorted({r['basis'] for r in plan['metrics']}):
                    subset=[r for r in plan['metrics'] if r['basis']==basis];rows.append({'arquivo':plan['source_name'],'tipo':'Resumo gerencial · '+BASIS_LABELS[basis],'abas':BASIS_LABELS[basis],'start':period['start'],'end':period['end'],'registros':len(subset),'revisão':'Total do intervalo separado das linhas mensais/diárias; não gera vendas'})
            if self.s.one('SELECT id FROM import_history WHERE source_hash=?',(plan['source_hash'],)):warnings.append('Arquivo já importado: '+plan['source_name']+'. Chaves existentes serão atualizadas sem somar novamente.')
        dialog=QDialog(self);dialog.setWindowTitle('Importação automática · confira antes de gravar');dialog.resize(1150,680);layout=QVBoxLayout(dialog)
        label=QLabel('Abas, colunas e períodos reconhecidos. Pedidos entram uma vez por ID; Pedido Feito e Produto Pago são bases de comparação, nunca novas vendas ou repasses. A gravação dos arquivos selecionados é única e cria backup.');label.setWordWrap(True);layout.addWidget(label)
        table=Table();table.fill(rows);layout.addWidget(table)
        note=QLabel('\n'.join(dict.fromkeys(warnings)));note.setWordWrap(True);layout.addWidget(note)
        details=QPushButton('Ver detalhes reconhecidos');layout.addWidget(details)
        def show_details():
            d=QDialog(dialog);d.setWindowTitle('Detalhes · sem dados de compradores');d.resize(1100,650);body=QVBoxLayout(d);records=[]
            for plan in plans:
                if plan['kind']=='orders':
                    for order in plan['orders']:
                        for item in order['items']:records.append({'tipo':'Pedido','referência':order['id'],'date':order['date'],'status':order['status'],'produto':item['title'],'variação':item['variation'],'unidades':item['qty'],'unit_cents':item['unit_cents']})
                else:
                    for metric in plan['metrics']:records.append({'tipo':BASIS_LABELS[metric['basis']],'referência':metric['grain'],'date':metric['start'],'fim':metric['end'],**metric['detail']})
            columns=list(dict.fromkeys(key for record in records for key in record));t=Table();t.fill(records,[(key,key) for key in columns]);body.addWidget(t);close=QPushButton('Fechar');close.clicked.connect(d.accept);body.addWidget(close);d.exec()
        details.clicked.connect(show_details)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Confirmar importação');buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        backup=commit_plans(self.erp,plans)
        start=min(plan['period']['start'] for plan in plans);end=max(plan['period']['end'] for plan in plans)
        order_plans=[p for p in plans if p['kind']=='orders'];month=max(p['period']['active_month'] for p in order_plans) if order_plans else end[:7]
        self.dashboard_month.setText(month);self.report_start.setText(start);self.report_end.setText(end);self.report_product.setCurrentIndex(0);self.report_status.setCurrentIndex(0)
        for widget in self.report_extra.values():widget.clear()
        self.report_coverage.setCurrentIndex(0);self.nav.setCurrentRow(8);self.report_tabs.setCurrentIndex(0);self.update_report()
        self.info(f'Importação concluída com backup: {backup}\nCampos preenchidos: confira vendas, taxas, consumo e resultado nas telas existentes. Custos e consumo continuam dependendo das receitas cadastradas; não são inventados pelo resumo gerencial.')
