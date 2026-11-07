from decimal import Decimal
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QSpinBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QDialogButtonBox,QComboBox,QCheckBox,QMessageBox)
from ..importers.slicing import read_slicing,combine_plates,suggested_name
from ..business.numbers import money,decimal
from ..business.production import save_sliced_product
from .visual import GlassCard


def hours_text(value):
    if value is None:return 'Não informado'
    seconds=int((Decimal(str(value))*3600).quantize(Decimal('1')))
    return f'{seconds//3600}h {(seconds%3600)//60:02}min {seconds%60:02}s'


def number_text(value,places=2):
    if value is None:return 'Pendente'
    return f'{Decimal(str(value)):,.{places}f}'.replace(',','X').replace('.',',').replace('X','.')


class SlicingProductDialog(QDialog):
    def __init__(self,erp,path,parent=None,pid=None):
        super().__init__(parent);self.erp=erp;self.path=Path(path);self.plates=read_slicing(path);self.recipe=None;self.result_data=None
        self.setWindowTitle('Cadastrar produto pelo fatiador');self.resize(1030,790);self.setMinimumSize(850,650)
        layout=QVBoxLayout(self);layout.setSpacing(12)
        title=QLabel('Um produto completo, todas as suas cores');title.setObjectName('pageTitle');layout.addWidget(title)
        note=QLabel('Selecione as placas que formam o mesmo produto e informe quantos produtos completos elas rendem. Peças, mãos e acessórios não são unidades vendidas.');note.setWordWrap(True);layout.addWidget(note)
        fields=QGridLayout();layout.addLayout(fields)
        self.target=QComboBox();self.target.addItem('Criar novo produto físico',None)
        for p in erp.s.rows('SELECT id,name,model FROM products ORDER BY name'):self.target.addItem(p['name']+' / '+p['model'],p['id'])
        self.name=QLineEdit(suggested_name(path));self.model=QLineEdit();self.units=QSpinBox();self.units.setRange(1,1000000);self.units.setValue(1)
        self.packaging=QLineEdit('0');self.other=QLineEdit('0')
        for row,(label,widget) in enumerate([('Cadastro',self.target),('Nome físico do produto',self.name),('Modelo / tamanho (opcional)',self.model)]):fields.addWidget(QLabel(label),row,0);fields.addWidget(widget,row,1)
        for row,(label,widget) in enumerate([('Produtos COMPLETOS nas placas selecionadas',self.units),('Embalagem R$/unidade',self.packaging),('Outros custos R$/unidade',self.other)]):fields.addWidget(QLabel(label),row,2);fields.addWidget(widget,row,3)
        self.plate_table=QTableWidget(len(self.plates),6);self.plate_table.setHorizontalHeaderLabels(['Usar','Placa','Tempo da placa','Filamento g','Cores do arquivo','Peças (não unidades)']);self.plate_table.verticalHeader().hide();self.plate_table.setMaximumHeight(205)
        for row,plate in enumerate(self.plates):
            check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);check.setCheckState(Qt.CheckState.Checked);self.plate_table.setItem(row,0,check)
            values=[plate['name'],hours_text(plate['hours']),number_text(sum((Decimal(c['grams']) for c in plate['colors']),Decimal(0))),'; '.join(c['label'] for c in plate['colors']),str(plate.get('object_count') or '—')]
            for col,value in enumerate(values,1):item=QTableWidgetItem(value);item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);self.plate_table.setItem(row,col,item)
        self.plate_table.resizeColumnsToContents()
        for col,width in enumerate((48,160,150,110,270,180)):self.plate_table.setColumnWidth(col,width)
        self.plate_table.horizontalHeader().setStretchLastSection(True);layout.addWidget(self.plate_table)
        self.summary=QLabel();self.summary.setObjectName('badge');self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.colors=QTableWidget(0,4);self.colors.setHorizontalHeaderLabels(['Material (editar)','Cor (editar se necessário)','Gramas por unidade','Referência R$/kg (editar)']);self.colors.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.colors.verticalHeader().hide();layout.addWidget(self.colors,1)
        note=QLabel('O preço por kg vem do seu cadastro ou padrão local, não da moeda do arquivo. Confirme os valores. Consumo inclui os suportes/expurgo informados pelo fatiador; não é pesagem real. Custos de pedidos já congelados serão preservados.');note.setWordWrap(True);note.setObjectName('muted');layout.addWidget(note)
        self.confirm=QCheckBox('Confirmo que as placas selecionadas compõem este produto e a quantidade de produtos completos está correta.');layout.addWidget(self.confirm)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.button(QDialogButtonBox.StandardButton.Save).setText('Salvar produto, cores e precificação');buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.plate_table.itemChanged.connect(self.recalculate);self.units.valueChanged.connect(self.recalculate);self.target.currentIndexChanged.connect(self.target_changed)
        if pid:self.target.setCurrentIndex(max(0,self.target.findData(pid)))
        self.recalculate()

    def target_changed(self):
        pid=self.target.currentData()
        if pid:
            p=self.erp.product(pid);self.name.setText(p['name']);self.model.setText(p['model']);self.packaging.setText(str(Decimal(p['packaging_cents'])/100));self.other.setText(str(Decimal(p['other_cents'])/100))

    def recalculate(self,*args):
        selected=[row for row in range(self.plate_table.rowCount()) if self.plate_table.item(row,0).checkState()==Qt.CheckState.Checked]
        if not selected:self.recipe=None;self.summary.setText('Selecione as placas do produto.');self.colors.setRowCount(0);return
        old={self.colors.item(row,1).text():[self.colors.item(row,col).text() for col in (0,1,3)] for row in range(self.colors.rowCount())}
        self.recipe=combine_plates(self.plates,selected,self.units.value(),self.path.name)
        grams=sum((Decimal(c['grams']) for c in self.recipe['colors']),Decimal(0))
        self.summary.setText(f'{len(selected)} placas · {self.units.value()} produtos completos · POR UNIDADE: {number_text(grams)} g · {hours_text(self.recipe["hours"])}')
        self.colors.setRowCount(len(self.recipe['colors']))
        for row,c in enumerate(self.recipe['colors']):
            existing=self.erp.s.one('SELECT * FROM filaments WHERE material=? AND color=?',(c['material'],c['color']))
            kg=str(Decimal(existing['kg_cents'])/100) if existing else self.erp.s.settings()['filament_kg']
            material,label,kg=old.get(c['color'],[c['material'],c['color'],kg])
            for col,value in enumerate([material,label,number_text(c['grams'],3),kg]):
                item=QTableWidgetItem(value)
                if col==2:item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
                self.colors.setItem(row,col,item)

    def save(self):
        try:
            if not self.confirm.isChecked():raise ValueError('Confirme que as placas e a quantidade correspondem ao produto completo.')
            if self.recipe is None:raise ValueError('Selecione as placas.')
            colors=[{**c,'material':self.colors.item(row,0).text().strip(),'color':self.colors.item(row,1).text().strip(),'kg':self.colors.item(row,3).text().strip()} for row,c in enumerate(self.recipe['colors'])]
            pid=self.target.currentData()
            if pid and QMessageBox.question(self,'Atualizar receita?','Substituir peso, tempo e cores deste produto? Custos históricos e SKUs serão preservados.')!=QMessageBox.StandardButton.Yes:return
            self.result_data=save_sliced_product(self.erp,self.name.text(),self.model.text(),self.recipe,colors,self.packaging.text(),self.other.text(),pid)
            self.accept()
        except Exception as error:QMessageBox.warning(self,'Verifique o cadastro',str(error))
