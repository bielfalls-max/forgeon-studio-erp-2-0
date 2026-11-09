from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QComboBox,QDialogButtonBox,
                              QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QPushButton,
                              QWidget,QHBoxLayout,QTextBrowser,QCheckBox,QSpinBox,QMessageBox,QMenu,QFileDialog,QApplication,QScrollArea)
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QColor
from ..business.numbers import money
from ..business.labels import LABELS
from datetime import datetime
from decimal import Decimal, InvalidOperation
from .visual import FlowLayout


class Form(QDialog):
    def __init__(self,title,fields,parent=None,note=''):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(540)
        layout=QVBoxLayout(self)
        if note:
            label=QLabel(note); label.setWordWrap(True); layout.addWidget(label)
        form=QFormLayout()
        if len(fields)>10:
            scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();body.setLayout(form);scroll.setWidget(body);layout.addWidget(scroll);scroll.setMinimumHeight(420)
        else:layout.addLayout(form)
        self.inputs={}
        for key,label,value in fields:
            if isinstance(value,list):
                widget=QComboBox()
                for text,data in value:
                    widget.addItem(text,data)
            else:
                widget=QLineEdit(str(value))
            form.addRow(label,widget)
            self.inputs[key]=widget
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {k:(w.currentData() if isinstance(w,QComboBox) else w.text().strip()) for k,w in self.inputs.items()}


class SortItem(QTableWidgetItem):
    def __lt__(self,other):
        a=self.data(Qt.ItemDataRole.UserRole+1);b=other.data(Qt.ItemDataRole.UserRole+1)
        return a<b if a is not None and b is not None else self.text().casefold()<other.text().casefold()


class Table(QTableWidget):
    def __init__(self):
        super().__init__()
        self.records=[]
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setWordWrap(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.columns_menu)
        self.horizontalHeader().setToolTip('Clique para ordenar, arraste para reorganizar, botão direito para escolher colunas.')
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self._columns=[];self.persistence=None;self._loading=False
        self._save_timer=QTimer(self);self._save_timer.setSingleShot(True);self._save_timer.timeout.connect(self.save_layout)
        self.horizontalHeader().sectionMoved.connect(self.schedule_layout)
        self.horizontalHeader().sectionResized.connect(self.schedule_layout)

    def fill(self,rows,columns=None,conflict=None):
        self._loading=True
        hidden={key for index,(key,_) in enumerate(self._columns) if self.isColumnHidden(index)}
        self.records=rows
        columns=columns or [(k,LABELS.get(k,k)) for k in (rows[0] if rows else {'info':'Sem registros'})]
        self.setSortingEnabled(False)
        self.clear(); self.setRowCount(len(rows)); self.setColumnCount(len(columns))
        self._columns=columns
        self.setHorizontalHeaderLabels([label for key,label in columns])
        for index,(key,_) in enumerate(columns):self.setColumnHidden(index,key in hidden)
        for rn,row in enumerate(rows):
            for cn,(key,label) in enumerate(columns):
                value=row.get(key,'')
                if key.endswith('_cents') and value is not None:
                    value=money(value)
                if value is None:
                    value='Pendente'
                if value is not None and key in ('weight','grams','unit_grams','hours','unit_hours'):
                    try:value=f'{Decimal(str(value)):,.3f}'.replace(',','X').replace('.',',').replace('X','.')
                    except InvalidOperation:pass
                if key in ('date','start','end','cost_at','snapshot_at','recorded','created','due','added') and isinstance(value,str):
                    try: value=datetime.strptime(value[:10],'%Y-%m-%d').strftime('%d/%m/%Y')+value[10:]
                    except ValueError: pass
                item=SortItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole,rn)
                raw=row.get(key)
                try:
                    number=Decimal(str(raw)); sort=(0,number) if number.is_finite() else (1,str(raw))
                except (InvalidOperation,ValueError):sort=(1,str(raw or '').casefold())
                item.setData(Qt.ItemDataRole.UserRole+1,sort)
                if conflict and conflict(row):
                    item.setBackground(QColor('#6e242a')); item.setForeground(QColor('#fff0ec'))
                self.setItem(rn,cn,item)
        self.setSortingEnabled(True)
        self.resizeColumnsToContents()
        for col in range(self.columnCount()):
            self.setColumnWidth(col,min(360,max(100,self.columnWidth(col))))
        self.restore_layout();self._loading=False

    def set_hidden(self,index,hidden):
        self.setColumnHidden(index,hidden);self.schedule_layout()

    def schedule_layout(self,*args):
        if not self._loading and self.persistence:self._save_timer.start(350)

    def save_layout(self):
        if not self.persistence or not self._columns:return
        from ..business.organization import set_preference
        store,key=self.persistence;header=self.horizontalHeader()
        set_preference(store,'table:'+key,{'order':[self._columns[header.logicalIndex(v)][0] for v in range(self.columnCount())],
            'hidden':[key for i,(key,_) in enumerate(self._columns) if self.isColumnHidden(i)],'widths':{key:self.columnWidth(i) for i,(key,_) in enumerate(self._columns)}})

    def restore_layout(self):
        if not self.persistence:return
        from ..business.organization import preference
        store,key=self.persistence;config=preference(store,'table:'+key,{})
        keys=[key for key,_ in self._columns];header=self.horizontalHeader()
        for visual,key in enumerate([k for k in config.get('order',[]) if k in keys]):header.moveSection(header.visualIndex(keys.index(key)),visual)
        for i,(key,_) in enumerate(self._columns):
            self.setColumnHidden(i,key in config.get('hidden',[]))
            if key in config.get('widths',{}):self.setColumnWidth(i,max(60,min(1200,int(config['widths'][key]))))

    def selected(self):
        row=self.currentRow()
        if row<0:
            raise ValueError('Selecione uma linha primeiro.')
        return self.records[self.item(row,0).data(Qt.ItemDataRole.UserRole)]

    def columns_menu(self,point):
        menu=QMenu(self)
        for index,(key,label) in enumerate(self._columns):
            action=menu.addAction(label);action.setCheckable(True);action.setChecked(not self.isColumnHidden(index))
            action.toggled.connect(lambda checked,i=index:self.set_hidden(i,not checked))
        menu.exec(self.horizontalHeader().mapToGlobal(point))

    def visible_columns(self):
        header=self.horizontalHeader()
        return [header.logicalIndex(visual) for visual in range(self.columnCount()) if not self.isColumnHidden(header.logicalIndex(visual))]

    def context_menu(self,point):
        menu=QMenu(self);menu.addAction('Copiar linha como texto para planilha',self.copy_row);menu.addAction('Mostrar todas as colunas',self.show_all_columns);menu.addAction('Exportar colunas visíveis em XLSX',self.export_visible)
        menu.exec(self.viewport().mapToGlobal(point))

    def copy_row(self):
        if self.currentRow()<0:return
        values=[self.item(self.currentRow(),col).text().replace('\t',' ').replace('\r',' ').replace('\n',' ') for col in self.visible_columns()]
        QApplication.clipboard().setText('\t'.join("'"+value for value in values))

    def show_all_columns(self):
        for column in range(self.columnCount()):self.setColumnHidden(column,False)
        self.schedule_layout()

    def visible_records(self):
        result=[]
        for row in range(self.rowCount()):
            source=self.records[self.item(row,0).data(Qt.ItemDataRole.UserRole)]
            result.append({self._columns[col][0]:source.get(self._columns[col][0]) for col in self.visible_columns()})
        return result

    def export_visible(self):
        if not self.visible_columns():
            QMessageBox.information(self,'Colunas','Mostre ao menos uma coluna no menu do cabeçalho.');return
        path,_=QFileDialog.getSaveFileName(self,'Exportar tabela visível','tabela-forgeon.xlsx','Planilha (*.xlsx)')
        if path:
            try:
                from ..reports.xlsx import export
                export(path,{'Tabela':self.visible_records()})
            except Exception as error:QMessageBox.warning(self,'Exportar',str(error))


class Page(QWidget):
    def __init__(self,title,subtitle=''):
        super().__init__()
        self.layout=QVBoxLayout(self); self.layout.setContentsMargins(26,24,26,22); self.layout.setSpacing(14)
        self.page_title=title
        top=QHBoxLayout();heading=QLabel(title);heading.setObjectName('pageTitle');top.addWidget(heading,1)
        self.help_button=QPushButton('ⓘ Como usar');self.help_button.setObjectName('helpButton');self.help_button.setToolTip('Ajuda desta aba · F1');self.help_button.clicked.connect(self.show_usage);top.addWidget(self.help_button);self.layout.addLayout(top)
        if subtitle:
            sub=QLabel(subtitle); sub.setWordWrap(True); sub.setObjectName('subtitle'); self.layout.addWidget(sub)
        self.toolbar=FlowLayout(); self.layout.addLayout(self.toolbar)

    def show_usage(self):
        from .help import show_help
        show_help(self,self.page_title)

    def button(self,text,callback,primary=False):
        b=QPushButton(text)
        if primary: b.setObjectName('primary')
        def invoke():
            try: callback()
            except Exception as error: QMessageBox.warning(self,'FORGEON • Verifique os dados',str(error))
        b.clicked.connect(invoke); self.toolbar.addWidget(b); return b

    def table(self):
        t=Table(); self.layout.addWidget(t); return t


def preview(parent,title,rows,note=''):
    d=QDialog(parent); d.setWindowTitle(title); d.resize(1080,640)
    layout=QVBoxLayout(d)
    label=QLabel(note); label.setWordWrap(True); layout.addWidget(label)
    label2=QLabel(f'{len(rows)} registros. Revise antes de confirmar. A confirmação grava no banco e cria um backup.'); layout.addWidget(label2)
    table=Table(); table.fill(rows); layout.addWidget(table)
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Confirmar importação')
    buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); layout.addWidget(buttons)
    return d.exec()==QDialog.DialogCode.Accepted


STYLE='''
QWidget { background: transparent; color: #e5edf6; font-family: "Segoe UI", sans-serif; font-size: 13px; }
QMainWindow { background: #0a1221; }
QDialog, QMessageBox, QMenu { background: #142239; }
QLabel#brand { font-size: 23px; font-weight: 800; color: #fff3e5; letter-spacing: 3px; }
QLabel#pageTitle { font-size: 27px; font-weight: 700; color: #f5f4f1; }
QLabel#subtitle, QLabel#muted { color: #a9bad0; font-size: 12px; }
QLabel#sectionTitle { font-size: 16px; font-weight: 650; color: #f0eee8; }
QLabel#metricTitle { color: #9eb3cc; font-size: 11px; letter-spacing: 1px; font-weight: 650; }
QLabel#metricValue { color: #f7f0e7; font-size: 29px; font-weight: 650; }
QLabel#badge { color: #f6c39f; background: rgba(171,105,62,36); border: 1px solid rgba(245,173,120,60); border-radius: 9px; padding: 8px 12px; font-size: 11px; }
QListWidget { background: transparent; border: none; padding: 0px; font-size: 13px; outline: none; }
QListWidget::item { padding: 11px 12px; border-radius: 10px; margin: 3px 0px; color: #b7c7db; }
QListWidget::item:selected { background: rgba(216,139,85,32); color: #ffcfaa; border: 1px solid rgba(248,179,127,65); }
QListWidget::item:hover { background: rgba(170,198,231,15); }
QPushButton { background: rgba(30,49,73,225); border: 1px solid rgba(189,214,244,40); padding: 9px 14px; border-radius: 9px; color: #e3edf8; }
QPushButton:hover { background: #304967; border-color: #a47959; }
QPushButton:disabled { color: #70849b; background: #17263a; }
QPushButton#primary { background: #c48255; border-color: #dea57c; color: #111c2b; font-weight: 700; }
QPushButton#primary:hover { background: #e4a574; }
QLineEdit, QComboBox, QSpinBox, QDateEdit { background: rgba(13,29,47,235); color: #eff4fb; padding: 8px 10px; border: 1px solid #3a526d; border-radius: 8px; selection-background-color: #8c654e; }
QComboBox QAbstractItemView { background: #1c3049; selection-background-color: #5c493d; }
QTableWidget { background: rgba(14,28,46,232); alternate-background-color: rgba(25,43,63,235); border: 1px solid rgba(191,215,243,42); border-radius: 12px; gridline-color: #2c3e54; selection-background-color: #5c493d; }
QTableWidget::item { padding: 9px; border: none; }
QTableWidget::item:selected { background: #624c3e; color: #ffffff; }
QHeaderView { background: transparent; }
QHeaderView::section { background: #22384f; color: #c5d6e9; padding: 11px; border: none; border-right: 1px solid #364b62; font-weight: 600; }
QTextBrowser { background: rgba(14,28,46,230); border: 1px solid rgba(191,215,243,38); border-radius: 14px; padding: 16px; }
QCheckBox { padding: 4px; color: #acbed2; }
QStatusBar { color: #9fb0c7; background: #0b1524; font-size: 11px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: rgba(12,25,42,90); width: 9px; margin: 0px; }
QScrollBar::handle:vertical { background: #506782; border-radius: 4px; min-height: 25px; }
QScrollBar:horizontal { background: #122338; height: 9px; }
QScrollBar::handle:horizontal { background: #506782; border-radius: 4px; min-width: 25px; }
QTabWidget::pane { border: none; padding-top: 10px; }
QTabBar::tab { padding: 10px 16px; margin: 0px 4px 0px 0px; border-radius: 8px; background: rgba(23,42,63,230); color: #a8bad0; }
QTabBar::tab:selected { color: #ffd1ae; background: #4a3c34; }
QProgressBar { border: 1px solid #3c526b; border-radius: 6px; background: #142338; text-align: center; min-height: 17px; }
QProgressBar::chunk { background: #b77c52; border-radius: 5px; }
QPushButton#helpButton { padding: 7px 10px; font-size: 11px; border-radius: 8px; background: rgba(22,42,62,170); }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #4a3c34; }
QToolTip { background: #203650; color: #f2e9df; border: 1px solid #64768d; padding: 8px; }
'''
