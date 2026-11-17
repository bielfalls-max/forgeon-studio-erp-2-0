# HF10 — Catálogo físico automático — 2.0.11

A tela Produtos passa a representar o personagem físico e sua receita. Títulos de anúncio, SKUs e contagem de origens deixam de aparecer nessa lista; continuam internamente nos vínculos e no catálogo de anúncios para a importação.

## Correção da versão anterior

O HF09 normalizava nomes, mas ainda dependia de uma confirmação de unificação, e títulos de anúncio legados podiam impedir a identidade. O HF10 reconhece esses títulos pelos vínculos de origem mesmo quando a observação automática antiga não existe. O título não define personagem ou tamanho.

Grupos compatíveis são unificados automaticamente ao abrir o ERP, abrir Produtos ou importar vendas. Há backup antes de alterar; os cadastros repetidos são arquivados e os anúncios/itens passam ao produto mantido. Não é necessário clicar em unificar para corrigir grupos vazios ou com receitas compatíveis.

Amy e Amy Rose usam um único cadastro Amy Rose. Os registros de Metal Sonic provenientes de anúncios distintos usam um único produto por tamanho. As aliases conhecidas e nomes repetidos são normalizados sem busca aproximada. Sonic, Super Sonic, Metal Sonic e Shadow continuam distintos.

A medida explícita na variação ou no modelo físico é preservada: 12 cm e 16 cm são produtos diferentes. O padrão informado para personagens reconhecidos sem medida continua 12 cm. Uma medida presente só no título do anúncio não é atribuída a todas as opções. Se esse título for a única informação da medida, edite o modelo físico para indicar o tamanho correto. Não se inventa uma versão 16 cm que ainda não apareceu.

## Receita cadastrada uma vez

Cadastre/complemente o produto físico pelo 3MF/G-code e vincule embalagens/insumos por unidade. As próximas vendas reconhecidas como esse personagem e tamanho consultam a mesma receita, mesmo quando vêm de outro anúncio. Gramas, tempo e custo vêm da receita; a planilha de vendas não fornece esses dados de fabricação.

Custos históricos já congelados não são recalculados. Itens pendentes de custo podem receber a receita atual, com registro da data atual, pelo fluxo existente de resolução de cadastros. Receitas/revisões antigas permanecem preservadas.

## Exceções

Grupos com receitas, insumos ou custos conflitantes não são unidos automaticamente. Use Revisar conflitos para conferir o grupo e editar os cadastros antes de tentar novamente. Nomes/variantes desconhecidos e tamanhos não claros continuam conservadores. A automação não adivinha o consumo nem escolhe uma receita divergente.

Instale com o ERP fechado, na mesma conta e pasta, após backup. Não precisa reimportar os arquivos para corrigir os vínculos já existentes. O esquema permanece 6.
