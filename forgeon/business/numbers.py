from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, date
import unicodedata


def decimal(value, label='Valor', maximum='1000000000'):
    try:
        s = str(value).strip().replace('R$', '').replace(' ', '')
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label}: número inválido.') from None
    if not d.is_finite() or d < 0 or d > Decimal(maximum):
        raise ValueError(f'{label}: informe número finito entre 0 e {maximum}.')
    return d


def cents(value):
    return int((decimal(value) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def money(value):
    return f'R$ {Decimal(value) / 100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).lower().split())


def day(value):
    if isinstance(value, (date, datetime)):
        return value.strftime('%Y-%m-%d')
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    raise ValueError(f'Data inválida: {value}. Use DD/MM/AAAA.')


def quantity(value):
    d = decimal(value, 'Quantidade', '1000000')
    if d < 1 or d != d.to_integral_value():
        raise ValueError('Quantidade deve ser inteira e positiva.')
    return int(d)
