# HF06 — Simplificação e custos editáveis — 2.0.6

## Resultado da revisão

| Situação encontrada | Ajuste |
|---|---|
| Dezesseis opções competiam no menu lateral | Oito áreas, com subabas por tarefa. As ferramentas continuam disponíveis. |
| Custos apareciam em Precificação e Configurações; o editor ficava longe do cálculo | Um editor em Precificação. Ajustes mantém preferências, backup, aparência, SKU e atualização. |
| Catálogo repetido ocupava a base da precificação | Comparação de produtos abre sob demanda, no botão Comparar produtos. |
| Leitura do fatiador repetida em Materiais | Cadastro central em Produtos; Materiais oferece acesso ao cadastro principal. |
| Ações de lote/estorno apareciam em subabas incompatíveis | Botões de etapa/previsão só em Lotes; estorno só em Perdas. |
| Exportação de Pedidos levava itens fora dos filtros | Itens exportados usam o mesmo período, produto e material/cor. |
| Perdas e vínculos de repasses ignoravam parte dos filtros | Perdas seguem seu período e filtros de pedido/produto/etapa/filamento; vínculos seguem recebimentos/pedido/referência. |
| Material e cor podiam corresponder a filamentos diferentes do produto | A combinação precisa existir no mesmo filamento. |
| Controles podiam se sobrepor em janelas menores | Conteúdo com rolagem e tabelas com altura mínima; Como usar permanece no topo. |

## Onde encontrar

| Área | Subabas |
|---|---|
| Início | Painel; Pendências |
| Produtos | Cadastro; Anúncios e SKUs |
| Precificação | Custo e preço; Simular cenário |
| Materiais | Cores e preços/kg; Estoque |
| Vendas | Pedidos; Importar |
| Produção | Lotes, Necessidades, Perdas e reimpressões |
| Financeiro | Lançamentos; Repasses; Relatórios |
| Ajustes | Preferências e backup; Atualizações |

A área lembra a última subaba usada enquanto o ERP estiver aberto. Atalhos e abertura de pendências continuam levando ao cadastro correto. Ajuda local disponível no canto das telas e por F1.

## Atualizar custos sem reescrever vendas

Em **Precificação → Custo e preço → Editar custos e taxas**, revise energia por kWh, potência, máquina por hora, referência padrão de filamento, taxas e margem/acréscimo. **Editar produto** abre embalagem, outros custos, peso, tempo e fabricação manual. Cada edição confirmada de parâmetros registra a data da revisão. Custo manual continua substituindo material + energia + máquina, não se somando a eles.

Em **Materiais → Cores e preços/kg**, compare:

- **Referência editável/kg:** valor usado nas novas estimativas do catálogo.
- **Última compra/kg:** custo efetivamente registrado na compra de data mais recente, incluindo frete e convertido pelo peso comprado.
- **Data da compra** e **Revisado em:** origem e momento da revisão. Referências antigas sem registro de revisão não recebem uma data inventada.

Exemplo: 500 g por R$ 60,00 + R$ 10,00 de frete equivalem a **R$ 140,00/kg**. Para usar esse valor, selecione o material e confirme **Usar preço da última compra**. A ação faz backup antes da alteração e mantém a referência à compra na auditoria. Compras não alteram preços automaticamente. Pode editar o preço por kg novamente depois.

Não foram informados novos valores reais de energia, máquina, filamento ou contrato de taxas nesta solicitação. Valores existentes continuam referências editáveis, sem promessa de preço de mercado atualizado. O usuário precisa confirmar suas tarifas e preços pagos. Nem taxas de marketplace nem tarifas de energia são presumidas atuais pelo programa.

Custos já congelados nos pedidos e receitas dos lotes existentes são preservados. Atualizar o catálogo não prova o custo histórico de uma venda. Um lote ainda não iniciado pode revisar a previsão pelo fluxo próprio em Produção. Simular cenário não grava no cadastro.

## Filtros

- **Datas:** deixe vazio para todo o histórico ou escolha mês atual, anterior, quinzena ou intervalo personalizado. Datas DD/MM/AAAA ou AAAA-MM-DD. Final anterior ao início é recusado.
- **Pedidos:** período da venda, produto, material, cor, busca por ID/SKU/anúncio/variação e status específico. Filtros de item selecionam pedidos que contenham o item; totais do pedido permanecem completos. A planilha de itens leva somente o recorte selecionado.
- **Produtos e precificação:** material/cor filtram os produtos físicos. A comparação usa o mesmo filtro. Não há filtro de data de criação para cadastros que nunca armazenaram essa data.
- **Materiais:** material/cor filtram preços e composições dos produtos.
- **Produção:** data de criação no lote, data de ocorrência na perda, pedido, produto, material/cor e etapa. Perdas sem lote só aparecem quando os filtros não exigem vínculo/etapa/produto. Exportação segue as três tabelas exibidas.
- **Estoque:** datas filtram entrada de rolos e movimentações. Saldos, reservas e faltas são sempre atuais, sem representar saldo histórico. Material/cor e busca filtram todas as subabas.
- **Lançamentos:** data, descrição/categoria e material/cor para compras. Despesas gerais não têm filamento e ficam fora quando há filtro de material/cor; limpe esse filtro para vê-las novamente.
- **Repasses:** períodos independentes de recebimentos e pedidos, referência/observação e ID do pedido. A lista de vínculos segue as datas de recebimentos e o mesmo recorte de referência/pedido. A conciliação usa o período de pedidos e pode incluir recebimentos posteriores; não é saldo bancário.
- **Relatórios:** pedido/ID além de SKU, variação, produto, status, material/cor e cobertura. Filtros salvos lembram também as datas. Histórico mensal e desempenho continuam gerais conforme indicado na tela; despesas, compras e repasses não são atribuídos a uma cor.
- **Simular cenário:** datas selecionam vendas usadas na referência de preço médio. Custo base continua sendo o atual do cadastro, não uma reconstrução do custo na data filtrada.

Clique Aplicar filtros/Consultar depois de mudar campos. Busca principal e seletores já existentes continuam atualizando a tela quando usados. Limpar remove o recorte adicional. Conteúdo do filtro fica na tela durante a sessão; filtros de Relatórios podem ser salvos com nome.

## Atualizar

Pacote cumulativo. Faça backup, feche o ERP e instale o Setup na mesma conta e pasta. Não precisa desinstalar nem apagar dados. O esquema continua 3; referências, preferências e auditoria usam as tabelas existentes. Gestão local funciona sem internet; consulta/download de hotfix é uma ação explícita.
