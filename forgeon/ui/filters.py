"""Filtros explícitos: datas opcionais e sem exclusão silenciosa do histórico."""
from datetime import date
from calendar import monthrange
from PySide6.QtWidgets import QWidget,QLabel,QLineEdit,QComboBox,QPushButton
from PySide6.QtCore import Signal
from .visual import FlowLayout
from ..business.numbers import day

class Filters(QWidget):
    changed=Signal()
    def __init__(self,erp,*,dates=False,product=False,order=False,material=False,color=False,date_label='Data'):
        super().__init__();self.erp=erp;self.fields={};layout=FlowLayout();self.setLayout(layout);self._busy=False
        if dates:
            layout.addWidget(QLabel(date_label));self.start=QLineEdit();self.end=QLineEdit()
            for name,widget in [('start',self.start),('end',self.end)]:
                widget.setPlaceholderText('De' if name=='start' else 'Até');widget.setToolTip('DD/MM/AAAA ou AAAA-MM-DD. Vazio: sem limite.');widget.setMaximumWidth(125);self.fields[name]=widget;layout.addWidget(widget)
            self.period=QComboBox()
            for label,key in [('Todo o histórico','all'),('Mês atual','month'),('Mês anterior','previous'),('1ª quinzena','first'),('2ª quinzena','second'),('Personalizado','custom')]:self.period.addItem(label,key)
            layout.addWidget(self.period);self.period.currentIndexChanged.connect(self.set_period)
            self.start.textEdited.connect(self.custom);self.end.textEdited.connect(self.custom)
        if product:
            self.product=QComboBox();self.product.setMinimumWidth(180);self.product.setMaximumWidth(260);self.fields['product']=self.product;layout.addWidget(self.product);self.refresh_products()
        for enabled,key,label in [(order,'order','Pedido / ID'),(material,'material','Material (PLA, PETG…)'),(color,'color','Cor')]:
            if enabled:
                widget=QLineEdit();widget.setPlaceholderText(label);widget.setMaximumWidth(170);self.fields[key]=widget;layout.addWidget(widget)
                widget.returnPressed.connect(self.changed.emit)
        button=QPushButton('Aplicar filtros');button.clicked.connect(self.changed.emit);layout.addWidget(button)
        button=QPushButton('Limpar');button.clicked.connect(self.clear);layout.addWidget(button)
    def custom(self,*args):self.period.blockSignals(True);self.period.setCurrentIndex(self.period.findData('custom'));self.period.blockSignals(False)
    def set_period(self,*args):
        kind=self.period.currentData();today=date.today();year,month=today.year,today.month
        if kind=='custom':return
        if kind=='previous':month-=1
        if month==0:year-=1;month=12
        start=16 if kind=='second' else 1;end=15 if kind=='first' else monthrange(year,month)[1]
        self.start.setText('' if kind=='all' else f'{year:04}-{month:02}-{start:02}');self.end.setText('' if kind=='all' else f'{year:04}-{month:02}-{end:02}');self.changed.emit()
    def refresh_products(self):
        if not hasattr(self,'product'):return
        current=self.product.currentData();self.product.blockSignals(True);self.product.clear();self.product.addItem('Todos os produtos',None)
        for row in self.erp.s.rows('SELECT id,name,model FROM products ORDER BY name,model'):self.product.addItem(row['name']+' / '+row['model'],row['id'])
        self.product.setCurrentIndex(max(0,self.product.findData(current)));self.product.blockSignals(False)
    def values(self):
        result={key:(widget.currentData() if isinstance(widget,QComboBox) else widget.text().strip()) for key,widget in self.fields.items()}
        for key in ('start','end'):
            if result.get(key):result[key]=day(result[key])
        if result.get('start') and result.get('end') and result['end']<result['start']:raise ValueError('Data final deve ser igual ou posterior à inicial.')
        return result
    def clear(self):
        for widget in self.fields.values():
            if isinstance(widget,QComboBox):widget.setCurrentIndex(0)
            else:widget.clear()
        if hasattr(self,'period'):self.period.blockSignals(True);self.period.setCurrentIndex(0);self.period.blockSignals(False)
        self.changed.emit()
