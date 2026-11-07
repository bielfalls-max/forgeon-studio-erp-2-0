# HF02 · Produção — versão 2.0.2

## Fluxo recomendado

1. **Produtos → Cadastrar via 3MF / G-code**. Escolha um arquivo fatiado, selecione as placas do mesmo produto e informe quantos produtos COMPLETOS elas rendem. Um boneco pode ter dezenas de peças divididas entre várias placas; peças não são unidades vendidas.
2. Confira nome físico, modelo/tamanho, cores, material, gramas e duração. Revise R$/kg, embalagem e outros custos. O preço por kg vem do cadastro/padrão local: não se presume a moeda de custos gravados pelo fatiador.
3. Confirme e salve. O produto entra na tabela com suas colunas, no painel de receita e na **Precificação**, que usa os parâmetros configurados de energia, máquina, taxas e margem.
4. **Importações → Pedidos Shopee XLSX**. Aba e cabeçalho são identificados em arquivos de uma aba. Revise o mapeamento e a prévia; os campos de compradores não são mapeados nem persistidos.
5. O período é identificado pelas datas dos pedidos e, quando compatível, pelo intervalo do nome do arquivo. O relatório abre no período importado. `Order.all` até parte do mês ainda é cobertura parcial do mês; `Order.toship` cobre somente A Enviar.
6. Em **Valores por pedido** e **Itens · gramas e horas**, confira receitas, taxas, pesos, tempo, quantidades e custo congelado. A visão geral mostra o consumo estimado conhecido por pedido e por cor, com unidades sem receita sinalizadas.
7. Revise origens pendentes em **Catálogo e SKUs**. Se cadastrar uma receita depois de importar os pedidos, vínculos unívocos por variação exata são resolvidos e custos pendentes completos recebem valor/data atuais. Não são custos históricos comprovados da data antiga da venda.

## Identificação de produtos

A variação tem prioridade sobre o título genérico do anúncio. Um anúncio com um personagem no título pode vender outro personagem em uma variação. O SKU principal do anúncio não identifica cada variação e não é usado como substituto de um SKU vazio.

A ligação automática exige uma correspondência exata e única após normalizações cosméticas limitadas (acentos/caixa, separação CamelCase, sufixo “- Hedgehog”, repetição idêntica separada por vírgula). Se houver modelo/tamanho, o nome completo com modelo deve corresponder. Não há busca por trecho, fusão de produtos ou aplicação de uma receita a variantes diferentes de cor. Ambiguidades ficam pendentes. O mesmo SKU em produtos diferentes é um conflito para revisão, não uma razão para unir cadastros.

## Bases financeiras das planilhas

- **Receita dos produtos**: soma do Subtotal do produto, que já considera o Preço acordado, menos Cupom do vendedor e cashback/moedas financiados pelo vendedor quando identificados em reais. Sem subtotais, usa o total de produtos mapeado ou estima preço unitário × quantidade com aviso de parcialidade.
- **Taxas**: comissão líquida + serviço líquido + transação, ou a coluna de taxas totais explicitamente mapeada. São valores por pedido. Brutas permanecem referências de origem, não são somadas junto às líquidas.
- **Após taxas/reembolsos**: receita dos produtos menos taxas e reembolso efetivo. Ainda não desconta produção e despesas; não é repasse observado.
- **Valor Total**, **frete pago pelo comprador** e **Total global**: referências separadas, preservadas por pedido. Podem incluir frete, moedas e critérios próprios do marketplace. Não são tratados como segunda receita nem como saldo bancário/repasse líquido comprovado.
- Não se desconta novamente “Desconto do vendedor” de preço, pois a diferença já está no Preço acordado/Subtotal. Cabeçalhos repetidos são diferenciados, sem somar a mesma coluna duas vezes.
- Solicitações de devolução/quantidades devolvidas sem reembolso informado geram dados parciais; não se inventa o valor devolvido.

É necessário que o arquivo contenha TODOS os itens de cada ID incluído. Quando “Número de produtos pedidos” estiver disponível, a soma das quantidades é conferida. Arquivos parciais preservam os demais pedidos do banco, e reimportar não duplica o mesmo pedido.

## Consumo e histórico

A estimativa é receita de impressão por unidade × quantidade. O painel separa a previsão dos pedidos ainda não enviados da estimativa dos enviados/entregues/devolvidos. Cancelados não entram no consumo gerencial; perdas de impressão de pedidos cancelados devem ser lançadas separadamente. Sem leitura de impressora, não há como comprovar filamento fisicamente consumido.

A receita importada inclui suportes/expurgo que o fatiador informar; não representa necessariamente o peso final do objeto. Se faltar metadado, o aplicativo informa pendência. Cores/tempo são preservados em snapshots de uso; custos completos são congelados com data e composição. Alterações posteriores do produto não reescrevem os registros já congelados.

## Atualização do banco

O esquema 1 das entregas 2.0.0/2.0.1 passa para esquema 2, com três tabelas adicionais: `product_slices`, `item_usage` e `order_financials`. Tabelas de produtos/pedidos anteriores permanecem intactas. Antes da conversão de um banco existente, a API SQLite gera um backup consistente na pasta de backups. Nenhuma instalação de versões antigas de outros projetos Forgeon é lida.

Faça também seu próprio backup antes de atualizar. Não abra o banco convertido com um executável mais antigo; preserve o backup de esquema 1 se precisar voltar à versão anterior. Restauração pelo HF02 valida identidade, esquema, integridade e chaves; um backup de esquema 1 deste projeto é convertido em cópia temporária, sem modificar o arquivo de origem, antes de substituir o banco atual.
