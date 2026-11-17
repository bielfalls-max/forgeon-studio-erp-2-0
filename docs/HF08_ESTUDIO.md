# HF08 — Gestão do estúdio — 2.0.9

## Fluxo diário

1. Importe o Order.all em Vendas. Pedidos e produtos são identificados automaticamente; no banco existente, origens sem produto recebem cadastro pendente ao abrir esta versão. O resumo anual sozinho não contém produtos ou receitas e não os inventa.
2. Em Produtos, abra o 3MF/G-code e escolha o produto existente no campo de destino para completar sua receita, em vez de criar outro produto. Revise placas, unidades completas, material/cor, gramas, horas e preço/kg. Produtos/receitas e custos históricos existentes são preservados.
3. Em Materiais → Compras e insumos, cadastre caixas, bolha, cola e consumíveis com quantidade, unidade, data, valor total e frete. Filamentos têm cadastro/compra próprios. Ferramentas/utensílios duráveis podem ser registrados como despesa pelo mesmo formulário ou por Despesa / utensílio.
4. Use Vincular consumo ao produto: por exemplo, 1 caixa, 0,5 metro de bolha, 2 gramas de cola por unidade vendida. O custo calculado soma ao campo Outros do produto. Remova valores manuais que já representem o mesmo insumo para não duplicar. Zero remove o vínculo.
5. Em Precificação, escolha o produto, confira custos e use Testar meu preço de venda. O diálogo mostra preço, custo completo, taxas configuradas, sobra por unidade e margem. O preço sugerido continua conforme a margem/acréscimo configurados. Receitas incompletas exigem preenchimento antes da simulação.
6. Financeiro abre nos gráficos, com filtros por período/produto para cada gráfico. Lançamentos, repasses e os detalhes dos relatórios ficam nas subabas existentes. Vendas sempre abre em Pedidos, mesmo depois de visitar Importar; filtre Em aberto / a enviar ou consulte os outros meses.

## Compras versus consumo

O relatório de caixa inclui a compra no mês da sua data, com frete. O custo operacional utiliza o consumo por unidade da receita do produto. A compra de um consumível não é descontada novamente como despesa operacional, porque seu consumo já compõe o custo de fabricação. Ferramenta durável lançada como despesa reduz resultado e caixa no mês uma única vez.

Exemplo: 10 caixas por R$ 20 + R$ 5 de frete custam R$ 2,50 por caixa. Com vínculo de uma caixa por produto, R$ 2,50 entram no custo unitário. Os R$ 25 da compra entram na saída de caixa no mês. Não são descontados também do resultado operacional como outra despesa.

Custos unitários de insumos guardam precisão abaixo de um centavo até multiplicar pelo consumo. Custo do produto é arredondado apenas ao final. A referência usa a compra de data mais recente; não é custo médio fiscal. Pedidos congelados não são recalculados quando uma compra nova altera a referência.

## Saldos e o que comprar

As sugestões são estimativas a partir das compras, vendas e receitas cadastradas. Para insumos, o sistema desconta o consumo estimado das vendas não canceladas já fora de aberto e calcula a necessidade dos pedidos abertos. Para filamentos, a composição vem das receitas/snapshots por cor. Sem receitas, o sistema avisa quantas unidades ainda não têm consumo conhecido.

É necessário cadastrar histórico/saldo coerente e conferir fisicamente. Não há leitura de sensores, inventário fiscal nem medição automática das perdas. Saldo negativo indica falta de informação/compra ou necessidade de revisão; não autoriza concluir que o estoque físico é negativo. Não lance uma compra novamente só para corrigir estoque: isso repetiria gasto financeiro.

## Organização

- Início: indicadores rápidos, consumo conhecido e pendências. Gráficos extensos ficam em Financeiro.
- Produção foi retirada do menu e sua antiga posição foi reaproveitada para Compras e insumos. Registros históricos de lotes/perdas permanecem no banco, sem novas baixas automáticas.
- Ajustes tem cartões para custos, backup/integridade, aparência, suporte e atualização.
- Produtos mantém o cadastro e o leitor do fatiador. Novos cadastros derivados de vendas começam com receita pendente, nunca com peso/tempo fictícios.

A atualização migra ao esquema 5 com backup prévio. Instale com o ERP fechado, na mesma conta/pasta. Não apague os dados.
