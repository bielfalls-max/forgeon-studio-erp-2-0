# Validação inicial em fontes e pendências

> Este primeiro registro documenta a entrega original em código-fonte. A etapa posterior de instalador e testes nativos está registrada ao fim desta página.

Data da execução: 06/11/2026. Ambiente Linux x86_64, Python 3.12.14, SQLite 3.53.1 e PySide6 6.8.3. Não foi utilizado Windows nesta execução.

## Executado de fato

- `QT_QPA_PLATFORM=offscreen python -m pytest -q -ra`: **49 testes aprovados**. Saída original em `resultado_pytest.txt`.
- `python -m pip check`: `No broken requirements found.` no ambiente virtual isolado.
- `python -m compileall -q forgeon tests`: compilação dos módulos sem erros.
- Instalação das dependências públicas fixadas em ambiente virtual novo.
- Geração de cinco modelos XLSX vazios e leitura dos modelos nos testes.
- Abertura e atualização das dez telas com banco vazio e preenchido, usando Qt real em modo offscreen; erros de diálogo são interceptados e causariam falha dos testes.
- Captura e inspeção visual da tela inicial vazia em Qt offscreen no Linux.

## Cobertura dos testes automatizados

| Área | Verificações |
|---|---|
| Números | Negativos, NaN, infinitos, limites, quantidades inteiras, datas e moeda brasileira |
| Precificação | Material/energia/máquina, custo manual substitutivo, margem versus acréscimo, taxas inválidas |
| Produtos | Compartilhamento de origens, cores somadas ao peso, cópia sem alterar SKUs, arquivo/reativação |
| Identificação | Sonic separado de Super Sonic, sugestões Silver sem fusão nem associação automática |
| SKUs | Reservas manuais/automáticas, zeros, não reutilização automática, aposentadoria e conflito entre produtos |
| Pedidos | Vários itens sem multiplicar total/taxas, reimportação sem duplicar, arquivo parcial preservando outros IDs |
| Histórico | Custo congelado persistente, SKU original preservado, desvinculação sem apagar pedidos, congelamento posterior datado |
| Status | Cancelamentos, devoluções, reembolso, custos e consumo de produção |
| Financeiro | Compra de material distinta do consumo, despesas e caixa estimado |
| Estatísticas | Reimportação por chave, não somar receita aos pedidos, períodos sobrepostos, resumo parcial e linha TOTAL |
| Importação | Transação revertida em falha, backup anterior preservado, dados pessoais de comprador não persistidos |
| Backup | Cópia consistente, restauração preservando estado anterior, rejeição de banco antigo/corrompido, trigger e esquema alterado |
| XLSX | Fórmulas recusadas na entrada, texto explícito na saída, zeros com máscara, modelos vazios e cadastro em transação |
| Fatiamento | 3MF com várias placas, divisão por unidade, comentários de G-code, arquivo sem metadados, recusa de entidades XML e caminhos inseguros |
| Interface | Dez telas vazias/preenchidas, leitura de formulário, bloqueio de duas instâncias |

Os arquivos usados nos testes são sintéticos, temporários e locais. Não são planilhas reais da conta do usuário nem todos os formatos já produzidos pelos marketplaces e fatiadores. Testar a abertura das telas não equivale a uma homologação manual de todos os cliques e diálogos.

## Ainda depende de validação no Windows

1. Instalação em máquinas Windows 10 e Windows 11 de 64 bits com Python 3.12, seguida de abertura pelo `.bat`.
2. Renderização com Segoe UI, escalas de 100%/125%/150%, vários tamanhos de tela, diálogos nativos e caminhos com acentos/espaços.
3. Todos os fluxos completos com mouse/teclado, arquivos reais e volume representativo da empresa; em especial mapeamento de cabeçalhos Shopee e critérios das estatísticas reais.
4. Metadados produzidos pelas versões efetivamente usadas de Bambu Studio e OrcaSlicer. O leitor aceita os formatos documentados, não promete decodificação universal.
5. Bloqueio entre processos Windows, encerramento inesperado, permissões locais, backup e restauração em mídias externas.
6. Abertura das exportações no Excel utilizado pela empresa e conferência dos valores com os relatórios originais.
7. Revisão dos parâmetros financeiros, taxas, status e regras de reembolso antes de usar os números para decisões comerciais.

Não foram executados análise antivírus, Microsoft Defender, assinatura de binário, geração de EXE/MSI ou instalação Windows. Não há alegação de ausência de detecção nem de segurança garantida. Nenhum arquivo foi publicado ou enviado para análise externa.

## Verificação sugerida após instalar

Use primeiro um banco de teste separado por conta Windows ou faça backup do banco vazio. Cadastre dois produtos distintos, vincule dois anúncios ao mesmo produto e um anúncio a outro produto; gere um conflito de SKU para conferir o destaque vermelho. Importe um pedido com dois itens, repita a importação e importe outro arquivo contendo apenas um dos IDs. Confira preservação do restante. Simule cancelamento e devolução, compare relatórios e teste restaurar um backup. Mantenha cópia dos arquivos de entrada para conciliação; o aplicativo não copia a planilha original para o banco.


## Etapa posterior: instalador Windows

Em 06/11/2026, a compilação [42288155855](https://github.com/bielfalls-max/forgeon-studio-erp-2-0/actions/runs/42288155855) passou em Windows Server 2022, Python 3.12.10 x64: **51 testes aprovados, zero falhas ou erros**. O executável PyInstaller abriu as dez telas e verificou criação, backup, restauração e integridade em banco temporário. O instalador Inno Setup foi compilado, instalado no runner e o aplicativo instalado passou novamente na verificação das dez telas. Os relatórios XML/JSON acompanham a Release.

Esses testes não são homologação interativa em computadores Windows 10/11 nem análise antivírus. Arquivos reais, escalas de tela, hardware e permissões do usuário ainda dependem de validação manual. O registro anterior de 49 testes permanece como histórico da primeira entrega. O `.bat` continua sendo somente o lançador dos fontes; para a versão instalada use o atalho criado pelo Setup. Consulte `INSTALADOR_WINDOWS.md`.

## HF01 — validação adicional

O hotfix 2.0.1 acrescenta testes para ordenação sem perda de identidade de registros, colunas visíveis, PDF real, série diária coerente com o relatório, abertura offline e recursos visuais, além de versões e downloads de atualização (hash inválido, cancelamento, limite/metadata e redirecionamento indevido). A rodada local passou **70 testes**. O fluxo Windows executa a mesma suíte, abre as onze telas no executável e na instalação e testa a atualização da própria entrega 2.0.0: confere que banco e backup de teste permanecem intactos. Os resultados nativos efetivos ficam anexados à Release, e não devem ser inferidos apenas da existência do script.

O ícone, a paisagem e as notas são recursos locais incluídos no pacote. Não existe consulta de rede ao abrir telas. A consulta de versões e o download só começam por clique do usuário; nenhum instalador é executado pelo aplicativo. As notas e limites do download estão em `HOTFIXES.md`.

## HF02 — produção e importação

A suíte acrescenta cadastro multi-placa, divisão por produtos completos, planilha sintética com dimensão A1 incorreta e cabeçalhos repetidos, preferência de taxas líquidas, pedidos multi-itens, identificação de período, correspondência exata de variação, conflito de SKU, snapshots preservados ao reimportar, cadastro posterior de receitas, conversão de banco/backup de esquema 1, assistente real de cadastro e abertura automática do relatório. Os testes públicos são exclusivamente sintéticos. Arquivos particulares fornecidos pelo usuário foram exercitados apenas em banco temporário local, sem inclusão no GitHub ou no instalador. A execução nativa e a quantidade final de testes aprovados constam dos anexos da Release.


## Pacote cumulativo HF03 a HF05 — 2.0.5 — 09/11/2026

No Linux, 96 testes aprovados com Qt real offscreen; dependências consistentes e compilação dos módulos sem erros. Inclui 17 novos testes de reserva versus baixa, idempotência, rollback em falta de uma cor, perdas/estornos, compras e fluxo físico separado, pedidos alterados, histórico de receitas, simulador sem escrita, repasses e datas sem duplicar vendas, importação de recebimentos transacional, filtros, privacidade do diagnóstico, ajuda nas 16 abas, persistência de colunas e restauração de esquema 2 ao 3 sem alterar a origem. Evidência local em resultado_hf05_pytest.txt.

Capturas Qt offscreen das novas telas e filtros foram inspecionadas. O teste do executável empacotado agora também exercita baixa de lote, perda/estorno, simulador e recebimento em banco temporário. O fluxo Windows exige 16 telas no executável e no programa instalado, testes nativos aprovados e migração preservando dados/backups antes de publicar. Relatórios dessa execução acompanham a versão no GitHub.

Validação manual no Windows 10/11, escalas de tela e arquivos reais continua pendente. Não há integração bancária/impressora ou medição automática do consumo; use os guias contextuais para os limites dos indicadores.


## HF06 — 2.0.6 — 17/11/2026

Linux: 110 testes aprovados, incluindo 14 novos cenários de navegação em oito áreas, seleção/limpeza de datas, filtros consistentes em pedidos e exportação, produção/perdas, estoque atual versus datas dos movimentos, despesas/compras, repasses, período de referência no simulador, custo pago por kg com frete e aplicação explícita, preservação dos snapshots, correspondência material/cor no mesmo filamento, filtros salvos com datas, comparação de produtos e geometria sem sobreposição em janela 1100×700. Saída em resultado_hf06_pytest.txt.

Capturas Qt offscreen das telas em 1440×900 e 1100×700 foram inspecionadas. O teste do pacote também exige oito áreas, visita todas as 16 telas e calcula/aplica preço de compra em banco temporário. A compilação/publicação Windows exige os testes nativos e as verificações do executável/instalador/atualização aprovadas; evidências acompanham a versão.

Não se presume que tarifas de energia ou taxas comerciais estejam atualizadas sem dados reais do usuário. Validação manual no Windows 10/11, escala de tela e volume real de dados permanece necessária.


## HF07 — 2.0.8 — 17/11/2026

131 testes locais com Qt offscreen, incluindo 21 cenários novos: detecção dos dois formatos/abas, período, privacidade, mesma venda em múltiplos itens, reimportação em ambas as ordens sem somar novamente, total anual versus meses/bases, período sem detalhe e sem rateio, transação revertida, cobertura mais curta preservando a completa, fórmulas/formato desconhecido, snapshots, pagamento conhecido preservado, migração/restauração de esquema 3, interface sem pedir mapeamento nos formatos conhecidos, cancelamento sem escrita, conflitos entre arquivos, telas existentes sem nova aba, resultado após produção pendente/completo e cobertura anual incompleta. Saída em resultado_hf07_pytest.txt.

Os dois arquivos fornecidos foram lidos localmente e verificados em banco temporário descartável, inclusive reimportação invertida. Totais e contagens de outubro conferiram entre as bases correspondentes; informações e arquivos particulares não foram incluídos nos testes públicos, código ou instalador. Capturas Qt offscreen com dados sintéticos foram inspecionadas. O teste do pacote também lê um resumo sintético e reimporta, verificando que não cria vendas nem duplica o total.

A compilação Windows exige os testes nativos e as verificações de executável/instalação/atualização aprovadas; evidências acompanham a versão. Validação manual no Windows 10/11 e com arquivos de outros formatos permanece necessária. Tarifas/custos e receitas de produção precisam ser informados pelo usuário.


## HF08 — 2.0.9 — 17/11/2026

136 testes locais, incluindo cinco novos cenários de produtos automáticos sem receita fictícia e sem duplicação, compras e consumo sem descontar duas vezes, custo congelado preservado, sugestão por pedidos abertos, precisão de frações de centavo e ferramenta/despesa com frete no mês. Capturas Qt offscreen em janela 1100×700 foram inspecionadas. A validação Windows e as verificações de instalação são exigidas pelo fluxo de publicação; evidências acompanham a versão. Saldos/sugestões são estimativas que dependem de histórico/receitas completos e conferência física.


## HF09 — 2.0.10 — 17/11/2026

141 testes locais, incluindo cinco cenários novos de identidade/tamanho, aliases explícitos e intervalos ambíguos, unificação de origens/itens sem mudar snapshots, separação 12/16 cm nas importações e bloqueio de receitas conflitantes. Testes públicos usam dados sintéticos. Verificações de pacote e instalação Windows são exigidas antes da publicação; evidências acompanham a versão. Validação manual dos grupos reais continua necessária na prévia.


## HF10 — 2.0.11 — 17/11/2026

146 testes locais, com cinco cenários adicionais: anúncios legados sem observação, reparo automático na reabertura, preservação de tamanhos explícitos, vendas de aliases em anúncios distintos consultando uma receita e tela Produtos com uma linha física sem colunas de anúncio/SKU. Os testes do pacote e instalação Windows são exigidos na publicação. Arquivos particulares não acompanham a distribuição.
