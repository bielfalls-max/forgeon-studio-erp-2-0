from io import BytesIO
from hashlib import sha256
from threading import Event
from urllib.request import Request
import pytest
from forgeon.business.updates import Release,select_release,download_release,SafeRedirect,version_tuple,REPOSITORY

PAYLOAD=b'MZ'+b'conteudo-de-teste-sem-execucao'*20
DIGEST=sha256(PAYLOAD).hexdigest()


def metadata(version='2.0.2',**changes):
    name=f'ForgeonStudioERP-{version}-Windows-x64-Setup.exe'
    r={'tag_name':'v'+version,'body':'Notas do hotfix','draft':False,'prerelease':True,'assets':[{'name':name,'size':len(PAYLOAD),'digest':'sha256:'+DIGEST,'browser_download_url':f'https://github.com/{REPOSITORY}/releases/download/v{version}/{name}'}]}
    r.update(changes);return r


class Opener:
    def open(self,*a,**k):return BytesIO(PAYLOAD)


def test_selects_newest_numeric_version_and_never_draft():
    result=select_release([metadata('2.0.2'),metadata('2.0.10'),metadata('9.0.0',draft=True)],'2.0.1')
    assert result.version=='2.0.10'
    assert select_release([metadata('2.0.1')],'2.0.1') is None

@pytest.mark.parametrize('change',[{'digest':''},{'digest':'sha256:123'},{'size':-1},{'browser_download_url':'http://evil.invalid/app.exe'},{'name':'outro.exe'}])
def test_rejects_unverifiable_installer_metadata(change):
    data=metadata();data['assets'][0].update(change)
    assert select_release([data],'2.0.1') is None


def test_verified_download_and_no_remaining_partial(tmp_path):
    release=select_release([metadata()],'2.0.1');target=tmp_path/'hotfix.exe';progress=[]
    result=download_release(release,target,lambda count,total:progress.append((count,total)),opener=Opener())
    assert result==target and target.read_bytes()==PAYLOAD
    assert progress[-1]==(len(PAYLOAD),len(PAYLOAD))
    assert not list(tmp_path.glob('*.part'))


def test_failed_hash_preserves_existing_file(tmp_path):
    data=metadata();data['assets'][0]['digest']='sha256:'+'0'*64
    release=select_release([data],'2.0.1');target=tmp_path/'hotfix.exe';target.write_bytes(b'anterior')
    with pytest.raises(ValueError,match='integridade'):download_release(release,target,opener=Opener())
    assert target.read_bytes()==b'anterior'
    assert not list(tmp_path.glob('*.part'))


def test_cancel_does_not_leave_executable(tmp_path):
    cancel=Event();cancel.set();release=select_release([metadata()],'2.0.1');target=tmp_path/'hotfix.exe'
    with pytest.raises(ValueError,match='cancelado'):download_release(release,target,cancel=cancel,opener=Opener())
    assert not target.exists() and not list(tmp_path.glob('*.part'))

@pytest.mark.parametrize('target',['http://github.com/file','https://evil.invalid/file','file:///etc/passwd'])
def test_redirect_blocks_non_https_and_external_hosts(target):
    with pytest.raises(ValueError):SafeRedirect().redirect_request(Request('https://github.com/'),None,302,'',{},target)


def test_version_tuple_rejects_unexpected_tags():
    assert version_tuple('v2.0.10')>(2,0,9)
    with pytest.raises(ValueError):version_tuple('v2.0.1/../../x')
