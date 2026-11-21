"""Orçamento por metadados, sem cadastrar produtos ou materiais."""
from .numbers import cents,decimal
from .pricing import calculate
from .printers import profiles


def quote_project(erp,recipe,colors,packaging,other,printer='custom'):
    config=erp.s.settings();product={'weight':'0','hours':recipe['hours'] or '0','manual_cents':None,'packaging_cents':cents(packaging),'other_cents':cents(other)}
    if printer!='custom':
        profile=profiles(erp.s).get(printer)
        if not profile:raise ValueError('Perfil de impressora inválido.')
        product.update(_power_w=profile['power_w'],_machine_hour=profile['machine_hour'])
    checked=[]
    for color in colors:
        if not color['material'].strip() or not color['color'].strip():raise ValueError('Informe material e cor.')
        checked.append({**color,'grams':str(decimal(color['grams'])),'kg_cents':cents(color['kg']),'filament_id':None})
    result=calculate(product,checked,config)
    if recipe['hours'] is None and 'tempo ausente' not in result['missing']:result['missing'].append('tempo ausente')
    return result
