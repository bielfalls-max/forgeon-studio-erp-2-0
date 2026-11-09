from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from ..business.numbers import money
from ..business.labels import LABELS
from datetime import datetime


def export(path, sheets):
    path = Path(path)
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title[:31])
        if not rows:
            ws.append(['Sem registros para este filtro.'])
            continue
        keys = list(rows[0])
        ws.append([LABELS.get(key,key) for key in keys])
        for row in rows:
            for col,key in enumerate(keys,1):
                value = row.get(key)
                if key.endswith('_cents') and value is not None:
                    value = money(value)
                if key in ('date','start','end') and isinstance(value,str):
                    try: value=datetime.strptime(value[:10],'%Y-%m-%d').strftime('%d/%m/%Y')+value[10:]
                    except ValueError: pass
                if isinstance(value, (dict,list)):
                    value = str(value)
                c = ws.cell(ws.max_row + 1 if col == 1 else ws.max_row, col)
                c.value = value
                if isinstance(value,str):
                    # Explicit string type prevents =,+,-,@ imported fields becoming formulas.
                    c.data_type = 's'
        for c in ws[1]:
            c.font = Font(color='FFFFFF',bold=True)
            c.fill = PatternFill('solid',fgColor='9B3327')
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        for i,key in enumerate(keys,1):
            ws.column_dimensions[get_column_letter(i)].width = min(48,max(18,len(key)+3))
    wb.save(path)
    return path


def templates(folder):
    folder = Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    definitions = {
        'pedidos': ['ID do pedido','Data','Status','Produto','Variação','SKU','Quantidade','Preço unitário','Total do pedido','Taxas totais','Reembolso'],
        'estatisticas': ['Anúncio','Receita','Pedidos'],
        'produtos': ['Nome','Modelo','Peso g','Horas','Custo manual R$','Embalagem R$','Outros R$','Observações'],
        'despesas': ['Data','Categoria','Descrição','Valor R$'],
        'repasses': ['Data','Referência','Valor recebido R$','Pedido ID','Valor vinculado R$'],
        'filamentos': ['Material','Cor','Preço kg R$'],
    }
    for name, headers in definitions.items():
        wb = Workbook()
        ws = wb.active
        ws.title = 'Dados'
        ws.append(headers)
        for col,h in enumerate(headers,1):
            ws.column_dimensions[get_column_letter(col)].width=25
            ws.cell(2,col).number_format='@'
        ws.freeze_panes='A2'
        instructions=wb.create_sheet('Instruções')
        instructions.append(['Preencha a aba Dados. Apague a linha vazia se necessário. Dinheiro em reais, peso em gramas, horas decimais.'])
        instructions.append(['SKUs e IDs como texto: preserve zeros. Datas DD/MM/AAAA. Sem fórmulas nem macros.'])
        instructions.append(['Pedidos: todos os itens de cada ID. Repita total e taxas do pedido em cada linha, sem ratear; o aplicativo conta uma vez.'])
        instructions.append(['Estatísticas: somente anúncios, sem linha TOTAL. Informe período na importação; resumo separado de pedidos.'])
        instructions.append(['Produtos e filamentos: novos cadastros; duplicidades devem ser revisadas na prévia. Use a tela para editar existentes.'])
        wb.save(folder/f'modelo_{name}.xlsx')
