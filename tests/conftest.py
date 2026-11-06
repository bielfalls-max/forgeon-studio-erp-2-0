import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from forgeon.db.store import Store
from forgeon.business.service import ERP

@pytest.fixture
def erp(tmp_path):
    s=Store(tmp_path/'new.sqlite3')
    yield ERP(s)
    s.close()

@pytest.fixture
def product(erp):
    return erp.save_product({'name':'Sonic','model':'10 cm','weight':'100','hours':'2','packaging':'2','other':'1'})

@pytest.fixture(scope='session')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
