import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from forgeon.db.store import Store
from forgeon.business.service import ERP

@pytest.fixture
def erp(tmp_path):
    s=Store(tmp_path/'new.sqlite3')
    service=ERP(s)
    # Base numérica explícita para os testes anteriores; padrões de instalação
    # são verificados separadamente nos testes HF12 com um banco novo.
    with s.transaction():
        s.db.executemany('UPDATE settings SET value=? WHERE key=?',[(v,k) for k,v in {'energy_kwh':'1','power_w':'150','machine_hour':'1','packaging_default':'0','labor_unit':'0','loss_percent':'0'}.items()])
    yield service
    s.close()

@pytest.fixture
def product(erp):
    return erp.save_product({'name':'Sonic','model':'10 cm','weight':'100','hours':'2','packaging':'2','other':'1'})

@pytest.fixture(scope='session')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
