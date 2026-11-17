"""Rolagem consistente em tabelas, painéis aninhados e formulários."""
from PySide6.QtCore import QObject,QEvent,Qt
from PySide6.QtWidgets import QWidget,QAbstractScrollArea,QAbstractItemView,QComboBox,QAbstractSpinBox,QScrollBar


class WheelRouter(QObject):
    def __init__(self,root):
        super().__init__(root);self.root=root

    def eventFilter(self,watched,event):
        if event.type()!=QEvent.Type.Wheel or not isinstance(watched,QWidget):return False
        if watched!=self.root and not self.root.isAncestorOf(watched):return False
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:return False
        # Listas abertas de seleção continuam navegáveis. Fechadas, não alteram dados ao rolar a página.
        if isinstance(watched,QComboBox) and watched.view().isVisible():return False
        pixel=event.pixelDelta();angle=event.angleDelta();is_pixel=not pixel.isNull()
        delta=pixel if is_pixel else angle;x,y=delta.x(),delta.y()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:x,y=x+y,0
        elif isinstance(watched,QScrollBar) and watched.orientation()==Qt.Orientation.Horizontal:x,y=x+y,0
        areas=[];parent=watched
        while parent:
            if isinstance(parent,QAbstractScrollArea) and parent not in areas:areas.append(parent)
            parent=parent.parentWidget()
        protected=isinstance(watched,(QComboBox,QAbstractSpinBox))
        if not areas:return protected
        for amount,horizontal in ((x,True),(y,False)):
            if not amount:continue
            for area in areas:
                if isinstance(area,QAbstractItemView):
                    area.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                    area.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                bar=area.horizontalScrollBar() if horizontal else area.verticalScrollBar()
                if bar.maximum()<=bar.minimum():continue
                if (amount>0 and bar.value()<=bar.minimum()) or (amount<0 and bar.value()>=bar.maximum()):continue
                step=amount if is_pixel else amount/120*min(bar.singleStep(),40)*3
                remainder=float(bar.property('forgeonWheelRemainder') or 0)-step
                whole=int(remainder);bar.setProperty('forgeonWheelRemainder',remainder-whole)
                bar.setValue(bar.value()+whole);break
        event.accept();return True
