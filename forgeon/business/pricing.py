from decimal import Decimal, ROUND_HALF_UP
from .numbers import decimal, cents


def round_cents(value):
    return int((value * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def calculate(product, colors, settings):
    grams = sum((decimal(c['grams'], 'Gramas') for c in colors), Decimal(0)) if colors else decimal(product['weight'], 'Peso')
    hours = decimal(product['hours'], 'Horas')
    material = sum((decimal(c['grams']) / 1000 * Decimal(c['kg_cents']) / 100 for c in colors), Decimal(0)) if colors else grams / 1000 * decimal(settings['filament_kg'])
    energy = hours * decimal(settings['power_w']) / 1000 * decimal(settings['energy_kwh'])
    machine = hours * decimal(settings['machine_hour'])
    manufacture = Decimal(product['manual_cents']) / 100 if product['manual_cents'] is not None else material + energy + machine
    total = manufacture + Decimal(product['packaging_cents'] + product['other_cents']) / 100
    rate = decimal(settings['fee_percent'], 'Taxa percentual') / 100
    profit = decimal(settings['profit_percent'], 'Margem/acréscimo') / 100
    fixed = decimal(settings['fee_fixed'], 'Taxa fixa')
    mode = settings['pricing_mode']
    if rate >= 1 or (mode == 'margem' and rate + profit >= 1):
        raise ValueError('Taxas + margem devem ser inferiores a 100%; taxa isolada também.')
    if mode not in ('margem', 'acrescimo'):
        raise ValueError('Modo de precificação inválido.')
    suggested = (total + fixed) / (1 - rate - profit) if mode == 'margem' else (total * (1 + profit) + fixed) / (1 - rate)
    missing = []
    if grams == 0:
        missing.append('peso ausente')
    if hours == 0 and product['manual_cents'] is None:
        missing.append('tempo ausente')
    if total == 0:
        missing.append('custo zero')
    return {'grams': str(grams), 'hours': str(hours), 'material_cents': round_cents(material), 'energy_cents': round_cents(energy),
            'machine_cents': round_cents(machine), 'manufacture_cents': round_cents(manufacture), 'manual': product['manual_cents'] is not None,
            'packaging_cents': product['packaging_cents'], 'other_cents': product['other_cents'], 'total_cents': round_cents(total),
            'suggested_cents': round_cents(suggested), 'fees_cents': round_cents(suggested * rate + fixed),
            'profit_cents': round_cents(suggested * (1 - rate) - fixed - total), 'missing': missing,
            'colors': [{'filament_id': c['filament_id'], 'material': c['material'], 'color': c['color'], 'grams': c['grams']} for c in colors]}
