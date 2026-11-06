Instalador do FORGEON STUDIO ERP 2.0 para Windows 10/11 de 64 bits, com Python e bibliotecas incluídos. Não é necessário instalar Python separadamente.

Baixe **ForgeonStudioERP-2.0.0-Windows-x64-Setup.exe** nos Assets e execute o assistente. Depois use o atalho **FORGEON STUDIO ERP 2.0** no menu Iniciar. Os arquivos Source code são apenas o código-fonte e não substituem o instalador.

O aplicativo fica em `%LOCALAPPDATA%\Programs\ForgeonStudioERP2`. Banco e backups ficam em `%LOCALAPPDATA%\ForgeonStudioERP2`, separados dos arquivos do aplicativo. O uso normal é local, sem internet. Nenhum banco da empresa ou dado de comprador acompanha o instalador.

Compilação reproduzível: scripts em `packaging/`, dependências fixadas em `requirements-build.txt`, fluxo na aba Actions. O arquivo SHA256.txt permite conferir a integridade do instalador; não é assinatura digital nem laudo antivírus.

Validação manual em computadores Windows 10/11, com os arquivos reais da empresa e suas configurações de tela, ainda é necessária. O executável não possui assinatura digital comercial. Não foram realizados laudo antivírus ou análise externa de segurança; testes funcionais não garantem ausência de alertas.

Verificação realizada no Windows Server 2022 do GitHub Actions: **51 testes aprovados**, executável empacotado com dez telas aberto sem erros e instalação do Setup seguida de abertura das dez telas do aplicativo instalado. A verificação usa banco temporário, incluindo criação, backup, restauração e integridade, e não acessa banco de produção.

Evidências: `resultado-windows.xml`, `verificacao-executavel.json` e `verificacao-instalado.json`, anexados a esta release. Compilação: https://github.com/bielfalls-max/forgeon-studio-erp-2-0/actions/runs/42288155855 . O registro `docs/VALIDACAO.md` incluído no instalador é o registro histórico da primeira entrega em fontes; os arquivos desta release registram a etapa posterior de compilação e teste Windows.

Esta é uma prévia instalável para validação manual; não há alegação de homologação interativa em todos os computadores Windows 10/11.
