from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QCheckBox,QDialogButtonBox,QMessageBox
from ..business.recipes import paste_colors


class PasteColorsDialog(QDialog):
    def __init__(self,erp,payload,target,parent=None):
        super().__init__(parent);self.erp=erp;self.payload=payload;self.target=target
        self.setWindowTitle('Colar e adaptar cores por unidade');self.resize(850,510)
        layout=QVBoxLayout(self);product=erp.product(target)
        for text in (f"Copiado de: {payload['name']} / {payload['model']}",f"Aplicar em: {product['name']} / {product['model']}",
                     'Edite as cores e gramas abaixo. Ao salvar, esta lista substitui as cores do destino. Zero remove uma linha. O nome, tamanho, embalagem e outros custos do destino são mantidos.'):
            label=QLabel(text);label.setTextFormat(Qt.TextFormat.PlainText);label.setWordWrap(True);layout.addWidget(label)
        self.colors=QTableWidget(len(payload['colors']),4);self.colors.verticalHeader().hide()
        self.colors.setHorizontalHeaderLabels(['Material','Cor · editar para a variação','Gramas / unidade','R$/kg · se for nova cor'])
        self.colors.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(self.colors,1)
        for row,c in enumerate(payload['colors']):
            for col,key in enumerate(('material','color','grams','kg')):self.colors.setItem(row,col,QTableWidgetItem(str(c[key])))
        self.copy_hours=QCheckBox(f"Copiar também o tempo de impressão ({Decimal(payload['hours']):.3f} h/un.)");layout.addWidget(self.copy_hours)
        label=QLabel('Cores já cadastradas usam o preço atual em Materiais. Novas cores usam o R$/kg informado acima. Pedidos com custos congelados mantêm seus valores.');label.setWordWrap(True);layout.addWidget(label)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Aplicar ao produto selecionado');buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def save(self):
        try:
            colors=[{key:self.colors.item(row,col).text() for col,key in enumerate(('material','color','grams','kg'))} for row in range(self.colors.rowCount())]
            paste_colors(self.erp,self.target,self.payload,colors,self.copy_hours.isChecked());self.accept()
        except Exception as error:QMessageBox.warning(self,'Verifique as cores',str(error))
