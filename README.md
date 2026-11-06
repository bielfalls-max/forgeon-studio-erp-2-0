# FORGEON STUDIO ERP 2.0

Aplicativo desktop local para gestão de pequena empresa de impressão 3D. Projeto criado do zero em Python 3.12, PySide6/Qt Widgets e SQLite. Interface em português, tema escuro e dados persistentes. O banco de produção é criado vazio no primeiro uso. Nenhum arquivo de versões antigas é necessário ou reutilizado.

**Versão instalável para Windows:** veja [Instalador Windows](docs/INSTALADOR_WINDOWS.md). O instalador inclui Python e bibliotecas; o ZIP do botão Code contém apenas os fontes. A compilação e os testes nativos são feitos pelo fluxo **Instalador Windows**, na aba Actions. O instalador só está disponível após uma execução bem-sucedida.

As instruções abaixo são para executar **a versão em código-fonte**, criando um ambiente Python isolado. Ela não modifica a instalação antiga do Forgeon.

## Instalar no Windows 10/11 de 64 bits

1. Instale Python **3.12 de 64 bits** do site oficial: https://www.python.org/downloads/windows/ . O ambiente de validação desta entrega usou Python 3.12.14; use uma versão 3.12 com atualizações de segurança disponíveis para seu Windows.
2. Extraia o ZIP inteiro para uma pasta nova e gravável. Não extraia sobre uma versão anterior.
3. Abra o **Prompt de Comando** nessa pasta (a pasta que contém este README) e execute:

```bat
py -3.12 --version
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m forgeon
```

A instalação das dependências requer internet. O uso normal do ERP não requer. Não há download automático de código durante a abertura. Os comandos usam o Python do ambiente virtual sem ativação e sem PowerShell.

Após instalar, abra por duplo clique em **`abrir_forgeon.bat`** ou pelo comando `.venv\Scripts\python.exe -m forgeon`. O lançador mantém erros visíveis. Se o Windows/Defender bloquear um arquivo, não desative a proteção nem crie exceções; consulte a documentação de segurança.

### Instalação inicial sem internet (opcional)

Em outro computador **Windows de 64 bits com Python 3.12**, conectado à internet, baixe as dependências públicas:

```bat
py -3.12 -m pip download --only-binary=:all: -r requirements.txt -d dependencias
```

Transfira a pasta `dependencias` junto com o projeto. No computador de destino:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --no-index --find-links=dependencias -r requirements.txt
.venv\Scripts\python.exe -m forgeon
```

Os wheels de Linux não servem para instalar PySide6 no Windows. A pasta de dependências não está incluída no ZIP desta entrega.

## Primeiro uso

1. Em **Configurações**, revise energia, potência, máquina, margem/acréscimo e taxas. Taxas iniciais zero não representam condições garantidas da Shopee.
2. Em **Custos e cores**, cadastre materiais, cores e preço por kg.
3. Em **Produtos**, crie um produto físico por personagem/modelo/tamanho. Cadastre horas, embalagem e outros custos. Fabricação manual é opcional e substitui material+energia+máquina.
4. Defina consumo por cor/unidade. Com cores, o peso é a soma dos gramas. Também é possível ler 3MF fatiado ou G-code, escolher placa e quantidade, revisar e associar filamentos.
5. Em **Importações**, importe uma planilha de pedidos. Selecione a aba, linha de cabeçalho, mapeie colunas e revise a prévia. Confirme somente após conferir valores, quantidades e zeros dos SKUs.
6. Em **Catálogo e SKUs**, associe cada origem ao produto físico correto. Sugestões nunca fazem fusões automáticas. Confira diferenças de personagem, tamanho e modelo. Conflitos de SKU entre produtos ficam vermelhos.
7. Em **Pedidos**, use **Congelar custos pendentes** após completar os cadastros. Essa ação registra o custo atual e a data atual; não afirma que era o custo na data passada da venda. Custos já congelados ficam preservados.
8. Cadastre despesas e compras em **Financeiro**. Importe o resumo mensal da loja separadamente e consulte a conciliação em **Relatórios**.
9. Crie backup em **Configurações** e mantenha cópia em outra mídia.

**Order.toship só cobre A Enviar**. Para maior cobertura mensal use Todos os pedidos/Order.all. Cada arquivo precisa conter todos os itens de cada ID de pedido que inclui. Uma importação parcial preserva pedidos ausentes no arquivo. Totais/taxas devem ser valores do pedido, não rateios por item.

## Onde os dados ficam

No Windows: `%LOCALAPPDATA%\ForgeonStudioERP2\forgeon2.sqlite3`. O caminho é calculado pela conta atual, sem nome de usuário fixo. Backups automáticos ficam na subpasta `backups`. Não são incluídos bancos de exemplo ou dados pessoais na entrega.

Use uma única instância por banco; o aplicativo tem bloqueio local. Não mantenha o arquivo em pasta sincronizada ou em compartilhamento de rede para uso simultâneo. O SQLite entregue é para uso local. Não exclua o arquivo de bloqueio enquanto outro processo estiver aberto.

## Recursos

- Visão geral, produtos, cores e custos, precificação com composição, catálogo, reservas e conflitos de SKU.
- Pedidos com vários itens, custo congelado e correções auditadas de status, taxas e reembolso.
- Importação XLSX com prévia/mapeamento, reimportação por ID e transação com backup.
- Estatísticas por anúncio/período separadas dos pedidos, comparação de cobertura e DADOS PARCIAIS.
- Despesas e compras de filamento, edição/exclusão de lançamentos com histórico, resultado operacional e caixa estimado.
- Relatórios por período/produto/status, mais vendidos, consumo por material/cor/mês/quinzena, histórico mensal.
- Exportação XLSX de produtos/custos, catálogo, pedidos/itens, financeiro, consumo e relatórios mensais.
- Modelos vazios em `modelos/`, também geráveis pelo aplicativo para produtos, filamentos, despesas, pedidos e estatísticas.
- Backup SQLite consistente, validação de integridade, restauração compatível com cópia prévia do banco atual.

## Limitações que precisam ser conhecidas

O resultado depende da completude das planilhas e dos cadastros. O mapeamento atende variações de cabeçalho, mas não promete interpretar qualquer relatório Shopee automaticamente. Se o relatório mensal possuir outra estrutura (por exemplo, só um total da loja ou dados distribuídos em blocos), normalize uma cópia para o modelo fornecido, sem inventar anúncios ou variantes.

3MF sem metadados de fatiamento não fornece consumo confiável; o leitor explica a limitação. Há suporte a `Metadata/slice_info.config` com placas/filamentos e a comentários conhecidos de Bambu/Orca e `TIME` no G-code. Não se calcula massa a partir de comandos ou da geometria. Placas com produtos diferentes não podem ser divididas somente pelo número de unidades: use placa de um mesmo produto ou cadastro manual por unidade.

O caixa é estimado, sem saldo inicial, agenda de repasses ou conciliação bancária. Consulte [Regras financeiras](docs/REGRAS_FINANCEIRAS.md). Estatísticas não criam vendas adicionais. Produtos sem vínculo/custo e fontes incompletas geram DADOS PARCIAIS.

## Executar os testes

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe -m pytest -q
set QT_QPA_PLATFORM=
```

O modo `offscreen` permite testar a abertura das telas sem mostrá-las. Para uso normal não é necessário definir essa variável. Veja o registro real de execução e o que depende do Windows em [Validação](docs/VALIDACAO.md).

## Estrutura e documentação

- [Árvore completa](docs/ARVORE.txt)
- [Arquitetura e modelo do banco](docs/ARQUITETURA.md)
- [Esquema SQL completo](forgeon/db/schema.sql)
- [Regras financeiras e custos históricos](docs/REGRAS_FINANCEIRAS.md)
- [Dependências, origem e segurança](docs/DEPENDENCIAS_E_SEGURANCA.md)
- [Validação e pendências no Windows](docs/VALIDACAO.md)

O código foi autorizado para publicação em repositório público no GitHub: https://github.com/bielfalls-max/forgeon-studio-erp-2-0 . Não houve publicação de site nem envio para análise antivírus externa. Reescrever não garante ausência de ameaças; resultados de testes funcionais não são laudo antivírus.
