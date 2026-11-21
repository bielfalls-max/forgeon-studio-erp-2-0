from copy import deepcopy
from decimal import Decimal
import pytest
from PySide6.QtCore import QPoint,QPointF,Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication,QDialog,QFileDialog,QMessageBox,QScrollArea,QWidget,QVBoxLayout,QComboBox,QSpinBox
from forgeon.business.recipes import copy_colors,paste_colors
from forgeon.ui.main import MainWindow
from forgeon.ui.production import SlicingProductDialog
from forgeon.ui.recipes import PasteColorsDialog
from forgeon.ui.scrolling import WheelRouter
from forgeon.ui.widgets import Table
from test_hf02 import sliced


def source_and_target(erp):
    source=erp.save_product({'name':'Metal Sonic','model':'12 cm','hours':'6','packaging':'2'})
    target=erp.save_product({'name':'Metal Sonic Dourado','model':'12 cm','hours':'1','packaging':'3','other':'4','manual':'20'})
    fid=erp.filament('PLA','Prata','100');erp.set_color(source,fid,'11.42')
    fid=erp.filament('PLA','Preto','80');erp.set_color(source,fid,'5.99')
    return source,target


def test_selected_product_import_replaces_recipe_and_keeps_color_edits(app,erp,tmp_path,monkeypatch):
    source,target=source_and_target(erp);file=sliced(tmp_path);w=MainWindow(erp);w.nav.setCurrentRow(1);w.select_product_row(target)
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *a:([str(file)],''))
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(w,'info',lambda *a:None)
    def execute(dialog):
        assert dialog.target.currentData()==target
        dialog.colors.item(0,1).setText('Dourado')
        dialog.units.setValue(2);dialog.units.setValue(1)
        assert dialog.colors.item(0,1).text()=='Dourado'
        for row in range(dialog.plate_table.rowCount()):dialog.plate_table.item(row,0).setCheckState(Qt.CheckState.Unchecked)
        assert dialog.colors.rowCount()==0
        for row in range(dialog.plate_table.rowCount()):dialog.plate_table.item(row,0).setCheckState(Qt.CheckState.Checked)
        assert dialog.colors.item(0,1).text()=='Dourado'
        dialog.confirm.setChecked(True);dialog.save();return dialog.result()
    monkeypatch.setattr(SlicingProductDialog,'exec',execute)
    try:
        w.slicing()
        assert len(erp.s.rows('SELECT * FROM products'))==2
        assert erp.product(target)['name']=='Metal Sonic Dourado'
        assert erp.product(target)['hours']=='6'
        assert Decimal(erp.product(target)['weight'])==21
        assert 'Dourado' in [c['color'] for c in erp.colors(target)]
        assert erp.product(source)['hours']=='6' and len(erp.colors(source))==2
    finally:w.close()


def test_wizard_can_explicitly_create_another_product(app,erp,tmp_path,monkeypatch):
    _,target=source_and_target(erp);dialog=SlicingProductDialog(erp,sliced(tmp_path),pid=target)
    dialog.target.setCurrentIndex(0);dialog.name.setText('Metal Sonic Preto');dialog.confirm.setChecked(True);dialog.save()
    assert dialog.result()==QDialog.DialogCode.Accepted and dialog.result_data[0]!=target
    assert len(erp.s.rows('SELECT * FROM products'))==3


def test_color_copy_adapts_recipe_without_overwriting_identity_costs_or_snapshots(erp):
    from test_orders import load,row
    source,target=source_and_target(erp)
    erp.set_color(target,erp.colors(source)[0]['filament_id'],'10')
    erp.origin('Anúncio','Dourado','00007',target);load(erp,[{**row(sku='00007',title='Anúncio'),'variation':'Dourado'}])
    before=erp.s.rows('SELECT * FROM order_items');usage=erp.s.rows('SELECT * FROM item_usage')
    assert before[0]['cost_cents'] is not None
    original=erp.product(target);payload=copy_colors(erp,source);colors=deepcopy(payload['colors']);colors[0]['color']='Dourado'
    paste_colors(erp,target,payload,colors)
    after=erp.product(target)
    for field in ('name','model','hours','manual_cents','packaging_cents','other_cents'):assert after[field]==original[field]
    assert Decimal(after['weight'])==Decimal('17.41')
    assert {c['color'] for c in erp.colors(target)}=={'Dourado','Preto'}
    assert erp.s.rows('SELECT * FROM order_items')==before and erp.s.rows('SELECT * FROM item_usage')==usage
    assert erp.colors(source)[0]['color']=='Prata'
    assert payload['colors'][0]['color']=='Prata'
    assert erp.s.one('SELECT count(*) n FROM recipe_revisions WHERE product_id=?',(target,))['n']==3


def test_paste_combines_same_color_keeps_existing_reference_and_optional_time(erp):
    source,target=source_and_target(erp);payload=copy_colors(erp,source);colors=deepcopy(payload['colors'])
    for c in colors:c.update(color='Preto',kg='999')
    paste_colors(erp,target,payload,colors,True)
    assert erp.product(target)['hours']=='6'
    assert len(erp.colors(target))==1 and Decimal(erp.colors(target)[0]['grams'])==Decimal('17.41')
    assert erp.colors(target)[0]['kg_cents']==8000


def test_invalid_paste_and_cancel_leave_database_unchanged(app,erp):
    source,target=source_and_target(erp);payload=copy_colors(erp,source);before=erp.s.db.total_changes
    dialog=PasteColorsDialog(erp,payload,target);dialog.colors.item(0,1).setText('Dourado');dialog.reject()
    assert erp.s.db.total_changes==before
    for colors in ([{**payload['colors'][0],'grams':'-1'}],[],[{**payload['colors'][0],'color':''}]):
        with pytest.raises(ValueError):paste_colors(erp,target,payload,colors)
    with pytest.raises(ValueError):paste_colors(erp,source,payload,payload['colors'])
    assert erp.s.db.total_changes==before


def test_products_copy_paste_opens_editable_preview_and_saves_only_on_apply(app,erp,monkeypatch):
    source,target=source_and_target(erp);w=MainWindow(erp);w.nav.setCurrentRow(1)
    w.select_product_row(source);w.copy_product_colors();w.select_product_row(target)
    def execute(dialog):
        assert dialog.target==target and dialog.colors.item(0,1).text()=='Prata'
        dialog.colors.item(0,1).setText('Dourado');dialog.copy_hours.setChecked(True);dialog.save();return dialog.result()
    monkeypatch.setattr(PasteColorsDialog,'exec',execute)
    try:
        w.paste_product_colors()
        assert erp.product(target)['hours']=='6' and len(erp.s.rows('SELECT * FROM products'))==2
        assert 'Dourado' in [c['color'] for c in erp.colors(target)]
    finally:w.close()


def wheel(widget,x=0,y=-120,shift=False,pixels=False,ctrl=False):
    mods=Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
    if ctrl:mods|=Qt.KeyboardModifier.ControlModifier
    event=QWheelEvent(QPointF(10,10),QPointF(widget.mapToGlobal(QPoint(10,10))),QPoint(x,y) if pixels else QPoint(),QPoint() if pixels else QPoint(x,y),Qt.MouseButton.NoButton,mods,Qt.ScrollPhase.NoScrollPhase,False)
    QApplication.sendEvent(widget,event)


def scroll_fixture(app):
    root=QWidget();layout=QVBoxLayout(root);area=QScrollArea();area.setWidgetResizable(True);layout.addWidget(area)
    content=QWidget();content.setMinimumHeight(1100);body=QVBoxLayout(content);area.setWidget(content)
    combo=QComboBox();combo.addItems(['A','B','C']);body.addWidget(combo)
    spin=QSpinBox();spin.setValue(5);body.addWidget(spin)
    table=Table();table.setFixedHeight(180);table.fill([{'a':str(i),'b':'x'*70,'c':'y'*70} for i in range(40)]);body.addWidget(table);body.addStretch()
    root.resize(420,420);router=WheelRouter(root);app.installEventFilter(router);root.show();app.processEvents()
    return root,area,table,combo,spin,router


def test_mouse_scroll_nested_vertical_horizontal_and_trackpad(app):
    root,area,table,combo,spin,router=scroll_fixture(app)
    try:
        wheel(table.viewport());assert table.verticalScrollBar().value()>0 and area.verticalScrollBar().value()==0
        wheel(table.viewport(),shift=True);assert table.horizontalScrollBar().value()>0
        bar=table.horizontalScrollBar();old=bar.value();wheel(table.viewport(),x=-12,y=0,pixels=True);assert bar.value()==old+12
        table.verticalScrollBar().setValue(table.verticalScrollBar().maximum());wheel(table.viewport());assert area.verticalScrollBar().value()>0
        area.verticalScrollBar().setValue(0);table.verticalScrollBar().setValue(0);wheel(table.viewport(),y=120)
        assert area.verticalScrollBar().value()==0 and table.verticalScrollBar().value()==0
    finally:app.removeEventFilter(router);root.close()


def test_wheel_does_not_change_closed_inputs_and_bubbles_to_page(app):
    root,area,table,combo,spin,router=scroll_fixture(app)
    try:
        wheel(combo);assert combo.currentIndex()==0 and area.verticalScrollBar().value()>0
        old=area.verticalScrollBar().value();wheel(spin);assert spin.value()==5 and area.verticalScrollBar().value()>old
        bar=table.horizontalScrollBar();bar.setValue(0);wheel(table.viewport(),shift=True,ctrl=True);assert bar.value()==0
    finally:app.removeEventFilter(router);root.close()


def test_horizontal_bar_and_nested_scroll_reverse_direction(app):
    root,area,table,combo,spin,router=scroll_fixture(app)
    try:
        bar=table.horizontalScrollBar();wheel(bar);assert bar.value()>0
        table.verticalScrollBar().setValue(0);area.verticalScrollBar().setValue(200)
        wheel(table.viewport(),y=120);assert area.verticalScrollBar().value()<200
        table.verticalScrollBar().setValue(0);bar.setValue(0)
        wheel(table.viewport(),x=-10,y=-10,pixels=True)
        assert bar.value()==10 and table.verticalScrollBar().value()==10
    finally:app.removeEventFilter(router);root.close()


def test_scroll_router_also_applies_to_parented_dialogs(app):
    root=QWidget();router=WheelRouter(root);app.installEventFilter(router)
    dialog=QDialog(root);layout=QVBoxLayout(dialog);table=Table();layout.addWidget(table)
    table.fill([{'a':str(i)} for i in range(60)]);dialog.resize(400,300);dialog.show();app.processEvents()
    try:
        wheel(table.viewport());assert table.verticalScrollBar().value()>0
    finally:app.removeEventFilter(router);dialog.close();root.close()


def test_archived_import_target_never_falls_back_to_new_product(app,erp,tmp_path):
    _,target=source_and_target(erp);erp.archive(target)
    with pytest.raises(ValueError,match='Reative'):SlicingProductDialog(erp,sliced(tmp_path),pid=target)
    assert len(erp.s.rows('SELECT * FROM products'))==2
