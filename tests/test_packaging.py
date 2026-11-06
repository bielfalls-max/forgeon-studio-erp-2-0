import json
from forgeon.packaging_check import check


def test_packaging_check_uses_temporary_database(app,tmp_path,monkeypatch):
    local=tmp_path/'dados-reais'
    monkeypatch.setenv('LOCALAPPDATA',str(local))
    report=tmp_path/'verificacao.json'
    assert check(report)==0
    result=json.loads(report.read_text(encoding='utf-8'))
    assert result['ok'] and result['screens']==10 and result['errors']==[]
    assert not local.exists()  # Never create/use the user's actual data directory.
