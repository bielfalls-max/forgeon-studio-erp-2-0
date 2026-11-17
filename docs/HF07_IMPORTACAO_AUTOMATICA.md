# HF07 — Importar e preencher o ERP — 2.0.8

Em **Vendas → Importar → Importar planilhas · automático**, selecione o arquivo de pedidos, o resumo gerencial Shopee ou os dois juntos. O aplicativo reconhece abas, cabeçalhos e períodos, mostra uma prévia única e só grava após Confirmar importação. Não é necessário selecionar cada aba ou mapear cada coluna nos formatos reconhecidos.

O resultado preenche o painel, o histórico mensal e os relatórios que já existem. Não foi criada outra área ou aba para gerenciar planilhas. Pequenos campos adicionais no resultado e nos valores por pedido mostram o valor depois da produção.

## Origem dos campos

| Campo do ERP | Informação usada |
|---|---|
| Pedidos, itens, quantidades, SKU/variação e datas | Exportação detalhada Order.all |
| Receita dos produtos | Subtotais dos itens menos cupom/moedas financiados pelo vendedor; cancelados excluídos |
| Taxas efetivas | Total ou componentes líquidos por pedido, contados uma vez |
| Gramas por material/cor e horas | Receita do produto vinculado × quantidade não cancelada |
| Custo de produção | Material + energia + máquina, ou fabricação manual substitutiva, somando embalagem e outros custos por unidade |
| Após taxas e produção completa | Receita − taxas − reembolsos − produção − perdas adicionais; pendente se faltar custo ou cobertura necessária |
| Resultado operacional | Valor anterior menos despesas gerais do período, sem descontar de novo a compra do filamento |
| Valores por pedido | Taxas/reembolso, produção da receita e valor após essa produção; perdas adicionais ficam no resultado geral |
| Indicadores mensais gerenciais | Linhas mensais/diárias de Pedido Feito e Produto Pago, separadas por base |
| Recebimentos reais | Repasses informados pelo usuário; não são criados por estas planilhas |

As planilhas de vendas/resumo não informam o consumo de filamento nem todo o custo de fabricar cada produto. Se faltar cadastro, vínculo, gramas, tempo ou custo, complete o produto/receita em Produtos e Precificação. O ERP não presume custo zero nem inventa lucro definitivo. Tarifas, energia, máquina, embalagem e outros custos continuam editáveis nos campos existentes.

## Como os arquivos se complementam sem repetir vendas

Pedidos detalhados são a fonte operacional: total e taxas pertencem ao pedido, não são multiplicados pelos itens. Cada ID/item atualiza o registro correspondente. Reimportar o mesmo arquivo ou importar um intervalo que contém IDs já conhecidos não adiciona a mesma venda novamente. Custos e receitas já congelados nos itens são preservados.

O resumo gerencial fornece indicadores por mês. Pedido Feito e Produto Pago são critérios diferentes; nunca se somam entre si. O total anual/do intervalo é armazenado separado das linhas mensais/diárias e não é somado novamente a elas. A comparação usa os subtotais antes de excluir cancelados, coerentes com o resumo de pedidos feitos; a receita operacional continua excluindo cancelados. Pagamento do comprador não comprova depósito à loja.

Dados de meses diferentes não são forçados a conferir. Um resumo de janeiro a outubro pode complementar pedidos de outubro; pedidos importados de novembro alimentam novembro sem serem comparados diretamente ao total de janeiro a outubro. Sem detalhes de janeiro a setembro, não se calculam gramas/custos/profit desse período como se os pedidos estivessem disponíveis.

A comparação por pagamento usa a data de pagamento disponível. Pode haver pedidos criados em outro intervalo, então igualdade numa amostra não prova cobertura completa de todos os pagamentos. Diferenças não ajustam vendas ou custos automaticamente.

O histórico mensal mostra as referências informadas e a receita dos pedidos lado a lado. Em mês com apenas resumo, o painel identifica essa origem e mantém o resultado de produção pendente. Exportações deixam explícitas as bases para não somar referências como novas receitas.

## Proteções

- Uma confirmação, um backup e uma transação para os arquivos selecionados. Qualquer falha reverte todo o conjunto.
- Se o mesmo ID tiver informações conflitantes entre arquivos selecionados, importe somente o arquivo mais recente correspondente; não há escolha arbitrária.
- Resumo parcial não substitui uma linha mensal que já cobre mais dias. Uma cobertura mais completa pode substituir a parcial sem se somar a ela.
- Fórmulas são recusadas; leitura e estruturas XLSX têm limites. O arquivo é tratado como dados.
- CPF, telefone, endereço, destinatário e dados de compradores não são mapeados para o banco nem para a prévia detalhada.
- Mapeamento manual permanece no modo avançado para arquivos não reconhecidos.
- A atualização preserva dados/backups; o esquema 4 acrescenta indicadores gerenciais e cobertura das importações. Scripts de esquemas publicados anteriormente permanecem preservados.

Instale o hotfix com o ERP fechado, após criar backup, na mesma conta/pasta. Não precisa apagar dados ou desinstalar. Gestão local funciona sem internet.
