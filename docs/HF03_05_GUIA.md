# HF03, HF04 e HF05 — pacote cumulativo 2.0.5

Instale uma vez sobre a versão atual, com o ERP fechado e na mesma conta/pasta. Não exclua a pasta dos dados. O instalador mantém `%LOCALAPPDATA%\ForgeonStudioERP2`; ao abrir um banco do esquema 1 ou 2, o aplicativo cria backup antes de migrar ao esquema 3. Faça também uma cópia externa em Configurações. Backups antigos são convertidos em estágio durante a restauração; o arquivo de origem permanece intacto. Voltar a uma versão antiga exige restaurar um backup compatível, não abrir o banco convertido no programa antigo.

## Ajuda e organização

Cada uma das 16 abas tem um pequeno **ⓘ Como usar** no canto superior direito. Subabas têm **ⓘ** próprio. Tudo funciona localmente, sem internet. F1 abre ajuda da aba principal; Ctrl+F busca produto/pedido/SKU/variação, Ctrl+N abre cadastro manual e Ctrl+I importa pedidos.

Em **Pendências**, filtre o tipo ou busque uma referência e abra o cadastro correspondente. Revisão de vínculos em lote exige escolher produtos explicitamente; não há união por semelhança. A operação tem backup e transação única; custos já congelados permanecem preservados.

Antes de importar pedidos, confira a comparação de IDs novos/alterados/sem alteração comercial e o aviso de arquivo já importado. Ela compara data/status/receita/taxas/reembolso e itens/quantidades/preços, não todos os campos auxiliares. Arquivos parciais não apagam IDs ausentes. A última prévia detalhada ainda precisa de confirmação antes de gravar.

Relatórios possuem filtros por SKU, variação, material, cor e cobertura das receitas, além de produto, status e datas. Salve combinações com nome. Botões de mês/quinzena usam o mês da data inicial. Cor/material selecionam itens que usam o filamento: não atribuem receita a uma cor. Despesas, compras e repasses permanecem gerais do período; perdas têm filtro de período/produto, sem rateio por SKU/cor/status. Histórico mensal é geral; Desempenho usa o período geral sem os filtros adicionais. PDF identifica os filtros; XLSX mantém os dados separados em abas.

Tabelas lembram colunas ocultas, ordem e largura. Botão direito no cabeçalho escolhe colunas; botão direito na tabela copia/exporta as visíveis ou mostra todas novamente. Preferências ficam no banco local e acompanham o backup.

## Produção e estoque

1. Complete o cadastro do produto com tempo, cores/gramas por unidade e preços de referência.
2. Em Estoque, cadastre o saldo restante **medido** dos rolos existentes. Compras novas no Financeiro geram rolos automaticamente; compras anteriores à atualização não são presumidas em estoque.
3. Em Produção, sincronize pedidos **A Enviar** com produto reconhecido ou crie lote avulso. Repetir a sincronização não duplica o mesmo item.
4. Confira necessidades agrupadas e reservas no Estoque. A reserva não baixa massa. Sem receita/cor, parte da previsão ficará pendente.
5. Atualize etapas. Ao confirmar **Pronto**, o sistema valida a receita e o saldo de todas as cores, então baixa uma única vez; se faltar uma cor, nenhuma baixa parcial é gravada. A alocação de massa usa os rolos mais antigos.
6. Pedido cancelado, quantidade ou produto alterado exigem revisão. Lote não iniciado e sem eventos pode atualizar a previsão; lote baixado não volta de etapa. Cancelar não retorna material já consumido.
7. Registre perdas/reimpressões adicionais com motivo, gramas e horas extras. Se a massa já tiver sido baixada, escolha a opção correspondente. O estorno conserva o evento e devolve somente seus próprios movimentos.

O custo adicional das perdas usa material de referência + energia/máquina nas horas extras e reduz o resultado operacional. Não é uma segunda compra nem nova saída de caixa; não duplique o mesmo custo em Despesas. Custos dos pedidos permanecem congelados. Uma reimpressão extra deve registrar apenas o consumo adicional, sem repetir o lote normal já baixado.

Editar/excluir uma compra financeira não recalcula massa já consumida nem troca material do rolo: revise o estoque e faça ajuste físico com motivo. O vínculo financeiro pode ficar vazio após excluir a compra, preservando a rastreabilidade física. Cadastro/ajuste de rolo isolado não cria compra/despesa.

Lote avulso não cria venda nem contabiliza estoque de produtos acabados. O controle é de massa operacional, sem sensores, integração de impressora, inventário fiscal ou custo médio contábil. Valor de referência não é custo FIFO contábil. Histórico das receitas começa nesta versão; não inventa revisões anteriores. Alterações globais de preço por kg são registradas no histórico de operações, não geram revisão em todos os produtos.

## Simulação, desempenho e repasses

**Simulador** testa filamento, embalagem, outros custos, energia, máquina, taxas e margem/acréscimo em memória, sem alterar cadastro/configurações. Fabricação manual substitui material/energia/máquina. Cenário é temporário; exporte se quiser guardá-lo. Preço médio dos itens observados é anterior a cupons do pedido; projeção com taxas simuladas não é margem histórica.

**Desempenho de produtos**, em Relatórios, mostra contribuição antes das despesas gerais e contribuição por hora conhecida, com pendências visíveis. Não equivale a lucro líquido; custos ausentes não são presumidos completos.

**Repasses** registra depósitos líquidos efetivamente recebidos, com referência única. Vincule parcelas a pedidos; um repasse pode cobrir vários pedidos e um pedido pode receber vários repasses. A soma dos vínculos não pode ultrapassar o recebimento. Repetir o mesmo par atualiza a alocação. Diferenças para receita menos taxas/reembolso exigem revisão, não correção automática das vendas.

Importe o `modelo_repasses.xlsx` gerado em **Modelos**. Data, Referência e Valor recebido R$ são obrigatórios. Pedido ID e Valor vinculado R$ são opcionais em conjunto. Para várias linhas do mesmo repasse, repita data/total e varie o pedido; não divida o total do repasse entre linhas. Referência atualiza sem duplicar; vínculos ausentes no arquivo não são excluídos. Fórmulas não são aceitas; prévia e backup antecedem a gravação.

Datas de recebimentos e pedidos têm filtros independentes. Conciliação considera os vínculos de todo o histórico; a terceira subaba mostra todos eles. Valores recebidos são totalizados pela data do depósito, nunca somados de novo às vendas. **Recebimentos menos despesas e compras** usa depósitos líquidos, sem descontar taxas retidas novamente; continua sem saldo inicial e sem todos os movimentos bancários.

## Aparência e diagnóstico

Configurações → Aparência: fonte 12–18 px, contraste, opacidade dos painéis 60–100% e menu mais estreito. Modo foco continua disponível na lateral. A paisagem fica atrás dos painéis; textos e números permanecem nítidos.

Exportar diagnóstico salva JSON apenas no caminho escolhido, com versões, integridade, quantidades de registros e contagem de tipos de operação. Não inclui nomes de produtos, SKUs, caminhos pessoais, dados de compradores ou detalhes da auditoria. Nada é enviado automaticamente.
