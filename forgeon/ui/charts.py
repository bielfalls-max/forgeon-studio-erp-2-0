from PySide6.QtCharts import (QChart,QChartView,QLineSeries,QBarSet,QBarSeries,QHorizontalBarSeries,
                             QBarCategoryAxis,QValueAxis,QPieSeries,QDateTimeAxis)
from PySide6.QtCore import Qt,QDateTime,QLocale
from PySide6.QtGui import QPainter,QColor,QPen,QCursor,QFont
from PySide6.QtWidgets import QLabel,QToolTip,QFileDialog,QMessageBox,QMenu
from .visual import GlassCard
from ..business.numbers import money

PALETTE=['#f5ad78','#7dd5c0','#86acec','#dba2d3','#e5ca7b','#a6c4d2']


class ChartCard(GlassCard):
    def __init__(self,title,subtitle=''):
        super().__init__()
        label=QLabel(title);label.setObjectName('sectionTitle');self.body.addWidget(label)
        self.caption=QLabel(subtitle);self.caption.setObjectName('muted');self.caption.setWordWrap(True);self.body.addWidget(self.caption)
        self.setMinimumHeight(280)
        self.chart=QChart();self.chart.setLocale(QLocale('pt_BR'));self.chart.setLocalizeNumbers(True);self.chart.setBackgroundVisible(False);self.chart.setPlotAreaBackgroundVisible(False)
        self.chart.legend().setVisible(False);self.chart.setMargins(__import__('PySide6.QtCore',fromlist=['QMargins']).QMargins(0,4,5,0))
        self.view=QChartView(self.chart);self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setBackgroundBrush(Qt.BrushStyle.NoBrush);self.view.viewport().setAutoFillBackground(False)
        self.view.setStyleSheet('background: transparent; border: none;');self.view.setMinimumHeight(190)
        self.body.addWidget(self.view,1)
        self.empty=QLabel('Sem dados neste período. Cadastre ou importe pedidos para visualizar.');self.empty.setObjectName('muted');self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter);self.body.addWidget(self.empty,1);self.empty.hide()
        self.view.setToolTip('Passe o mouse para ver valores. Botão direito para salvar o gráfico em PNG.')
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.view.customContextMenuRequested.connect(self.menu)

    def reset(self,has_data):
        self.chart.removeAllSeries()
        for axis in self.chart.axes():self.chart.removeAxis(axis)
        self.chart.legend().setVisible(False)
        self.view.setVisible(has_data);self.empty.setVisible(not has_data)

    def axes_style(self):
        for axis in self.chart.axes():
            axis.setTitleBrush(QColor('#aab9cd'))
            axis.setLabelsColor(QColor('#aab9cd'));axis.setLinePenColor(QColor('#435068'))
            axis.setGridLineColor(QColor(180,200,230,21));axis.setLabelsFont(QFont('Segoe UI',9))

    def line(self,rows,key='gross_cents'):
        self.reset(bool(rows))
        if not rows:return
        series=QLineSeries();series.setPen(QPen(QColor(PALETTE[0]),2.8));series.setPointsVisible(True)
        moments=[QDateTime.fromString(row['date'],'yyyy-MM-dd') for row in rows]
        for moment,row in zip(moments,rows):series.append(moment.toMSecsSinceEpoch(),row[key]/100)
        self.chart.addSeries(series)
        x=QDateTimeAxis();x.setFormat('dd/MM');x.setTickCount(min(6,max(2,len(rows))));x.setRange(moments[0].addDays(-1) if len(rows)==1 else moments[0],moments[-1].addDays(1) if len(rows)==1 else moments[-1])
        y=QValueAxis();maximum=max(r[key]/100 for r in rows);y.setRange(0,max(1,maximum*1.2));y.setLabelFormat('R$ %.0f');y.applyNiceNumbers()
        self.chart.addAxis(x,Qt.AlignmentFlag.AlignBottom);self.chart.addAxis(y,Qt.AlignmentFlag.AlignLeft);series.attachAxis(x);series.attachAxis(y)
        def hover(point,state):
            if state:
                r=rows[min(range(len(rows)),key=lambda index:abs(moments[index].toMSecsSinceEpoch()-point.x()))];QToolTip.showText(QCursor.pos(),f"{r['date'][8:10]}/{r['date'][5:7]} • {money(r[key])}")
        series.hovered.connect(hover);self.axes_style()

    def bars(self,rows,label,value,unit='un.'):
        rows=rows[:6];self.reset(bool(rows))
        if not rows:return
        series=QHorizontalBarSeries();bar=QBarSet('Quantidade');bar.setColor(QColor(PALETTE[1]));bar.setBorderColor(QColor(PALETTE[1]))
        for row in rows:bar.append(float(row[value]))
        series.append(bar);self.chart.addSeries(series)
        y=QBarCategoryAxis();y.append([str(r[label])[:28] for r in rows]);y.setReverse(True);x=QValueAxis();x.setRange(0,max(1,max(float(r[value]) for r in rows)*1.2));x.setLabelFormat('%.0f');x.setTitleText(unit);x.applyNiceNumbers()
        self.chart.addAxis(y,Qt.AlignmentFlag.AlignLeft);self.chart.addAxis(x,Qt.AlignmentFlag.AlignBottom);series.attachAxis(y);series.attachAxis(x)
        bar.hovered.connect(lambda state,index:QToolTip.showText(QCursor.pos(),f"{rows[index][label]}: {rows[index][value]} {unit}") if state else None)
        self.axes_style()

    def donut(self,values):
        values=[(name,value) for name,value in values if value>0];self.reset(bool(values))
        if not values:return
        series=QPieSeries();series.setPieSize(.78);series.setHoleSize(.48)
        for index,(name,value) in enumerate(values):
            piece=series.append(name,value/100);piece.setColor(QColor(PALETTE[index%len(PALETTE)]));piece.setBorderColor(QColor('#162638'))
            piece.setLabel(f'{name}: {money(value)}');piece.hovered.connect(lambda state,n=name,v=value:QToolTip.showText(QCursor.pos(),f'{n}: {money(v)}') if state else None)
        self.chart.addSeries(series);self.chart.legend().setVisible(True);self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight);self.chart.legend().setLabelColor(QColor('#d8e3f1'));self.chart.legend().setFont(QFont('Segoe UI',9))

    def menu(self,point):
        menu=QMenu(self);menu.addAction('Salvar gráfico em PNG',self.save_png);menu.exec(self.view.mapToGlobal(point))

    def save_png(self):
        path,_=QFileDialog.getSaveFileName(self,'Salvar gráfico','grafico-forgeon.png','Imagem PNG (*.png)')
        if path and not self.grab().save(path,'PNG'):QMessageBox.warning(self,'Gráfico','Não foi possível salvar a imagem.')
