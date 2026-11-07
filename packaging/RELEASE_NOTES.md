# HF02 · Produção — FORGEON STUDIO ERP 2.0.2

Baixe **ForgeonStudioERP-2.0.2-Windows-x64-Setup.exe** nos Assets. Faça backup em Configurações, feche o ERP e execute o Setup para a mesma conta/pasta. Não precisa instalar Python nem apagar cadastros.

- Cadastro integrado de produto a partir de 3MF/G-code, selecionando várias placas e a quantidade de produtos completos. Salva cores, gramas e tempo por unidade, com preços por kg revisáveis.
- Produtos com resumo do catálogo, ações de início, tabela e painel da receita. Precificação com indicadores, composição por coluna, seletor automático e catálogo.
- Correção de XLSX que declara dimensões A1 incorretas, cabeçalhos repetidos e datas com horas/minutos.
- Identificação de mês/período e abertura automática do relatório após confirmar a prévia.
- Colunas de receita dos produtos, comissão/serviço líquidos, transação e referências separadas de frete, Valor Total e Total global. Sem duplicar taxas em pedidos com vários itens ou descontar duas vezes o desconto de preço.
- Vínculo por variação exata e única, sem unir personagens, variantes de cor/modelo ou usar somente SKU principal. Ambiguidades ficam pendentes.
- Visão geral com filamento e horas estimados, previsão a produzir, consumo conhecido por cor e tabela por pedido. Relatórios/XLSX incluem gramas/horas por unidade e por item.
- Snapshots preservam consumo e custos já congelados; custos pendentes preenchidos posteriormente têm data atual e são estimativas de cadastro.
- Esquema SQLite 2 deste mesmo projeto, com backup antes de converter bancos de esquema 1. Preserva cadastros e pedidos; restauração de backups compatíveis faz conversão em cópia temporária. Não use o banco convertido em versões anteriores do executável.

Consumo é estimado pelo cadastro e pelos pedidos, não medição real da impressora. Pedidos A Enviar representam previsão; custos/receitas ausentes são marcados DADOS PARCIAIS. Revise os parâmetros de fabricação e taxas antes de decidir preços.

Arquivos enviados pelo usuário foram examinados apenas localmente. Nenhuma planilha, modelo 3D, dado pessoal ou informação comercial do usuário acompanha fontes, testes públicos ou instalador. Os testes publicados usam somente dados sintéticos.

Os relatórios XML/JSON anexados registram a execução real no Windows Server 2022 do GitHub Actions, a abertura do executável/instalador e a preservação de registros/backups ao atualizar o esquema. Ainda é necessária validação manual no Windows 10/11 com seus arquivos e parâmetros. Não há assinatura digital comercial nem laudo antivírus.
