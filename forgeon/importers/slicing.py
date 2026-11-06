"""Reads metadata only. Never extracts archives or executes printer commands."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
from decimal import Decimal
import re
from defusedxml.ElementTree import fromstring
from ..business.numbers import decimal, quantity

MAX_FILE = 128 * 1024 * 1024
MAX_XML = 8 * 1024 * 1024


def duration(text):
    text = str(text).strip()
    if re.fullmatch(r'\d+(\.\d+)?', text):
        return decimal(text) / 3600  # slicer XML numeric values are seconds
    if not re.fullmatch(r'(?:\d+(?:\.\d+)?\s*[dhms]\s*)+', text.lower()):
        return None
    parts = re.findall(r'(\d+(?:\.\d+)?)\s*([dhms])', text.lower())
    if not parts:
        return None
    factors = {'d':Decimal(24),'h':Decimal(1),'m':Decimal(1)/60,'s':Decimal(1)/3600}
    return sum((decimal(v) * factors[u] for v,u in parts), Decimal(0))


def gcode_metadata(text, name='Placa 1'):
    # Only comment lines are considered. Commands have no effect and are ignored.
    comments = '\n'.join(line[:4096] for line in text.splitlines() if line.lstrip().startswith(';'))
    weights = re.findall(r'filament (?:used \[g\]|weight \[g\])\s*[:=]\s*([\d.,; ]+)', comments, re.I)
    colors = []
    if weights:
        values = re.split(r'[,;]\s*', weights[-1].strip())
        colors = [{'label':f'Filamento {i+1}','grams':str(decimal(v))} for i,v in enumerate(values) if v.strip()]
    time = re.search(r'estimated printing time[^=\n]*=\s*([^\n]+)', comments, re.I)
    hours = duration(time.group(1)) if time else None
    if hours is None:
        sec = re.search(r'^;\s*TIME\s*:\s*(\d+(?:\.\d+)?)', comments, re.M | re.I)
        hours = duration(sec.group(1)) if sec else None
    if not colors and hours is None:
        return None
    return {'name':name,'hours':str(hours) if hours is not None else None,'colors':colors}


def read_slicing(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise ValueError('Arquivo excede 128 MB.')
    if path.suffix.lower() in ('.gcode', '.gco'):
        result = gcode_metadata(path.read_text(encoding='utf-8',errors='replace'))
        if result:
            return [result]
        raise ValueError('G-code sem metadados compatíveis de peso/tempo. Não é possível inferir consumo de comandos.')
    if path.suffix.lower() != '.3mf':
        raise ValueError('Selecione um 3MF fatiado ou G-code.')
    plates = {}
    try:
        with ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > 4096 or sum(i.file_size for i in infos) > 512*1024*1024:
                raise ValueError('Estrutura compactada excede limites.')
            for info in infos:
                p = PurePosixPath(info.filename.replace('\\','/'))
                if p.is_absolute() or '..' in p.parts or info.flag_bits & 1:
                    raise ValueError('Caminho inseguro ou conteúdo criptografado no 3MF.')
            for info in infos:
                if info.filename.lower().endswith('slice_info.config'):
                    if info.file_size > MAX_XML:
                        raise ValueError('XML de metadados excede 8 MB.')
                    root = fromstring(z.read(info), forbid_dtd=True, forbid_entities=True, forbid_external=True)
                    for index, plate in enumerate(root.iter('plate'),1):
                        meta = {m.get('key'):m.get('value') for m in plate.findall('metadata')}
                        key = meta.get('index',str(index))
                        hours = duration(meta.get('prediction',''))
                        colors = []
                        for f in plate.iter('filament'):
                            grams = f.get('used_g')
                            if grams is not None:
                                label = ' / '.join(x for x in (f.get('type'),f.get('color'),f.get('id')) if x)
                                colors.append({'label':label or 'Filamento','grams':str(decimal(grams))})
                        if colors or hours is not None:
                            plates[key] = {'name':f'Placa {key}','hours':str(hours) if hours is not None else None,'colors':colors}
            for info in infos:
                match = re.search(r'plate_(\d+)\.gcode$', info.filename, re.I)
                if match and match.group(1) not in plates:
                    if info.file_size > MAX_FILE:
                        raise ValueError('G-code interno excede limite.')
                    plate = gcode_metadata(z.read(info).decode('utf-8',errors='replace'), f'Placa {match.group(1)}')
                    if plate:
                        plates[match.group(1)] = plate
    except BadZipFile:
        raise ValueError('3MF não é um arquivo ZIP válido.') from None
    if not plates:
        raise ValueError('3MF sem metadados de fatiamento Bambu/Orca compatíveis. Um modelo geométrico não informa peso nem tempo confiáveis.')
    return list(plates.values())


def per_unit(plate, units):
    units = quantity(units)
    return {'name':plate['name'], 'hours':str(decimal(plate['hours'])/units) if plate['hours'] is not None else None,
            'colors':[{'label':c['label'],'grams':str(decimal(c['grams'])/units)} for c in plate['colors']]}
