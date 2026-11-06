# Cálculos, histórico e cobertura

## Custo e preço

Todos os valores monetários persistidos usam centavos inteiros. Os cálculos usam `Decimal`, arredondando centavos com ROUND_HALF_UP. Pesos e horas são strings decimais no SQLite; não se usa ponto flutuante para dinheiro.

- Material sem cores: peso(g) ÷ 1000 × preço padrão por kg.
- Com cores: soma de gramas de cada filamento ÷ 1000 × seu preço por kg. O peso exibido é a soma.
- Energia: horas × potência(W) ÷ 1000 × preço do kWh.
- Máquina: horas × custo de uso por hora.
- Fabricação: material + energia + máquina, OU custo manual informado. O valor manual substitui os três, não é somado a eles.
- Total: fabricação + embalagem por unidade + outros custos por unidade.

Com `C` = custo total, `f` = taxa fixa, `t` = taxa proporcional, `m` = margem e `a` = acréscimo:

- Margem sobre venda: `P = (C + f) / (1 − t − m)`.
- Acréscimo sobre custo: `P = (C × (1 + a) + f) / (1 − t)`.

A margem é lucro/preço de venda. O acréscimo é lucro desejado/custo. A taxa fixa da sugestão é por unidade; pedidos usam taxas efetivas totais importadas. Valores negativos, não finitos, excessivos e denominadores inválidos são recusados. As taxas iniciais são zero e precisam de revisão pelo usuário; não representam condições atuais garantidas da Shopee.

## Histórico de custos

O primeiro congelamento completo do item grava custo unitário, material/energia/máquina, embalagem, outros, peso, tempo, consumo por cor e data do congelamento. Mudanças posteriores em produto, cor, preço por kg ou parâmetros não alteram esse registro. A reimportação preserva o registro se a chave do item não mudar.

Quando uma origem for corrigida para outro produto, o custo antigo continua congelado: a identificação pode mudar, mas não se reescreve o cálculo do passado. O histórico mostra a correção. Um custo que faltava poderá ser congelado explicitamente com o cadastro atual, registrando a data atual. Esse valor é uma estimativa registrada posteriormente, não uma evidência do custo praticado na data da venda. Consulte a coluna de data do congelamento.

## Resultado operacional

`vendas brutas dos pedidos não cancelados − reembolsos efetivos − taxas retidas − custos de produção congelados × quantidades − despesas`.

Compras de filamento não são despesas operacionais novamente: o consumo já compõe o custo de produção. Se houver custo manual, considera-se que ele já cobre a fabricação, inclusive material. Não lance uma compra de filamento também como despesa de fabricação, para não duplicar a saída gerencial.

## Caixa estimado

`vendas brutas − reembolsos − taxas − despesas − compras de filamento e frete`.

Esse indicador usa datas de pedidos e lançamentos, sem agenda de repasses e sem saldo inicial. Não inclui automaticamente saídas de embalagem, energia ou manutenção quando não lançadas. O custo de máquina é uma referência gerencial, não uma saída bancária observada. Portanto, o indicador não é saldo bancário nem fluxo de caixa conciliado. Para análise contábil, ajuste categorias e critérios com seu responsável contábil.

## Status, cancelamentos e devoluções

Status contendo “cancel” são cancelados; contendo “devol”, “reembols”, “return” ou “refund” são devoluções/reembolsos. Os demais são ativos, inclusive A Enviar. Isso é uma visão gerencial da carteira de pedidos; não implica liquidação ou reconhecimento contábil da receita. Use filtros e corrija status quando necessário.

Cancelados ficam fora de vendas, taxas e consumo do relatório. Se houve produção perdida ou taxa efetivamente retida em cancelamento, lance a perda/despesa separadamente. Devoluções mantêm custo e consumo de produção; não se presume que material ou produto voltaram ao estoque. Reembolso efetivo reduz receita. Taxas devem ser o valor efetivamente retido; não se presume devolução automática das taxas. Devolução com reembolso zero é sinalizada como parcial, até que o caso seja esclarecido.

## Filtros e estatísticas

Filtros por produto rateiam os valores do cabeçalho do pedido pelo valor bruto dos itens. Despesas e compras continuam sendo gerais do período: o resultado filtrado não é um lucro líquido isolado do produto. A aba Histórico mensal apresenta meses completos sem os filtros de produto/status; as outras abas usam os filtros selecionados. Quantidades de mais vendidos incluem unidades devolvidas, coerentemente com consumo de produção; não são unidades líquidas de devoluções.

O resumo mensal da loja fica separado. O total comparável soma somente períodos integralmente contidos no filtro; períodos cruzando as bordas aparecem na tabela, mas não são rateados. As linhas de resumo são por anúncio, e não por variante física. A contagem por anúncio não deve ser somada como pedidos únicos da loja. Remova linhas TOTAL antes de importar anúncios. Períodos sobrepostos para o mesmo anúncio são recusados. Reimporte a mesma chave anúncio+início+fim para corrigir valores; exclua uma linha incorreta na aba de estatísticas, com backup.

A diferença é `receita do resumo − vendas brutas dos pedidos`. As duas fontes podem seguir definições diferentes, datas diferentes ou status diferentes; igualdade não prova conciliação bancária. São marcados DADOS PARCIAIS: ausência de pedidos ou de resumo para comparação, arquivo parcial, total ou taxas não identificados, falta de custo, diferença entre fontes, devolução sem reembolso, filtro por produto/status e períodos de resumo incompatíveis com o filtro.

`Order.toship` representa apenas A Enviar, não todas as vendas do mês. Para maior cobertura, importe Todos os pedidos / Order.all. Estatísticas nunca são adicionadas como uma segunda venda e nunca completam os itens físicos desconhecidos.
