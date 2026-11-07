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
    if not colors:
        total_weight=re.search(r'total filament weight \[g\]\s*[:=]\s*([0-9.]+)',comments,re.I)
        if total_weight:
            ids=re.search(r'^;\s*filament\s*:\s*(\d+)\s*$',comments,re.M|re.I)
            color_list=re.search(r'^;\s*filament_colour\s*=\s*([^\n]+)',comments,re.M|re.I)
            material_list=re.search(r'^;\s*filament_type\s*=\s*([^\n]+)',comments,re.M|re.I)
            if ids:
                slot=int(ids.group(1))-1
                palette=color_list.group(1).split(';') if color_list else []
                materials=re.split('[;,]',material_list.group(1)) if material_list else []
                color=palette[slot].strip() if 0<=slot<len(palette) else ''
                material=materials[slot].strip() if 0<=slot<len(materials) else 'PLA'
                colors=[{'label':color or f'Filamento {slot+1}','hex':color,'material':material,'grams':str(decimal(total_weight.group(1)))}]
    time = re.search(r'estimated printing time[^=\n]*=\s*([^\n]+)', comments, re.I)
    hours = duration(time.group(1)) if time else None
    if hours is None:
        total=re.search(r'total estimated time\s*[:=]\s*([^;\n]+)',comments,re.I)
        hours=duration(total.group(1)) if total else None
    if hours is None:
        sec = re.search(r'^;\s*TIME\s*:\s*(\d+(?:\.\d+)?)', comments, re.M | re.I)
        hours = duration(sec.group(1)) if sec else None
    if not colors and hours is None:
        return None
    return {'name':name,'hours':str(hours) if hours is not None else None,'colors':colors,'object_count':None}


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
            if len({i.filename for i in infos})!=len(infos):raise ValueError('3MF com caminhos repetidos.')
            plate_names={}
            for info in infos:
                if info.filename.lower().endswith('model_settings.config') and info.file_size<=MAX_XML:
                    config=fromstring(z.read(info),forbid_dtd=True,forbid_entities=True,forbid_external=True)
                    for plate in config.iter('plate'):
                        meta={m.get('key'):m.get('value') for m in plate.findall('metadata')}
                        plate_names[meta.get('plater_id','')]=meta.get('plater_name','')
            for info in infos:
                p = PurePosixPath(info.filename.replace('\\','/'))
                if p.is_absolute() or '..' in p.parts or re.match(r'^[A-Za-z]:',str(p)) or info.flag_bits & 1:
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
                                colors.append({'label':label or 'Filamento','grams':str(decimal(grams)),'material':f.get('type') or 'PLA','hex':f.get('color') or '', 'filament_id':f.get('id') or ''})
                        if colors or hours is not None:
                            plates[key] = {'name':f"Placa {key}"+(' · '+plate_names[key] if plate_names.get(key) else ''),'index':key,'seconds':meta.get('prediction') if re.fullmatch(r'\d+(?:\.\d+)?',meta.get('prediction','')) else None,'hours':str(hours) if hours is not None else None,'colors':colors,'object_count':len([o for o in plate.findall('object') if o.get('skipped')!='true'])}
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
            'colors':[{**c,'grams':str(decimal(c['grams'])/units)} for c in plate['colors']]}


def suggested_name(path):
    name=Path(path).name
    while Path(name).suffix.lower() in ('.3mf','.gcode','.gco'):name=Path(name).stem
    return re.sub(r'([a-z])([A-Z])',r'\1 \2',name).replace('_',' ').strip()


def color_name(value):
    palette={'Prata':(166,169,170),'Preto':(0,0,0),'Branco':(255,255,255),'Azul':(40,80,224),'Vermelho':(193,46,31),'Amarelo':(244,238,42),'Verde':(40,150,50),'Dourado':(210,170,60)}
    if not re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?',value or ''):return value or 'Cor não identificada'
    rgb=tuple(int(value[i:i+2],16) for i in (1,3,5))
    label=min(palette,key=lambda key:sum((a-b)**2 for a,b in zip(rgb,palette[key])))
    return f'{label} ({value.upper()})'


def combine_plates(plates,selected,units=1,source_name=''):
    from collections import defaultdict
    units=quantity(units)
    if not selected:raise ValueError('Selecione ao menos uma placa.')
    if len(set(selected))!=len(selected) or any(i<0 or i>=len(plates) for i in selected):raise ValueError('Seleção de placas inválida.')
    groups={};seconds=Decimal(0);complete_time=True;warnings=[]
    for i in selected:
        plate=plates[i]
        if plate['hours'] is None:complete_time=False
        else:seconds+=decimal(plate['seconds']) if plate.get('seconds') is not None else decimal(plate['hours'])*3600
        for color in plate['colors']:
            material=color.get('material') or 'PLA';hex_color=color.get('hex') or ''
            label=color_name(hex_color) if hex_color else color['label']
            key=(material,label)
            if key not in groups:groups[key]={'material':material,'color':label,'hex':hex_color,'label':color['label'],'grams':Decimal(0)}
            groups[key]['grams']+=decimal(color['grams'])
    if not complete_time:warnings.append('Uma placa não informa tempo; preencha o tempo total manualmente antes de finalizar custos.')
    return {'name':suggested_name(source_name) if source_name else 'Produto','source_name':Path(source_name).name,'units':units,
            'plates':[plates[i]['name'] for i in selected], 'hours':str(seconds/3600/units) if complete_time else None,
            'colors':[{**c,'grams':str(c['grams']/units)} for c in groups.values()],'warnings':warnings}
