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
