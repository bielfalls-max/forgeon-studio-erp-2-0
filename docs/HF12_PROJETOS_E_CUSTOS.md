# HF12 — Projetos e custos — 2.0.13 — 20/11/2026

## Importar todas as placas

**Fatiar todas** e **exportar todas** são ações diferentes. Um G-code comum contém uma placa. A lista de cores configuradas no cabeçalho não significa que todas foram usadas nessa placa, nem que os outros G-codes estão no arquivo.

Em Produtos → Cadastrar via 3MF / G-code, selecione:

- **Um 3MF fatiado** com os metadados de todas as placas; ou
- **Vários G-codes juntos**, um de cada placa, usando Ctrl/Shift no seletor de arquivos.

Confira as placas e informe quantos **produtos completos** elas rendem. Se seis placas formam um boneco, informe **1**. Gramas por cor e tempo são somados e divididos por essa quantidade. Arquivos idênticos e mistura de 3MF com G-codes são bloqueados para evitar dupla contagem. Limites: 64 arquivos e 128 MB no total. Não são executados comandos das impressoras.

A importação no produto selecionado continua substituindo a receita completa, sem criar outro cadastro. Cores editadas são preservadas ao recalcular placas/quantidade. O parser Bambu usa o slot realmente impresso, em vez de atribuir o peso total à primeira cor da paleta.

## Simular o projeto antes de cadastrar

1. Abra Precificação → **Simular por G-code / 3MF**.
2. Selecione os arquivos como acima; confira placas, quantidade completa, cores, R$/kg e embalagem.
3. Escolha a impressora ou a média geral configurada.
4. Clique **Calcular custo do projeto**.

A composição exibe filamento, energia, máquina, reserva de perdas, mão de obra, embalagem, outros e custo por unidade. O preço sugerido usa as taxas e a margem atuais. A simulação não grava produtos, filamentos ou pedidos. Alterar os campos invalida a prévia anterior; recalcule para consultar o novo custo. Se faltarem peso ou tempo, o orçamento é parcial e o preço não é sugerido.

Os totais são calculados com precisão decimal antes de arredondar para centavos; pode haver um centavo de diferença em relação à soma de componentes exibidos já arredondados.

## Custos iniciais solicitados

| Componente | Referência inicial | Como editar |
| --- | --- | --- |
| Embalagem | R$ 0,53 por unidade | Editar produto, campo da importação/simulação ou padrão em Editar custos e taxas |
| Mão de obra | R$ 2,00 por unidade | Editar custos e taxas |
| Reserva de perdas/reimpressão | 10% da fabricação | Editar custos e taxas |
| Energia São Paulo | R$ 1,10/kWh, estimativa provisória | Editar custos e taxas; substitua pelo custo efetivo da sua conta |
| Média geral das três máquinas | 140 W estimados | Editar custos e taxas |
| Máquina | R$ 1,00/h, reserva provisória de desgaste/manutenção | Editar custos e taxas ou Perfis de impressoras |

**Fabricação calculada = filamento + energia + máquina.** Custo por unidade = fabricação × 1,10 + mão de obra + embalagem + outros/insumos vinculados. Se houver fabricação manual informada, ela substitui a fabricação calculada; reserva e mão de obra continuam como campos separados. A reserva é um acréscimo orçamentário de 10%, não uma probabilidade de falha convertida por divisão de rendimento, nem baixa real de filamento.

Não duplique a mão de obra em Outros nem a mesma embalagem no campo Embalagem e em um insumo vinculado. A mão de obra é por produto completo; não por peça, placa ou hora de impressão.

Ao atualizar, o novo padrão de embalagem preenche cadastros com embalagem zero **sem insumos vinculados**. Embalagens já preenchidas e produtos com insumos vinculados são mantidos. O padrão também vale para novos cadastros e produtos derivados das vendas. Alterá-lo depois não substitui automaticamente embalagens de produtos existentes. As novas chaves de custos são incluídas uma vez; energia/potência com os antigos padrões 1 R$/kWh e 150 W passam a 1,10 e 140, respectivamente. Referências diferentes desses padrões são preservadas. Edições posteriores não são desfeitas ao reabrir.

## Impressoras e limites das estimativas

| Perfil | Consumo médio assumido para orçamento PLA | Energia estimada por hora a R$ 1,10/kWh |
| --- | --- | --- |
| Bambu Lab A1, 110/127 V | 120 W | R$ 0,132 |
| Flashforge AD5X, 110/127 V | 150 W | R$ 0,165 |
| Creality SPARKX i7, 110/127 V | 150 W | R$ 0,165 |

São **hipóteses conservadoras editáveis**, não médias medidas dessas máquinas nem valores fornecidos pelos fabricantes. Material, temperatura da mesa, ambiente, aquecimento inicial e acessórios variam o consumo. Tensão de alimentação não determina sozinha o consumo por hora. O orçamento geral usa a média aritmética dessas três hipóteses, 140 W.

R$ 1/h de máquina é uma reserva provisória igual nos três perfis, pois não há preços pagos, vida útil e manutenção individuais. Para ajustar: custo/h = (investimento − valor residual) ÷ vida útil produtiva em horas + manutenção/h. Por exemplo, R$ 4.000 ÷ 5.000 h + R$ 0,20/h = R$ 1/h; esse exemplo não é um preço de mercado das impressoras.

Escolha o perfil ao importar a receita. O perfil fica vinculado ao produto e suas referências podem ser editadas em **Perfis de impressoras**. Produtos sem perfil explícito usam consumo e máquina gerais. Alterações afetam estimativas futuras, sem reescrever custos de pedidos congelados. Para vincular um perfil a um cadastro antigo, importe a receita no mesmo produto e escolha a impressora.

### Fontes consultadas

- [Enel São Paulo — Tarifa de Energia Elétrica](https://www.enel.com.br/pt-saopaulo/Para_Voce/tarifa-energia-eletrica.html), consultada em 20/11/2026. A página informa B1 residencial convencional: TUSD R$ 472,42/MWh + TE R$ 316,96/MWh = **R$ 0,78938/kWh**, conforme resolução 3.596/2026, vigente desde 04/07/2026. Isso não equivale ao custo final da conta com tributos, bandeiras e demais itens. Por isso, R$ 1,10/kWh é uma **referência de orçamento**, não uma tarifa oficial garantida para a residência.
- [Creality — SPARKX i7, especificações](https://store.creality.com/products/sparkx-i7-3d-printer), consultada em 20/11/2026: potência nominal 400 W a 110 V e 700 W a 220 V. Esses números são nominais e não foram usados como consumo médio contínuo. Os 150 W do perfil são uma hipótese provisória de orçamento.

## Atualizar

Faça backup, feche o ERP e instale **ForgeonStudioERP-2.0.13-Windows-x64-Setup.exe** na mesma conta/pasta. Instalador cumulativo, esquema 6 preservado. Há backup antes da primeira inclusão das referências. Arquivos pessoais de G-code e planilhas não acompanham a distribuição.
