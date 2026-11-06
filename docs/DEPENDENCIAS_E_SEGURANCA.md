# Dependências e segurança

## Origem e versões

A instalação usa os pacotes públicos do Python Package Index (PyPI), pelos comandos locais documentados, com TLS habilitado. Não há código antigo do Forgeon nem download/execução de scripts remotos. O Python deve vir de https://www.python.org/downloads/windows/.

| Dependência | Versão | Origem / finalidade |
|---|---|---|
| Python | 3.12.x, 64 bits | Python Software Foundation, biblioteca padrão e SQLite embarcado |
| PySide6 | 6.8.3 | Qt for Python, interface Qt Widgets |
| PySide6_Addons | 6.8.3 | Distribuição oficial Qt, dependência do PySide6 |
| PySide6_Essentials | 6.8.3 | Distribuição oficial Qt, componentes essenciais |
| shiboken6 | 6.8.3 | Distribuição oficial Qt, bindings |
| openpyxl | 3.1.5 | Leitura e escrita XLSX sem macros |
| et_xmlfile | 2.0.0 | Dependência de escrita XML do openpyxl |
| defusedxml | 0.7.1 | Parser que recusa DTD/entidades externas |
| pytest | 8.3.5 | Somente testes |
| iniconfig | 2.1.0 | Dependência de testes |
| packaging | 24.2 | Dependência de testes |
| pluggy | 1.5.0 | Dependência de testes |
| colorama | 0.4.6 | Dependência de testes no Windows |

As versões estão fixadas em `requirements.txt` e `requirements-dev.txt`, inclusive dependências transitivas. As licenças são as das respectivas distribuições; PySide6/Qt possui condições LGPL/GPL/comerciais. Este pacote entrega código Python, sem redistribuir binários Qt nem wheels. Revise as licenças antes de redistribuir um aplicativo empacotado. Documentação: https://doc.qt.io/qtforpython-6/ ; https://openpyxl.readthedocs.io/ ; https://pypi.org/project/defusedxml/ ; https://docs.pytest.org/.

## Controles implementados

- Banco separado em `%LOCALAPPDATA%\ForgeonStudioERP2`, sem caminhos com nome fixo de usuário e sem tocar instalações anteriores.
- Gestão local sem rede; a partir do HF01 há consulta/download HTTPS de atualizações, exclusivamente ao clicar, no repositório oficial. Sem telemetria, instalação automática, terminal embutido, IA, controle remoto ou automação de sites.
- QLockFile impede duas instâncias deste aplicativo no mesmo banco. SQL parametrizado e transações explícitas.
- Backup pela API SQLite, conferindo identidade, integridade e chaves estrangeiras. Restauração validada em cópia temporária local, com conferência do esquema exato, sem triggers nem views, e backup do banco atual antes de substituir.
- XLSX limitado a 32 MB compactados, 128 MB de conteúdo, 4096 entradas, 256 colunas, 100 mil linhas e 2 milhões de células. Fórmulas são recusadas, inclusive nas colunas que não seriam importadas. Nenhuma macro é executada.
- Strings exportadas são explicitamente texto, inclusive nomes iniciados por `=`, `+`, `-`, `@` e SKUs com zeros. Dinheiro e datas são exportados de forma legível em português; valores monetários ficam como texto `R$`, sem fórmulas.
- 3MF limitado a 128 MB compactados, 512 MB de conteúdo total, 4096 entradas, XML de metadados de até 8 MB. Caminhos absolutos/traversal e entradas criptografadas são recusados. Não há extração para o sistema de arquivos. XML recusa DTD/entidades. G-code é apenas lido; somente comentários conhecidos fornecem estimativas.
- Backups aceitos até 512 MB. A identidade do projeto não é uma assinatura criptográfica de autoria: aceite backups somente de fontes confiáveis.
- Não existe `eval`, `exec` nem subprocesso para executar instruções vindas de arquivos. O lançador `.bat` é legível e apenas abre o Python local do ambiente virtual, exibindo erros.
- Não são persistidos CPF, telefone, endereço ou nome de comprador. O arquivo de entrada é lido em memória, mas somente campos gerenciais selecionados são gravados. Não inclua informações pessoais em nomes de produtos ou observações.

## Limitações e análise antivírus

A reescrita não garante segurança nem ausência de alertas. A origem do alerta anterior `Trojan:Script/Ulthar.A!ml` permanece desconhecida. Não houve análise antivírus, certificação, assinatura digital ou validação pelo Microsoft Defender nesta entrega. Os testes funcionais relatados não substituem isso.

Não desative o Defender, não crie exceções e não restaure arquivos bloqueados para usar este projeto. Se o arquivo for bloqueado, interrompa a instalação e trate o alerta pelos procedimentos normais de análise. Nenhum arquivo foi enviado a serviço externo de análise nesta execução. A instalação antiga não foi consultada ou modificada.

O banco não é criptografado. Permissões da conta Windows e backups em local confiável protegem o acesso. Backups podem conter informações comerciais e devem receber o mesmo cuidado que o banco. A pasta de backups não tem limpeza automática: revise espaço em disco e guarde cópias em outra mídia.

## Empacotamento Windows acrescentado

A compilação utiliza PyInstaller 6.16.0, hooks 2025.9, altgraph 0.17.4, setuptools 80.9.0, pefile 2023.2.7 e pywin32-ctypes 0.2.3, além das dependências já descritas, com versões fixadas em `requirements-build.txt`. O instalador Inno Setup 6 vem do runner Windows oficial do GitHub; sua versão é registrada nos logs da compilação. As bibliotecas incluídas mantêm suas licenças e metadados no pacote gerado pelo PyInstaller. Confira as condições de redistribuição do Qt/PySide6 antes de redistribuir. Nenhuma análise antivírus foi adicionada ao fluxo. Veja `INSTALADOR_WINDOWS.md`.

## HF01 — rede opcional e recursos

A consulta de atualizações usa `urllib`/TLS da biblioteca padrão, em thread separada e sem credenciais. Não envia arquivos, banco nem informações de compradores. URLs de instaladores são restritas ao repositório oficial, com HTTPS, limite de tamanho e redirecionamentos para distribuição GitHub. O download usa arquivo temporário e só substitui o destino após tamanho, assinatura MZ e SHA-256 coincidirem com os metadados da Release. Não há instalação ou execução automática. O SHA-256 não é assinatura digital de autoria. Os testes usam respostas sintéticas, falhas de hash, cancelamento e redirecionamentos indevidos. As imagens locais e seu ícone estão documentados em `forgeon/assets/ORIGEM_DOS_RECURSOS.md`; nenhuma função de IA foi adicionada ao aplicativo. Os gráficos usam desenho local QPainter/Qt Widgets, sem adicionar QtCharts ou uma nova biblioteca de gráficos ao pacote.
