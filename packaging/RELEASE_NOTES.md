# HF12 · Projetos e custos — 2.0.13

Baixe **ForgeonStudioERP-2.0.13-Windows-x64-Setup.exe**, faça backup, feche o ERP e instale na mesma conta/pasta.

**Todas as placas:** selecione um 3MF fatiado ou os G-codes de cada placa juntos. Um G-code isolado não inclui automaticamente as outras placas fatiadas. O ERP avisa isso e bloqueia arquivos idênticos/mistura com 3MF para não duplicar consumo. Corrige a leitura Bambu de slot, cor e material realmente utilizados.

**Orçamento sem cadastro:** em Precificação → Simular por G-code / 3MF, confira placas, unidades completas, cores, kg e impressora; calcule sem criar produtos ou materiais. Campos ausentes deixam o orçamento parcial.

**Custos editáveis:** embalagem R$ 0,53/un., mão de obra R$ 2/un. e reserva de 10% sobre fabricação. Energia SP com referência provisória R$ 1,10/kWh; perfis PLA estimados A1 120 W, AD5X 150 W e SPARKX i7 150 W, com reserva provisória de máquina R$ 1/h. São hipóteses de orçamento, não medições ou tarifa final garantida. As referências podem ser alteradas em Editar custos e taxas / Perfis de impressoras.

Padrões são aplicados uma vez, preservando referências personalizadas e embalagens já preenchidas. Embalagem zero recebe o padrão quando não há insumos vinculados; confira para não duplicar embalagens. Custos congelados dos pedidos são mantidos. Backup antes da inclusão inicial; esquema 6 preservado.

[Guia, fórmula e fontes](https://github.com/bielfalls-max/forgeon-studio-erp-2-0/blob/main/docs/HF12_PROJETOS_E_CUSTOS.md). Prévia com testes automatizados de negócio, interface, executável e atualização Windows.
