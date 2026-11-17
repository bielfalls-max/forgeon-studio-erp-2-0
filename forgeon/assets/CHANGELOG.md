# Notas de atualização

## 2.0.9 — HF08 · Gestão do estúdio — 17/11/2026

- Produtos das vendas são cadastrados automaticamente com receita pendente; a importação não inventa gramas ou tempo. Banco existente recebe os cadastros faltantes ao abrir.
- Produção sai do menu; registros antigos são preservados. Sete áreas, Vendas sempre abre em Pedidos e Financeiro abre nos gráficos.
- Materiais recebe compras de caixas, bolha, cola e consumíveis com data, quantidade, valor e frete. Ferramentas/utensílios duráveis usam despesas.
- Vínculo de quantidade por produto soma insumos ao custo unitário; compras afetam caixa no mês, sem descontar novamente a compra no resultado operacional.
- Sugestões de compra estimadas para filamentos e insumos conforme pedidos abertos e dados cadastrados. Saldos estimados exigem histórico completo e conferência física.
- Financeiro com gráficos de vendas, custos, produtos e compras/despesas; cada gráfico tem filtro próprio. Início fica no resumo e pendências rápidas.
- Precificação com instruções em três passos e teste do preço de venda, exibindo custo, taxas, sobra e margem sem fazer contas manualmente.
- Ajustes com cartões de custos, proteção, aparência e suporte.
- Esquema 5 com backup de migração; custos históricos congelados são preservados.


## 2.0.8 — HF07 · Importação automática — 17/11/2026

- Exportação XLSX preserva campos pendentes como Pendente, sem falhar nem converter ausência de custo em zero.
- Um botão reconhece pedidos detalhados e resumo gerencial Shopee; permite selecionar os dois arquivos juntos sem escolher abas ou mapear colunas nos formatos reconhecidos.
- As abas Pedido Feito/Produto Pago são lidas juntas, com períodos identificados e bases preservadas. Totais de intervalo não são somados às linhas mensais/diárias.
- As informações alimentam o painel, o histórico mensal e os relatórios existentes. Nenhuma nova área ou aba de gerenciamento foi criada.
- Pedidos entram por ID e item; reimportar atualiza sem duplicar vendas. Arquivos selecionados com versões conflitantes do mesmo pedido exigem revisão, sem escolha arbitrária.
- Gravação dos arquivos selecionados em uma transação com backup; falhas revertem o conjunto. Custos e receitas já congelados são preservados.
- Vendas/taxas vêm dos pedidos; gramas, horas e custo completo vêm dos produtos vinculados. O custo inclui material, energia, máquina, embalagem e outros custos cadastrados.
- Resultado recebe um campo Após taxas e produção completa. Custos ou cobertura detalhada incompletos deixam o valor pendente. Valores por pedido mostra produção da receita e valor após essa produção; perdas adicionais continuam no resultado geral.
- Resumo anual preenche indicadores mensais sem inventar produtos, pedidos, filamento ou custos. Pagamento do comprador não vira repasse recebido.
- Cobertura e diferenças são verificadas por período. Meses sem pedidos detalhados não recebem custos fictícios; períodos que cruzam o filtro não são rateados.
- Histórico mensal e exportações preservam os indicadores gerenciais separados dos valores operacionais. Mapeamento avançado continua disponível para outros formatos.
- Esquema 4, com backup antes de migrar bancos anteriores e restauração em estágio sem modificar o arquivo de origem.

Os arquivos particulares usados para verificar a compatibilidade não acompanham o código ou instalador. Testes publicados usam somente dados sintéticos.


## 2.0.6 — HF06 · Simplificação — 17/11/2026

- Menu reorganizado: 16 entradas viram oito áreas, com funções relacionadas em subabas. Recursos e dados preservados.
- Precificação com um editor de custos/taxas, edição direta do produto e comparação de produtos em janela própria. Simulação permanece separada de alterações reais.
- Ajustes concentra preferências, backup, aparência, formato de SKUs e atualização; os parâmetros financeiros deixam de aparecer duplicados ali.
- Referência editável por kg comparada ao preço pago da última compra, calculado pelo peso e incluindo frete. Aplicar esse custo exige confirmação e não altera vendas/lotes congelados.
- Edição de material e parâmetros registra data da revisão. Sem valores reais informados, os parâmetros existentes permanecem referências; não há coleta ou presunção de preços de mercado.
- Pedidos: datas, produto, material/cor, busca por ID/SKU/variação e status específico. Exportação de itens respeita o mesmo recorte.
- Produtos, precificação e materiais: filtros de material/cor; combinação refere-se ao mesmo filamento.
- Produção: datas, pedido, produto, material/cor e etapa aplicados a lotes e perdas; ações mudam conforme a subaba.
- Estoque: datas de entrada/movimento e material/cor. Saldos e reservas continuam atuais; não se apresentam como saldo histórico.
- Financeiro: datas, categoria/descrição e material/cor nas compras. Repasses: datas, pedido e referência, com vínculos filtrados.
- Relatórios: filtro por pedido, período lembrado nos filtros salvos; simulador com período de vendas usado na referência.
- Conteúdo com rolagem para janelas menores, tabelas com altura mínima e ajuda mantida no topo. Botões de cadastro redundantes substituídos por acesso ao cadastro principal.

Instalador cumulativo, sem desinstalar nem apagar dados. Esquema permanece 3; preferências existentes são preservadas.


## 2.0.5 — HF03, HF04 e HF05 — 09/11/2026

Pacote cumulativo: instale uma vez sobre a versão anterior. Banco local preservado, com backup antes da migração do esquema.

### HF03 · Organização
- Central de pendências, revisão explícita de vínculos em lote e busca global (Ctrl+F).
- Comparação antes de importar pedidos: novos, alterados e sem alteração comercial; identificação do mesmo arquivo.
- Filtros de relatórios por SKU, variação, material, cor e cobertura de receitas; filtros salvos.
- Colunas reordenáveis e ocultáveis com posição/largura lembradas por tabela.
- Pequeno botão Como usar em todas as 16 abas, ajuda nas subabas e atalho F1.

### HF04 · Produção
- Lotes avulsos ou sincronizados de A Enviar, etapas e necessidades agrupadas.
- Reserva por material/cor, saldo físico por rolo, faltas, ajustes com motivo e histórico de movimentações.
- Baixa confirmada ao marcar Pronto, sem duplicação; estoque insuficiente impede concluir.
- Compras novas criam lotes de estoque; compras antigas exigem confirmação do saldo atual.
- Perdas/reimpressões com gramas, horas, custo estimado e estorno rastreável.
- Histórico de alterações das receitas, sem alterar custos congelados dos pedidos.

### HF05 · Gestão
- Simulador temporário de filamento, embalagem, energia, máquina, taxas e margem/acréscimo.
- Desempenho por produto com contribuição e retorno por hora quando conhecido.
- Repasses recebidos e conciliação manual por pedido, importação XLSX com referência única.
- Recebimentos separados de vendas; caixa por recebimentos separado de caixa estimado.
- Fonte, contraste, opacidade dos painéis e largura do menu configuráveis.
- Diagnóstico JSON local com versões, integridade e contagens; sem dados comerciais ou envio automático.

Filamento/horas seguem receitas e confirmação do operador; não há leitura da impressora. Contribuição não é lucro líquido. Repasses são informados pelo usuário, sem integração bancária. Simulador não altera os parâmetros do cadastro. Operação local funciona sem internet.


## 2.0.2 — HF02 · Produção — 06/11/2026

### Cadastro integrado ao fatiador
- Produtos ganha cartões de resumo, orientação para começar e painel lateral com receita e custos.
- Cadastrar via 3MF / G-code cria o produto físico, suas cores, gramas por unidade e tempo de impressão em um único fluxo.
- É possível selecionar várias placas que compõem o mesmo produto. A divisão usa produtos completos, nunca a quantidade de peças do arquivo.
- O material e a cor são identificados pelos metadados; nomes e preços por kg ficam disponíveis para revisão antes de salvar.
- Precificação mostra produto selecionado, peso, duração, custo, preço sugerido, composição em colunas e catálogo. Cálculo se atualiza ao selecionar o produto.

### Vendas e relatórios
- Leitura de XLSX com dimensões A1 incorretas e cabeçalhos repetidos, comuns em exportações do marketplace.
- Datas com horas e minutos são reconhecidas, e o período/mês vêm das datas e do intervalo declarado no nome do arquivo.
- Após confirmar a prévia, o relatório abre no período importado, com valores em colunas separadas.
- Receita dos produtos usa subtotais já descontados menos cupons/moedas financiados pelo vendedor. Frete pago pelo comprador, Valor Total e Total global são referências separadas. Não se desconta novamente a diferença entre preço original e acordado.
- Comissão e serviço líquidos têm preferência quando disponíveis; taxas do pedido não são multiplicadas pelos itens.
- Quantidade declarada no pedido, quando presente, é conferida para recusar arquivos com itens faltando.
- Produto reconhecido por variação exata e unívoca recebe a receita cadastrada, mesmo vindo de outro anúncio. SKU principal, trecho do título e semelhança ambígua nunca unem produtos.
- Variações de cor, modelo/tamanho e personagens diferentes permanecem separadas até revisão. SKU original e custos já congelados são preservados.

### Produção na visão geral
- Filamento e horas estimados dos pedidos, consumo por cor/material e tabela por pedido.
- Separa previsão a produzir de consumo estimado dos enviados/entregues/devolvidos. Não é telemetria ou comprovação de impressão.
- Itens sem receita ou tempo são exibidos como pendência, não como consumo zero conhecido.
- Abas de relatório com gramas/horas por unidade e por item, custo de produção e componentes financeiros por pedido. Exportação XLSX inclui essas tabelas.

### Dados e atualização
- Banco passa ao esquema 2 deste mesmo projeto, com backup consistente antes da conversão. Preserva produtos, cores, SKUs, pedidos, custos históricos e backups.
- Backups de esquema 1 deste ERP são aceitos, validados e convertidos em uma cópia temporária antes da restauração. Não são aceitos bancos antigos de outros projetos Forgeon.
- Nenhum arquivo enviado pelo usuário ou dado comercial acompanha o instalador. Importe seus arquivos localmente depois de atualizar.
- Custos preenchidos após o cadastro são estimativas registradas com a data atual; custos históricos já congelados não são recalculados.

## 2.0.1 — HF01 · Alpes — 06/11/2026

### Visual
- Novo ambiente dos Alpes suíços, incluído no instalador e disponível sem internet.
- Painéis com bordas arredondadas, transparência, reflexo suave e fundo desfocado, sem desfocar textos e valores.
- Ícone Forgeon com Banguela, aplicado à janela, ao executável, ao instalador e aos atalhos.
- Modo foco para reduzir a paisagem e priorizar a leitura.
- Painel organizado em indicadores, vendas do período e pendências com atalhos para resolução.

### Relatórios e ferramentas
- Gráficos de vendas por dia, custos do período, produtos mais vendidos e consumo por cor/material.
- Exportação dos gráficos em PNG e relatório do período em PDF, além do XLSX já disponível.
- Colunas ordenáveis, reorganizáveis e ocultáveis pelo cabeçalho; exportação das colunas visíveis e cópia de linhas pelo menu de contexto.
- As tabelas mantêm a identificação correta da linha ao ordenar, para editar o registro selecionado.
- Estados vazios claros e indicação de dados parciais também nos gráficos.

### Atualizações
- Nova área Atualizações com versão instalada e histórico incluído no aplicativo.
- Consulta à página oficial de Releases somente ao clicar em Verificar atualizações.
- Download do instalador de uma versão mais recente, com progresso, cancelamento e conferência de SHA-256 fornecido pelo GitHub.
- O arquivo é salvo na pasta escolhida. O aplicativo não executa o instalador nem altera seus dados automaticamente.
- O funcionamento normal permanece local e sem internet. Conexão é necessária somente para consultar/baixar atualizações por escolha do usuário.

### Compatibilidade e dados
- Mantém o banco e os backups já criados pelo ERP 2.0.0; não reutiliza bancos de versões antigas do Forgeon.
- Sem migração de esquema ou recálculo dos custos congelados nos pedidos.
- O instalador atualiza apenas os arquivos do ERP 2.0 e preserva a pasta de dados. Faça backup antes de instalar um hotfix.

## 2.0.0 — Entrega inicial — 06/11/2026

- Gestão de produtos físicos, anúncios e SKUs, cores, custos e precificação.
- Pedidos Shopee com prévia, transação e reimportação por ID.
- Estatísticas separadas dos pedidos, financeiro, relatórios, backup e restauração.
- Instalador Windows com Python e dependências incluídos.
- Correção do fechamento de conexões SQLite para liberar arquivos de backup/restauração no Windows.
