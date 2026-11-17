# HF11 — Receitas e rolagem — 2.0.12

## Atualizar a receita no produto selecionado

Em Produtos, selecione a linha do boneco e clique **Cadastrar via 3MF / G-code**. O campo **Cadastro** já indica esse produto. Confira o nome e tamanho, selecione as placas, informe quantos produtos completos elas rendem e edite as cores. Confirme e salve. Peso, tempo e cores são substituídos no mesmo ID, preservando anúncios, SKUs e custos congelados.

Para cadastrar outro produto, escolha **Criar novo produto físico** no campo Cadastro e informe nome/tamanho. A cor do filamento não muda automaticamente o nome do produto. Dourado, Preto, Super e tamanhos distintos continuam sendo variantes separadas. Se as seis placas do Metal Sonic rendem um boneco, informe **1** produto completo.

A importação continua substituindo a receita completa: importar novamente o mesmo arquivo não soma o consumo duas vezes. Para um boneco com várias placas, selecione as placas que o compõem na mesma importação. Cores editadas são mantidas quando a quantidade ou as placas mudam.

## Aproveitar consumo em outra variante de cor

1. Selecione o produto de origem e clique **Copiar cores e gramas**.
2. Selecione o produto de destino e clique **Colar / adaptar cores**.
3. Na prévia, edite os nomes das cores, materiais e gramas por unidade. Zero remove a linha. Linhas do mesmo material/cor são somadas.
4. Se desejar, marque **Copiar também o tempo de impressão**. Sem marcar, o tempo do destino é mantido.
5. Clique **Aplicar ao produto selecionado**. Cancelar não altera o banco.

A lista de cores do destino é substituída e o peso total é recalculado. Nome, tamanho, embalagem, custos manuais, outros custos e insumos vinculados continuam pertencendo ao destino. Cores já cadastradas usam seu preço atual em Materiais; novas cores usam o R$/kg informado. Se trocar Prata por Dourado, confira o preço do Dourado.

A cópia fica na memória até fechar o ERP. Alterar a origem depois de copiar não muda a prévia já copiada. Há backup antes de aplicar, histórico de receita e indicação da origem no painel do produto. Pedidos com custos congelados conservam esses valores; custos ainda pendentes podem ser preenchidos pela nova receita, com data atual.

## Rolar as telas

- Roda do mouse: vertical.
- **Shift + roda**: horizontal, inclusive nas tabelas de cores e na importação.
- Trackpad: movimentos verticais e horizontais, inclusive diagonais.
- Ao chegar ao início/fim de uma tabela, a rolagem segue no painel externo se houver espaço no mesmo sentido.
- Seletores fechados e campos numéricos não mudam ao passar a roda sobre eles. Abra a lista ou edite o campo para mudar o valor.

A ajuda **Como usar**, no canto de Produtos, traz o fluxo de cópia e importação.

## Instalar

Faça backup, feche o ERP e execute **ForgeonStudioERP-2.0.12-Windows-x64-Setup.exe** na mesma conta/pasta. Não desinstale nem apague a pasta de dados. Atualização cumulativa, esquema 6 preservado. Receitas antigas divergentes continuam em Revisar conflitos para evitar sobrescrever valores sem revisão.
