from ..business.numbers import decimal, cents, day


def prepare(rows, kind):
    result=[]
    for n,r in enumerate(rows,2):
        try:
            if kind=='produtos':
                name=str(r.get('Nome') or '').strip()
                if not name:
                    raise ValueError('Nome obrigatório.')
                result.append({'name':name,'model':str(r.get('Modelo') or ''), 'weight':str(decimal(r.get('Peso g') or 0)),
                    'hours':str(decimal(r.get('Horas') or 0)), 'manual_cents':None if r.get('Custo manual R$') in (None,'') else cents(r['Custo manual R$']),
                    'packaging_cents':cents(r.get('Embalagem R$') or 0),'other_cents':cents(r.get('Outros R$') or 0),'notes':str(r.get('Observações') or '')})
            elif kind=='despesas':
                cat=str(r.get('Categoria') or '').strip()
                if not cat:
                    raise ValueError('Categoria obrigatória.')
                result.append({'date':day(r.get('Data')),'category':cat,'description':str(r.get('Descrição') or ''),'amount_cents':cents(r.get('Valor R$'))})
            elif kind=='filamentos':
                mat,col=str(r.get('Material') or '').strip(),str(r.get('Cor') or '').strip()
                if not mat or not col:
                    raise ValueError('Material e cor obrigatórios.')
                result.append({'material':mat,'color':col,'kg_cents':cents(r.get('Preço kg R$'))})
            else:
                raise ValueError('Tipo de importação inválido.')
        except (ValueError,TypeError) as e:
            raise ValueError(f'Linha {n}: {e}') from None
    if not result:
        raise ValueError('Planilha sem registros.')
    return result


def commit(erp, rows, kind):
    statements = {
        'produtos':'INSERT INTO products(name,model,weight,hours,manual_cents,packaging_cents,other_cents,notes) VALUES(:name,:model,:weight,:hours,:manual_cents,:packaging_cents,:other_cents,:notes)',
        'despesas':'INSERT INTO expenses(date,category,description,amount_cents) VALUES(:date,:category,:description,:amount_cents)',
        'filamentos':'INSERT INTO filaments(material,color,kg_cents) VALUES(:material,:color,:kg_cents)'
    }
    backup=erp.s.backup()
    with erp.s.transaction():
        erp.s.db.executemany(statements[kind], rows)
        erp.s.log('importar_'+kind,{'registros':len(rows),'backup':backup.name})
    return backup
