"""Menu por tarefa, preservando rotas internas e atalhos dos cadastros."""
from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QListWidget,QListWidgetItem,QTabBar

GROUPS=[('Início',[0,11]),('Produtos',[1,4]),('Precificação',[3,14]),('Materiais',[2,13]),('Vendas',[5,6]),('Produção',[12]),('Financeiro',[7,15,8]),('Ajustes',[9,10])]
SUBTITLES={0:'Painel',11:'Pendências',1:'Cadastro',4:'Anúncios e SKUs',3:'Custo e preço',14:'Simular cenário',2:'Cores e preços/kg',13:'Estoque',5:'Pedidos',6:'Importar',12:'Lotes e perdas',7:'Lançamentos',15:'Repasses',8:'Relatórios',9:'Preferências e backup',10:'Atualizações'}

class WorkspaceNavigation(QWidget):
    currentRowChanged=Signal(int)
    def __init__(self):
        super().__init__();layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.groups=QListWidget();layout.addWidget(self.groups);self.tabs=QTabBar();self.tabs.setExpanding(False);self.tabs.setDrawBase(False)
        self.routes=[];self._current=-1;self._busy=False;self._last={}
        for title,routes in GROUPS:self.groups.addItem(title)
        self.groups.currentRowChanged.connect(self._group_changed);self.tabs.currentChanged.connect(self._tab_changed)

    def addItem(self,title):self.routes.append(QListWidgetItem(title))
    def item(self,index):return self.routes[index]
    def count(self):return len(self.routes)
    def currentRow(self):return self._current
    def setHorizontalScrollBarPolicy(self,policy):self.groups.setHorizontalScrollBarPolicy(policy)
    def _group_changed(self,index):
        if not self._busy and index>=0:self.setCurrentRow(self._last.get(index,GROUPS[index][1][0]))
    def _tab_changed(self,index):
        if not self._busy and index>=0:self.setCurrentRow(GROUPS[self.groups.currentRow()][1][index])
    def setCurrentRow(self,route):
        if not 0<=route<len(self.routes):return
        group=next(i for i,(_,routes) in enumerate(GROUPS) if route in routes)
        changed=self._current!=route;self._current=route;self._last[group]=route;self._busy=True
        self.groups.setCurrentRow(group)
        while self.tabs.count():self.tabs.removeTab(0)
        for item in GROUPS[group][1]:self.tabs.addTab(SUBTITLES[item]);self.tabs.setTabToolTip(self.tabs.count()-1,self.routes[item].text())
        self.tabs.setCurrentIndex(GROUPS[group][1].index(route));self.tabs.setVisible(len(GROUPS[group][1])>1);self._busy=False
        if changed:self.currentRowChanged.emit(route)
    def set_compact(self,compact):
        short=['Início','Produtos','Preços','Materiais','Vendas','Produção','Finanças','Ajustes']
        for i,(title,_) in enumerate(GROUPS):self.groups.item(i).setText(short[i] if compact else title);self.groups.item(i).setToolTip(title)
