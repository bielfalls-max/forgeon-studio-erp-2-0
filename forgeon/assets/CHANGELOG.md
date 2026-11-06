# Notas de atualização

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
