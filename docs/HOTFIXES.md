# Hotfixes e atualização manual

## HF01 — versão 2.0.1 — Alpes — 06/11/2026

Veja as [notas completas incluídas no aplicativo](../forgeon/assets/CHANGELOG.md). Este hotfix preserva o esquema do banco ERP 2.0.0 e os custos congelados. Adiciona o tema de vidro fosco com paisagem dos Alpes, identidade visual com ícone do Banguela, modo foco, indicadores em cartões, gráficos com filtros, PDF/PNG e organização de colunas.

### Instalar este primeiro hotfix

A versão 2.0.0 ainda não tem o botão de atualização. Faça backup em Configurações, feche o ERP e baixe o Setup **2.0.1** na [página da versão](https://github.com/bielfalls-max/forgeon-studio-erp-2-0/releases/tag/v2.0.1). Execute-o para a mesma conta Windows e mesma pasta de instalação. Não precisa desinstalar nem apagar dados. Banco e backups permanecem em `%LOCALAPPDATA%\ForgeonStudioERP2`.

### Próximos hotfixes, pelo aplicativo

1. Abra **Atualizações** no menu lateral. A versão instalada e o histórico local são exibidos mesmo sem internet.
2. Clique **Verificar atualizações**. Só essa ação inicia uma consulta HTTPS à API pública do repositório oficial, sem enviar banco, pedidos ou dados pessoais.
3. Se houver versão mais recente com instalador e SHA-256 verificáveis, leia as notas e clique **Baixar hotfix disponível**.
4. Escolha onde salvar. O aplicativo cria um backup consistente antes do download, mostra progresso e permite cancelar. Um arquivo interrompido ou com hash/tamanho inválido é descartado; arquivos existentes não são substituídos antes da verificação.
5. Depois de baixar, feche o ERP e execute o Setup manualmente. Nenhum instalador é executado automaticamente e nenhuma atualização ocorre ao iniciar o programa.

São consideradas versões `X.Y.Z` publicadas no mesmo repositório com instalador Windows. Prévias também são exibidas, identificadas como prévias para validação. A consulta não instala versões mais antigas e ignora releases sem metadados verificáveis. Em caso de indisponibilidade ou limite de consultas do GitHub, tente mais tarde; a gestão local continua funcionando.

O SHA-256 confirma que os bytes correspondem ao artefato publicado pelo GitHub. Não é assinatura digital comercial nem laudo antivírus. Não desative o Defender nem crie exceções diante de bloqueios.

## Ferramentas visuais

- **Modo foco**, no rodapé lateral: reduz a paisagem e deixa os painéis mais opacos; preferência salva no banco.
- **Gráficos**, em Relatórios: respeitam período, produto e status selecionados. Fontes incompletas permanecem sinalizadas.
- Passe o mouse nos pontos, barras e fatias para ver valores. Use botão direito no gráfico para salvar em PNG.
- **Exportar PDF** salva indicadores, filtros, produtos em destaque e gráficos. XLSX permanece disponível.
- Clique no cabeçalho para ordenar, arraste para mudar a posição e use o botão direito no cabeçalho para ocultar/mostrar colunas.
- Botão direito na tabela: copiar a linha ou exportar apenas as colunas visíveis, na ordem apresentada. A edição usa o registro efetivamente selecionado após ordenar.

As imagens são recursos locais incluídos no instalador. O desfoque é da paisagem atrás dos painéis; textos e números permanecem nítidos. Não há dependência de transparência nativa do Windows, internet ou GPU avançada para o efeito. Em máquinas com pouca memória, use Modo foco.
