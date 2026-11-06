# Instalador Windows 10/11 de 64 bits

O instalador é gerado em Windows pelo GitHub Actions, usando Python 3.12.10 x64, PyInstaller 6.16.0 e Inno Setup 6 disponível no runner oficial `windows-2022`. Os scripts de compilação ficam em `packaging/` e o fluxo em `.github/workflows/windows-installer.yml`. As dependências adicionais estão fixadas em `requirements-build.txt` e vêm do PyPI. As actions oficiais estão fixadas por SHA.

## Para instalar e usar

Quando a compilação terminar com sucesso, baixe o artefato **FORGEON-STUDIO-ERP-2.0.0-Windows-x64-Instalador** na execução da aba Actions do repositório. Extraia o ZIP do artefato e execute **ForgeonStudioERP-2.0.0-Windows-x64-Setup.exe**. O pacote pode também ser distribuído nos Assets de uma Release verificada pelo mantenedor. O ZIP de código-fonte do botão Code não é o instalador.

O instalador contém o interpretador Python e as bibliotecas necessárias. Você não precisa instalar Python ou executar comandos. Ele abre um assistente em português, instala apenas para sua conta e cria um atalho no menu Iniciar. O atalho na área de trabalho é opcional. Use o atalho **FORGEON STUDIO ERP 2.0** para abrir depois da instalação.

- Aplicativo: `%LOCALAPPDATA%\Programs\ForgeonStudioERP2`.
- Banco e backups: `%LOCALAPPDATA%\ForgeonStudioERP2`.
- O banco é criado vazio no primeiro uso, se ainda não existir um banco deste projeto.
- Nenhuma instalação antiga do Forgeon é lida ou alterada.
- A desinstalação remove o aplicativo e preserva banco/backups. Antes de qualquer reinstalação ou troca de versão, mantenha seu próprio backup em outra mídia.
- O uso normal funciona sem internet. O instalador não baixa nem executa scripts remotos.

O `.bat` da raiz continua sendo apenas o lançador da versão em código-fonte, que exige ambiente `.venv`. Ele não deve ser usado para abrir a versão instalada.

## Como a compilação é conferida

O fluxo executa os testes no Windows, empacota o aplicativo em uma pasta com dependências e inclui o SQL do banco. Em seguida abre o executável empacotado em modo de verificação explícita, percorrendo as dez telas com banco temporário, cria/restaura um backup e verifica a integridade. Depois compila o instalador, instala-o no Windows descartável do CI e repete a verificação no executável instalado.

A instalação automática sem interação existe somente para o teste no runner, e seus comandos são visíveis no YAML. A instalação no seu computador é pelo assistente normal. A verificação não acessa seu banco real e apaga os dados temporários após finalizar.

Os arquivos JSON e o relatório JUnit ficam no artefato `validacao-windows`. A presença de uma receita de compilação não significa que o instalador já foi gerado: confira a execução e os artefatos. Os arquivos expiram após 30 dias no Actions; uma Release tem armazenamento independente.

## Compilar manualmente em Windows (desenvolvimento)

Com Python 3.12 x64 e Inno Setup 6 instalados de suas origens oficiais:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm packaging\ForgeonStudioERP.spec
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\ForgeonStudioERP.iss
```

O instalador ficará em `dist\installer`. Não compile o executável Windows a partir de Linux: o PyInstaller não faz compilação cruzada.

## Transparência e limites

O executável é distribuído em pasta (`onedir`) dentro do instalador, sem UPX, ofuscação, autoatualização ou alterações no Defender. Ele ainda não tem assinatura digital comercial. Não há garantia de ausência de alertas nem laudo antivírus. Se houver bloqueio, não desative a proteção nem crie exceções.

A verificação automatizada no Windows não substitui validação manual no Windows 10/11 com seus arquivos reais, configurações de tela e impressoras/fatiadores utilizados. Consulte também `VALIDACAO.md` e `DEPENDENCIAS_E_SEGURANCA.md`.

## Caso a integração não tenha permissão para criar workflows

O modelo completo também está em `packaging/windows-installer.yml`. No GitHub, crie um arquivo `.github/workflows/windows-installer.yml` copiando esse modelo integralmente e confirme na branch `main`. A compilação começa com esse commit. Isso é necessário somente quando a conexão do aplicativo não tem a permissão especial de escrita em workflows.
