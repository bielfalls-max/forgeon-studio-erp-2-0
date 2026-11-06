"""Consulta/download opt-in: nunca instala nem executa conteúdo baixado."""
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlparse, unquote
import hashlib
import json
import os
import re
import tempfile
from .numbers import norm
from ..version import VERSION, REPOSITORY

MAX_DOWNLOAD = 250 * 1024 * 1024
API = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=20'


def version_tuple(value):
    m=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',str(value))
    if not m:raise ValueError('Versão não reconhecida.')
    return tuple(map(int,m.groups()))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    filename: str
    size: int
    sha256: str
    notes: str
    page: str
    preview: bool = False


def select_release(releases,current=VERSION):
    candidates=[]
    for r in releases:
        if r.get('draft'):continue
        try:
            tag=r['tag_name'];v=version_tuple(tag)
        except (KeyError,ValueError):continue
        if v<=version_tuple(current):continue
        version='.'.join(map(str,v));name=f'ForgeonStudioERP-{version}-Windows-x64-Setup.exe'
        for asset in r.get('assets',[]):
            if asset.get('name')!=name:continue
            url=asset.get('browser_download_url','')
            expected=f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
            digest=asset.get('digest','')
            size=asset.get('size',0)
            if url!=expected or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):continue
            if not isinstance(size,int) or isinstance(size,bool) or not 0<size<=MAX_DOWNLOAD:continue
            candidates.append(Release(version,url,name,size,digest[7:].lower(),str(r.get('body',''))[:60000],
                                      f'https://github.com/{REPOSITORY}/releases/tag/{tag}',bool(r.get('prerelease'))))
    return max(candidates,key=lambda r:version_tuple(r.version)) if candidates else None


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        host=urlparse(newurl).hostname or ''
        if urlparse(newurl).scheme!='https' or not (host in ('github.com','api.github.com') or host.endswith('.githubusercontent.com')):
            raise ValueError('Redirecionamento fora dos servidores de distribuição do GitHub.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def request(url):
    return Request(url,headers={'User-Agent':f'ForgeonStudioERP/{VERSION}','Accept':'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/octet-stream'})


def fetch_release(current=VERSION,opener=None):
    opener=opener or build_opener(SafeRedirect())
    with opener.open(request(API),timeout=15) as response:
        raw=response.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('Resposta de atualizações excede o limite.')
    releases=json.loads(raw)
    if not isinstance(releases,list):raise ValueError('Resposta de atualizações inválida.')
    return select_release(releases,current)


def download_release(release,destination,progress=None,cancel=None,opener=None):
    # Revalidate URL/path and metadata even if called without the UI selection step.
    tag='v'+release.version
    if release.url not in (f'https://github.com/{REPOSITORY}/releases/download/{tag}/{release.filename}',
                            f'https://github.com/{REPOSITORY}/releases/download/{release.version}/{release.filename}'):
        raise ValueError('Endereço do instalador não reconhecido.')
    if release.filename!=f'ForgeonStudioERP-{release.version}-Windows-x64-Setup.exe' or not re.fullmatch(r'[a-f0-9]{64}',release.sha256):
        raise ValueError('Metadados do instalador inválidos.')
    if not 0<release.size<=MAX_DOWNLOAD:raise ValueError('Tamanho do instalador inválido.')
    target=Path(destination)
    if target.suffix.lower()!='.exe':raise ValueError('Salve o instalador como arquivo .exe.')
    target.parent.mkdir(parents=True,exist_ok=True)
    opener=opener or build_opener(SafeRedirect())
    fd,temp=tempfile.mkstemp(prefix='.forgeon-download-',suffix='.part',dir=target.parent)
    count=0;digest=hashlib.sha256();magic=b''
    try:
        with os.fdopen(fd,'wb') as output:
            with opener.open(request(release.url),timeout=15) as response:
                while True:
                    if cancel and cancel.is_set():raise ValueError('Download cancelado. Nenhum instalador foi executado.')
                    chunk=response.read(128*1024)
                    if not chunk:break
                    if not magic:magic=chunk[:2]
                    count+=len(chunk)
                    if count>release.size or count>MAX_DOWNLOAD:raise ValueError('Download excedeu o tamanho publicado.')
                    output.write(chunk);digest.update(chunk)
                    if progress:progress(count,release.size)
        if count!=release.size or digest.hexdigest()!=release.sha256 or magic!=b'MZ':
            raise ValueError('O instalador não passou na verificação de integridade. Download descartado.')
        if cancel and cancel.is_set():raise ValueError('Download cancelado.')
        os.replace(temp,target)
        return target
    finally:
        Path(temp).unlink(missing_ok=True)
