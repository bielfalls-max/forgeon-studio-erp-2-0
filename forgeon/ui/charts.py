"""Gráficos interativos locais com QPainter, sem dependência de QtCharts."""
from datetime import date
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter,QColor,QPen,QFont,QPainterPath,QLinearGradient
from PySide6.QtWidgets import QWidget,QLabel,QToolTip,QFileDialog,QMessageBox,QMenu
from .visual import GlassCard
from ..business.numbers import money

PALETTE=['#f5ad78','#7dd5c0','#86acec','#dba2d3','#e5ca7b','#a6c4d2']


def compact(value):
    if abs(value)>=1000000:return f'{value/1000000:.1f} mi'.replace('.',',')
    if abs(value)>=1000:return f'{value/1000:.1f} mil'.replace('.',',')
    if 0<abs(value)<1:return f'{value:.3g}'.replace('.',',')
    return f'{value:.1f}'.rstrip('0').rstrip('.').replace('.',',') if value!=int(value) else str(int(value))


class PlotCanvas(QWidget):
    def __init__(self):
        super().__init__();self.kind='line';self.rows=[];self.key='';self.value='';self.unit='';self.hits=[];self.ring=None
        self.setMinimumHeight(190);self.setMouseTracking(True)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setFont(QFont('Segoe UI',9));self.hits=[];self.ring=None
        if not self.rows:return
        if self.kind=='line':self.draw_line(p)
        elif self.kind=='bars':self.draw_bars(p)
        else:self.draw_donut(p)
    def grid(self,p,rect,maximum,currency=False):
        for index in range(5):
            y=rect.bottom()-rect.height()*index/4
            p.setPen(QColor(166,195,228,28));p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            p.setPen(QColor('#aabbd0'));label=('R$ ' if currency else '')+compact(maximum*index/4)
            p.drawText(QRectF(0,y-9,rect.left()-9,18),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,label)
    def draw_line(self,p):
        rect=QRectF(70,14,max(1,self.width()-88),max(1,self.height()-48))
        amounts=[row[self.value]/100 for row in self.rows];highest=max(amounts)
        if highest>0:
            magnitude=10**math.floor(math.log10(highest));maximum=math.ceil(highest/magnitude*2)/2*magnitude
            if maximum==highest:maximum*=1.15
        else:maximum=1
        self.grid(p,rect,maximum,True)
        days=[date.fromisoformat(row['date']).toordinal() for row in self.rows];span=max(1,days[-1]-days[0])
        points=[]
        for day,amount,row in zip(days,amounts,self.rows):
            x=rect.center().x() if len(days)==1 else rect.left()+rect.width()*(day-days[0])/span
            point=QPointF(x,rect.bottom()-rect.height()*amount/maximum);points.append(point)
            self.hits.append((QRectF(x-9,point.y()-9,18,18),f"{row['date'][8:10]}/{row['date'][5:7]} • {money(row[self.value])}"))
        path=QPainterPath(points[0])
        for point in points[1:]:path.lineTo(point)
        area=QPainterPath(path);area.lineTo(points[-1].x(),rect.bottom());area.lineTo(points[0].x(),rect.bottom());area.closeSubpath()
        gradient=QLinearGradient(0,rect.top(),0,rect.bottom());gradient.setColorAt(0,QColor(245,173,120,40));gradient.setColorAt(1,QColor(245,173,120,0))
        p.fillPath(area,gradient);p.setPen(QPen(QColor(PALETTE[0]),2.5));p.drawPath(path);p.setBrush(QColor(PALETTE[0]))
        for point in points:p.drawEllipse(point,3.5,3.5)
        ticks=sorted({round(i*(len(days)-1)/min(5,max(1,len(days)-1))) for i in range(min(6,len(days)))})
        p.setPen(QColor('#aabbd0'))
        for index in ticks:
            row=self.rows[index];p.drawText(QRectF(points[index].x()-27,rect.bottom()+9,54,18),Qt.AlignmentFlag.AlignCenter,f"{row['date'][8:10]}/{row['date'][5:7]}")
    def draw_bars(self,p):
        rect=QRectF(min(146,self.width()*.34),12,max(1,self.width()-min(146,self.width()*.34)-56),max(1,self.height()-44))
        maximum=max(1,max(float(row[self.value]) for row in self.rows)*1.16)
        if self.unit=='un.':maximum=max(4,math.ceil(max(float(row[self.value]) for row in self.rows)/4)*4)
        for index in range(5):
            x=rect.left()+rect.width()*index/4;p.setPen(QColor(166,195,228,25));p.drawLine(QPointF(x,rect.top()),QPointF(x,rect.bottom()))
            p.setPen(QColor('#aabbd0'));p.drawText(QRectF(x-24,rect.bottom()+6,48,18),Qt.AlignmentFlag.AlignCenter,compact(maximum*index/4))
        step=rect.height()/len(self.rows);height=min(30,step*.55)
        for index,row in enumerate(self.rows):
            y=rect.top()+step*(index+.5);bar=QRectF(rect.left(),y-height/2,rect.width()*float(row[self.value])/maximum,height)
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(PALETTE[1]));p.drawRoundedRect(bar,4,4)
            p.setPen(QColor('#b9cbe0'));label=p.fontMetrics().elidedText(str(row[self.key]),Qt.TextElideMode.ElideRight,int(rect.left()-12))
            p.drawText(QRectF(0,y-12,rect.left()-12,24),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,label)
            p.drawText(QRectF(bar.right()+7,y-12,45,24),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,compact(float(row[self.value])))
            self.hits.append((QRectF(0,y-step/2,self.width(),step),f"{row[self.key]}: {row[self.value]} {self.unit}"))
        p.setPen(QColor('#829bb8'));p.drawText(QRectF(0,self.height()-18,self.width(),18),Qt.AlignmentFlag.AlignRight,self.unit)
    def draw_donut(self,p):
        total=sum(value for name,value in self.rows);cx=self.width()*.25;cy=self.height()*.51;radius=min(self.width()*.20,self.height()*.37);thickness=radius*.30
        bounds=QRectF(cx-radius,cy-radius,radius*2,radius*2);start=90.;pieces=[]
        for index,(name,value) in enumerate(self.rows):
            span=value/total*360;pen=QPen(QColor(PALETTE[index%len(PALETTE)]),thickness);pen.setCapStyle(Qt.PenCapStyle.FlatCap);p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(bounds,int(start*16),-max(1,int((span-1)*16)));percent=f'{value/total*100:.1f}'.replace('.',',');pieces.append((span,f'{name}: {money(value)} · {percent}%'));start-=span
        p.setPen(QColor('#a9bbd1'));p.setFont(QFont('Segoe UI',8));p.drawText(QRectF(cx-radius,cy-19,radius*2,18),Qt.AlignmentFlag.AlignCenter,'TOTAL')
        p.setPen(QColor('#f1e8df'));p.setFont(QFont('Segoe UI',11,QFont.Weight.DemiBold));p.drawText(QRectF(cx-radius-10,cy+1,radius*2+20,24),Qt.AlignmentFlag.AlignCenter,money(total))
        p.setFont(QFont('Segoe UI',9));legend_x=self.width()*.53;top=cy-len(self.rows)*14
        for index,(name,value) in enumerate(self.rows):
            y=top+index*28;p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(PALETTE[index%len(PALETTE)]));p.drawRoundedRect(QRectF(legend_x,y+3,7,7),2,2)
            p.setPen(QColor('#c7d6e8'));label=p.fontMetrics().elidedText(f'{name}: {money(value)}',Qt.TextElideMode.ElideRight,int(self.width()-legend_x-18))
            box=QRectF(legend_x+13,y-2,self.width()-legend_x-15,22);p.drawText(box,Qt.AlignmentFlag.AlignVCenter,label);self.hits.append((box,f'{name}: {money(value)}'))
        self.ring=(cx,cy,radius,thickness,pieces)
    def mouseMoveEvent(self,event):
        point=event.position();tip=None
        for rect,label in self.hits:
            if rect.contains(point):tip=label;break
        if tip is None and self.ring:
            cx,cy,radius,width,pieces=self.ring;distance=math.hypot(point.x()-cx,point.y()-cy)
            if radius-width/2<=distance<=radius+width/2:
                angle=(90-math.degrees(math.atan2(cy-point.y(),point.x()-cx)))%360
                for span,label in pieces:
                    if angle<=span:tip=label;break
                    angle-=span
        if tip:QToolTip.showText(event.globalPosition().toPoint(),tip,self)
        else:QToolTip.hideText()


class ChartCard(GlassCard):
    def __init__(self,title,subtitle=''):
        super().__init__();self.setMinimumHeight(280)
        label=QLabel(title);label.setObjectName('sectionTitle');self.body.addWidget(label)
        self.caption=QLabel(subtitle);self.caption.setObjectName('muted');self.caption.setWordWrap(True);self.body.addWidget(self.caption)
        self.view=PlotCanvas();self.body.addWidget(self.view,1)
        self.empty=QLabel('Sem dados neste período. Cadastre ou importe pedidos para visualizar.');self.empty.setObjectName('muted');self.empty.setWordWrap(True);self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter);self.body.addWidget(self.empty,1);self.empty.hide()
        self.view.setToolTip('Passe o mouse para ver valores. Botão direito para salvar o gráfico em PNG.');self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.view.customContextMenuRequested.connect(self.menu)
    def reset(self,kind,rows,key='',value='',unit=''):
        self.view.kind=kind;self.view.rows=rows;self.view.key=key;self.view.value=value;self.view.unit=unit
        self.view.setVisible(bool(rows));self.empty.setVisible(not rows);self.view.update()
    def line(self,rows,key='gross_cents'):self.reset('line',rows,value=key)
    def bars(self,rows,label,value,unit='un.'):self.reset('bars',rows[:6],label,value,unit)
    def donut(self,values):self.reset('donut',[(name,value) for name,value in values if value>0])
    def menu(self,point):
        menu=QMenu(self);menu.addAction('Salvar gráfico em PNG',self.save_png);menu.exec(self.view.mapToGlobal(point))
    def save_png(self):
        path,_=QFileDialog.getSaveFileName(self,'Salvar gráfico','grafico-forgeon.png','Imagem PNG (*.png)')
        if path and not self.grab().save(path,'PNG'):QMessageBox.warning(self,'Gráfico','Não foi possível salvar a imagem.')
