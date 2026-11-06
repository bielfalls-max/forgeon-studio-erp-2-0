"""Composição local do tema: paisagem, vidro fosco e cartões legíveis."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPoint, QSize
from PySide6.QtGui import QPainter, QPixmap, QColor, QLinearGradient, QPainterPath, QFont, QIcon
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsBlurEffect, QLayout, QSizePolicy)

ASSETS = Path(__file__).resolve().parent.parent / 'assets'


def app_icon():
    return QIcon(str(ASSETS / 'forgeon.ico'))


class MountainBackdrop(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QPixmap(str(ASSETS / 'swiss-alps.png'))
        self.focus_mode = False
        self._size = QSize()
        self.frosted = QPixmap()

    def prepare(self):
        if self._size == self.size() and not self.frosted.isNull():
            return
        self._size = self.size()
        if self.image.isNull() or self.width() < 1 or self.height() < 1:
            return
        scaled = self.image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x, y = (scaled.width()-self.width())//2, (scaled.height()-self.height())//2
        self.original = scaled.copy(x,y,self.width(),self.height())
        scene=QGraphicsScene()
        item=QGraphicsPixmapItem(self.original)
        effect=QGraphicsBlurEffect(); effect.setBlurRadius(22)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect); scene.addItem(item)
        self.frosted=QPixmap(self.size()); self.frosted.fill(Qt.GlobalColor.transparent)
        painter=QPainter(self.frosted)
        scene.render(painter,QRectF(self.rect()),QRectF(self.rect()))
        painter.end()

    def set_focus(self,enabled):
        self.focus_mode=enabled
        self.update()
        for child in self.findChildren(GlassCard):child.update()

    def paintEvent(self,event):
        self.prepare()
        p=QPainter(self)
        p.fillRect(self.rect(),QColor('#0a1221'))
        if not self.image.isNull() and not self.focus_mode:
            p.drawPixmap(0,0,self.original)
            g=QLinearGradient(0,0,self.width(),self.height())
            g.setColorAt(0,QColor(6,14,27,214));g.setColorAt(.55,QColor(8,17,31,172));g.setColorAt(1,QColor(7,17,30,140))
            p.fillRect(self.rect(),g)


class GlassCard(QFrame):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('glassCard')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,False)
        self.body=QVBoxLayout(self);self.body.setContentsMargins(20,18,20,18);self.body.setSpacing(12)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        clip=QPainterPath();clip.addRoundedRect(rect,18,18);p.setClipPath(clip)
        backdrop=self.parentWidget()
        while backdrop is not None and not isinstance(backdrop,MountainBackdrop):backdrop=backdrop.parentWidget()
        if backdrop is not None and not backdrop.focus_mode:
            backdrop.prepare()
            if not backdrop.frosted.isNull():
                point=self.mapTo(backdrop,QPoint(0,0))
                p.drawPixmap(QRectF(self.rect()),backdrop.frosted,QRectF(point.x(),point.y(),self.width(),self.height()))
        p.fillRect(self.rect(),QColor(12,24,42,225 if backdrop is None or backdrop.focus_mode else 205))
        reflection=QLinearGradient(0,0,self.width()*.7,self.height())
        reflection.setColorAt(0,QColor(220,236,255,21));reflection.setColorAt(.48,QColor(220,236,255,5));reflection.setColorAt(1,QColor(220,236,255,0))
        p.fillRect(self.rect(),reflection)
        p.setClipping(False);p.setPen(QColor(203,221,245,38));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRoundedRect(rect,18,18)
        p.setPen(QColor(232,240,255,42));p.drawLine(21,1,self.width()-22,1)


class MetricCard(GlassCard):
    def __init__(self,title,caption):
        super().__init__()
        self.title=QLabel(title.upper());self.title.setObjectName('metricTitle')
        self.value=QLabel('—');self.value.setObjectName('metricValue')
        self.caption=QLabel(caption);self.caption.setObjectName('muted');self.caption.setWordWrap(True)
        self.body.addWidget(self.title);self.body.addWidget(self.value);self.body.addWidget(self.caption)
        self.setMinimumHeight(133)

    def set_value(self,value,negative=False):
        self.value.setText(str(value));self.value.setStyleSheet('color: #ff9d9b;' if negative else 'color: #f7f0e7;')


class FlowLayout(QLayout):
    """Barra de ferramentas que quebra linhas em janelas menores."""
    def __init__(self):
        super().__init__();self.items=[];self.setContentsMargins(0,0,0,0);self.setSpacing(8)
    def addItem(self,item):self.items.append(item)
    def count(self):return len(self.items)
    def itemAt(self,index):return self.items[index] if 0<=index<len(self.items) else None
    def takeAt(self,index):return self.items.pop(index) if 0<=index<len(self.items) else None
    def expandingDirections(self):return Qt.Orientation(0)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self.arrange(QRectF(0,0,width,0),True)
    def sizeHint(self):return self.minimumSize()
    def minimumSize(self):
        size=QSize()
        for item in self.items:size=size.expandedTo(item.minimumSize())
        return size
    def setGeometry(self,rect):super().setGeometry(rect);self.arrange(QRectF(rect),False)
    def arrange(self,rect,test):
        x,y,line=rect.x(),rect.y(),0;space=self.spacing()
        for item in self.items:
            hint=item.sizeHint();width=min(hint.width(),int(rect.width()))
            if x+width>rect.right()+1 and line>0:x=rect.x();y+=line+space;line=0
            if not test:
                from PySide6.QtCore import QRect
                item.setGeometry(QRect(int(x),int(y),width,hint.height()))
            x+=width+space;line=max(line,hint.height())
        return int(y+line-rect.y())
