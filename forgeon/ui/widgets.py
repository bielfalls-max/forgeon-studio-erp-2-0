from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QComboBox,QDialogButtonBox,
                              QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QPushButton,
                              QWidget,QHBoxLayout,QTextBrowser,QCheckBox,QSpinBox,QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..business.numbers import money
from ..business.labels import LABELS
from datetime import datetime


class Form(QDialog):
    def __init__(self,title,fields,parent=None,note=''):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(540)
        layout=QVBoxLayout(self)
        if note:
            label=QLabel(note); label.setWordWrap(True); layout.addWidget(label)
        form=QFormLayout(); layout.addLayout(form)
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

    def fill(self,rows,columns=None,conflict=None):
        self.records=rows
        columns=columns or [(k,LABELS.get(k,k)) for k in (rows[0] if rows else {'info':'Sem registros'})]
        self.setSortingEnabled(False)
        self.clear(); self.setRowCount(len(rows)); self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([label for key,label in columns])
        for rn,row in enumerate(rows):
            for cn,(key,label) in enumerate(columns):
                value=row.get(key,'')
                if key.endswith('_cents') and value is not None:
                    value=money(value)
                if value is None:
                    value='Pendente'
                if key in ('date','start','end') and isinstance(value,str):
                    try: value=datetime.strptime(value[:10],'%Y-%m-%d').strftime('%d/%m/%Y')+value[10:]
                    except ValueError: pass
                item=QTableWidgetItem(str(value))
                if conflict and conflict(row):
                    item.setBackground(QColor('#6e242a')); item.setForeground(QColor('#fff0ec'))
                self.setItem(rn,cn,item)
        self.resizeColumnsToContents()
        for col in range(self.columnCount()):
            self.setColumnWidth(col,min(360,max(100,self.columnWidth(col))))

    def selected(self):
        row=self.currentRow()
        if row<0:
            raise ValueError('Selecione uma linha primeiro.')
        return self.records[row]


class Page(QWidget):
    def __init__(self,title,subtitle=''):
        super().__init__()
        self.layout=QVBoxLayout(self); self.layout.setContentsMargins(28,24,28,24); self.layout.setSpacing(16)
        heading=QLabel(title); heading.setObjectName('pageTitle'); self.layout.addWidget(heading)
        if subtitle:
            sub=QLabel(subtitle); sub.setWordWrap(True); sub.setObjectName('subtitle'); self.layout.addWidget(sub)
        self.toolbar=QHBoxLayout(); self.layout.addLayout(self.toolbar)

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
QWidget { background: #15181e; color: #ede9e1; font-family: "Segoe UI", sans-serif; font-size: 13px; }
QMainWindow, QStackedWidget { background: #15181e; }
QLabel#brand { font-size: 26px; font-weight: 800; color: #ff9c48; letter-spacing: 2px; }
QLabel#pageTitle { font-size: 27px; font-weight: 700; }
QLabel#subtitle { color: #adafb7; }
QListWidget { background: #101217; border: none; padding: 10px; font-size: 14px; outline: none; }
QListWidget::item { padding: 12px 10px; border-radius: 6px; margin: 2px; }
QListWidget::item:selected { background: #592c27; color: #ffba72; border-left: 3px solid #ed743b; }
QPushButton { background: #292d36; border: 1px solid #404550; padding: 9px 14px; border-radius: 5px; }
QPushButton:hover { background: #3a3d46; border-color: #d29358; }
QPushButton#primary { background: #b74629; border-color: #d36036; color: white; font-weight: 600; }
QLineEdit, QComboBox, QSpinBox, QDateEdit { background: #20242c; padding: 8px; border: 1px solid #414650; border-radius: 4px; selection-background-color: #a64229; }
QTableWidget { background: #1a1e25; alternate-background-color: #20242c; border: 1px solid #343941; gridline-color: #30353d; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { background: #5b3b2e; }
QHeaderView::section { background: #292d35; color: #deb477; padding: 11px; border: none; border-bottom: 1px solid #51504a; font-weight: 600; }
QTextBrowser { background: #1c2027; border: 1px solid #353a43; padding: 16px; }
QCheckBox { padding: 4px; }
QStatusBar { color: #aaa59d; background: #101217; }
QScrollBar:vertical { background: #1b1e25; width: 12px; }
QScrollBar::handle:vertical { background: #505059; border-radius: 5px; min-height: 20px; }
QTabBar::tab { padding: 10px; background: #292d35; }
QTabBar::tab:selected { color: #ffad63; }
'''
