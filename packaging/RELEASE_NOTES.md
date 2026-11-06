# HF01 · Alpes — FORGEON STUDIO ERP 2.0.1

Baixe **ForgeonStudioERP-2.0.1-Windows-x64-Setup.exe** nos Assets. Faça backup em Configurações, feche o ERP e execute o Setup. Não precisa instalar Python, apagar banco nem desinstalar a versão 2.0.0.

- Novo tema de vidro fosco: painéis arredondados com reflexo, paisagem dos Alpes suíços e modo foco.
- Ícone Forgeon com Banguela na janela, executável, instalador e atalhos.
- Painel com indicadores e pendências, gráficos de vendas, custos, mais vendidos e consumo por cor/material.
- Exportação PDF do relatório e PNG dos gráficos, além das planilhas XLSX.
- Colunas ordenáveis, reorganizáveis e ocultáveis; cópia de linha e exportação das colunas visíveis.
- Área Atualizações com versão instalada e histórico local de hotfixes.
- Consulta e download dos próximos hotfixes somente por escolha do usuário, com progresso, cancelamento, backup prévio e SHA-256. O instalador nunca é executado automaticamente.
- Mantém banco, backups e custos congelados do ERP 2.0.0. Nenhuma migração do esquema.

A 2.0.0 não possui o botão de atualização; instale este primeiro hotfix pelo Setup. Na 2.0.1, use Atualizações para consultar os próximos.

As imagens são recursos locais, incluídos no instalador. O ícone é uma ilustração de fã solicitada pelo usuário, sem afiliação ou endosso à franquia. O aplicativo não inclui IA, geração de imagens, rastreamento ou atualização automática.

As evidências anexadas a esta Release registram os testes, a atualização de 2.0.0 com banco e backup de teste preservados e as verificações reais do executável/instalador em Windows Server 2022 do GitHub Actions. A validação manual no seu computador Windows 10/11, com arquivos reais, continua necessária. O executável não tem assinatura digital comercial. Não foi realizado laudo antivírus; testes funcionais não garantem ausência de alertas.

`SHA256.txt` permite conferir a integridade do instalador. Banco e backups ficam em `%LOCALAPPDATA%\ForgeonStudioERP2`, separados da instalação. Se o Defender bloquear, não desative a proteção nem crie exceções.
