"""Ajuda contextual local, sem internet nem alteração de dados."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QTextBrowser,QPushButton

GUIDES={
'Visão geral':('Ler o painel mensal',['Escolha o mês e clique Atualizar painel.','Confira receitas, custos conhecidos e unidades sem receita.','Use os atalhos para cadastrar, importar ou corrigir pendências.'],'Filamento e horas são estimados pela receita × quantidade. A Enviar é previsão; não comprova impressão. Caixa estimado não é saldo bancário.'),
'Produtos':('Cadastrar um produto físico',['Use Cadastrar via 3MF / G-code ou Cadastro manual.','Selecione as placas do mesmo produto e quantos produtos COMPLETOS elas rendem.','Revise material, cor, preço por kg e embalagem; salve e confira a precificação.'],'Peças na placa não são unidades vendidas. SKU e anúncio não definem sozinhos o produto. Arquivar preserva pedidos.'),
'Custos e cores':('Manter materiais e referências',['Cadastre ou edite material, cor e preço por kg.','Defina gramas de cada cor por unidade; zero remove a cor.','Copie receitas entre produtos se necessário e confira o destino.'],'Preços alteram o custo atual do catálogo, não os custos já congelados nas vendas. Compra de filamento é registrada em Financeiro.'),
'Precificação':('Simular e consultar preços',['Selecione um produto completo.','Confira a composição do custo e os parâmetros de venda.','Use Simulador para testar alterações sem gravar no cadastro.'],'Margem é lucro/preço; acréscimo é lucro/custo. Custo manual substitui material, energia e máquina; taxas precisam ser revisadas pelo usuário.'),
'Catálogo':('Corrigir origens e SKUs',['Busque anúncio, variação ou SKU.','Vincule a origem ao produto físico correto.','Revise conflitos em vermelho; reserve códigos quando precisar.'],'Não una personagens, cores ou tamanhos diferentes para esconder conflito. SKU original dos pedidos e custos congelados são preservados.'),
'Pedidos':('Conferir vendas detalhadas',['Busque o ID ou SKU original e filtre status.','Abra Ver itens para conferir variação, quantidade, gramas e custo.','Após completar cadastros, congele custos pendentes se desejar registrar a estimativa atual.'],'Reimportar atualiza apenas IDs presentes. O arquivo deve trazer todos os itens de cada ID. Congelamento posterior usa a data atual, não inventa custo histórico.'),
'Importações':('Importar com revisão',['Escolha Pedidos XLSX e confira o mapeamento.','Leia a comparação: novos, alterados, repetidos e períodos sobrepostos.','Confirme somente depois de revisar os valores e itens.'],'Order.toship cobre só A Enviar. Estatísticas ficam separadas dos pedidos. Cadastros/despesas adicionam registros, diferentemente da reimportação por ID.'),
'Financeiro':('Lançar despesas e compras',['Cadastre despesas por data/categoria.','Registre compras de filamento com peso, valor e frete.','Compras novas criam um rolo/lote de massa no Estoque; confira o saldo físico.'],'Compras anteriores à atualização não viram estoque disponível automaticamente. Compra afeta caixa; consumo compõe produção, sem descontar ambos no resultado operacional.'),
'Relatórios':('Consultar e exportar',['Escolha período, produto, status e filtros adicionais.','Salve um filtro para reutilizar ou ajuste as datas.','Exporte XLSX/PDF ou use botão direito nos gráficos para PNG.'],'Filtros por cor/material selecionam itens que usam essas cores; não atribuem receita a uma cor. Despesas gerais e repasses continuam do período completo. Gráficos e exportações seguem os filtros selecionados.'),
'Configurações':('Configurar e proteger o banco',['Revise custos de fabricação, taxas e método de precificação.','Use Aparência para fonte, contraste, vidro e menu.','Crie backups, confira integridade e exporte diagnóstico quando necessário.'],'Diagnóstico contém versões, contagens e integridade; não inclui compradores, SKUs, nomes comerciais, caminhos pessoais nem detalhes do histórico. Nenhum diagnóstico é enviado automaticamente.'),
'Atualizações':('Baixar um hotfix',['Clique Verificar atualizações somente quando quiser consultar.','Leia as notas e baixe o instalador para a pasta escolhida.','Faça backup, feche o ERP e execute o arquivo manualmente.'],'Não há instalação automática. A gestão local funciona sem internet. Um backup de esquema antigo é convertido em estágio ao restaurar, sem alterar o arquivo original.'),
'Pendências':('Resolver o que falta',['Filtre o tipo ou procure uma referência.','Selecione uma linha e use Abrir cadastro.','Na revisão em lote, escolha explicitamente um produto para cada origem e confirme.'],'Não há fusão automática por semelhança. Custos pendentes preenchidos agora são estimativas de cadastro; valores históricos já congelados não são recalculados.'),
'Produção':('Organizar lotes e registrar perdas',['Sincronize pedidos A Enviar com produto reconhecido, ou crie lote avulso.','Agrupe necessidades por produto e confira reservas por cor/material.','Mude a etapa; ao marcar Pronto, confirme a baixa por receita. Registre perdas/reimpressões à parte.'],'Reserva não diminui o saldo físico. Pronto dá baixa uma única vez e exige estoque suficiente e receita completa. Cancelar não devolve material já usado. Perdas são custo adicional modelado, não nova saída de caixa observada.'),
'Estoque':('Controlar gramas por rolo/lote',['Cadastre o saldo físico atual de cada rolo, material e cor.','Confira reservado, disponível e faltas para lotes abertos.','Quando pesar um rolo, ajuste o saldo com um motivo; consulte movimentações.'],'Baixas seguem a receita confirmada e perdas informadas, não sensores da impressora. Compras novas entram como lote; compras antigas precisam de saldo confirmado. Não há inventário fiscal ou custo médio contábil.'),
'Simulador':('Comparar um cenário sem alterar cadastro',['Selecione o produto e revise as taxas/margem do cenário.','Teste variação do filamento, energia, máquina e embalagem.','Compare custo, preço sugerido e retorno por hora; exporte o resultado.'],'Nada é gravado nos custos do produto. O preço médio observado é dos itens antes de cupons do pedido; o lucro exibido sobre ele usa as taxas simuladas, não é lucro histórico comprovado.'),
'Repasses':('Conciliar recebimentos',['Registre o repasse efetivamente recebido, com referência única.','Vincule parcelas do repasse a pedidos já importados, ou importe o modelo XLSX.','Confira diferença para a previsão dos pedidos e valores ainda não vinculados.'],'Recebimentos não são somados novamente às vendas. O caixa por recebimentos usa datas reais informadas, sem saldo inicial nem conciliação bancária completa. Taxas já retidas não são descontadas outra vez do depósito líquido.'),
}
SUBTABS={
'Resultado':'Receita menos taxas, reembolsos, produção, perdas modeladas e despesas. Caixa estimado não é saldo bancário; compra de material não é novamente custo de produção.',
'Mais vendidos':'Unidades incluem devoluções, coerentes com produção. Use a comparação por produto para avaliar contribuição antes das despesas gerais; receitas/custos incompletos são destacados.',
'Consumo':'Consumo previsto é receita congelada por unidade × quantidade. Cores não informadas permanecem pendentes; cancelados são excluídos desta estimativa.',
'Histórico mensal':'Comparativo mensal geral, sem os filtros de produto/status da consulta. Diferenças e dados parciais permanecem sinalizados.',
'Estatísticas de anúncios':'Resumo por anúncio/período, separado dos pedidos. Nunca soma novas vendas nem inventa variantes físicas. Sobreposição é recusada para o mesmo anúncio.',
'Gráficos':'Passe o mouse para valores. Botão direito salva PNG; PDF e XLSX seguem o período e os filtros. Não há atribuição de receita por grama de cor.',
'Itens · gramas e horas':'Mostra SKU original, variação, consumo e duração por unidade e total, com data do snapshot. Custos preenchidos depois do pedido usam a data atual.',
'Valores por pedido':'Receita de produtos e taxas por pedido. Frete do comprador, Valor Total e Total global são referências separadas; não os some como novas receitas.',
'Desempenho por produto':'Contribuição antes de despesas gerais, por unidade/hora quando o tempo é conhecido. Cadastros incompletos não são tratados como lucro completo.',
'Despesas':'Lançamentos gerais por data/categoria. Evite lançar compra de filamento como despesa e também como compra: isso duplica valores.',
'Compras de filamento':'Peso, material, valor e frete. Compra nova cria lote de estoque; editar o financeiro não reconta material já utilizado. Corrija massa pelo ajuste de estoque.',
'Lotes':'A produzir → Em impressão → Acabamento → Pronto. Pronto dá baixa de massa uma vez. Atualização de pedido/quantidade exige revisão do lote iniciado.',
'Necessidades':'Agrupa lotes abertos por produto. Para reservar e avaliar faltas por cor/material, consulte Estoque. Lotes sem receita completa precisam de revisão.',
'Perdas e reimpressões':'Registre gramas/horas adicionais e motivo. Se a massa já foi baixada, marque essa opção para não baixá-la duas vezes. Estorno conserva o histórico e devolve apenas os movimentos daquele registro.',
'Materiais':'Saldo por material/cor, reserva dos lotes abertos e falta prevista. Um rolo não cadastrado não é presumido disponível.',
'Rolos/lotes':'Cada entrada mantém saldo e movimentações. Cadastre rolos parcialmente usados pelo peso restante, não necessariamente pelo peso da embalagem.',
'Movimentações':'Entradas, ajustes e baixas com motivos e referências. Ajuste físico não é uma compra nem uma venda.',
'Recebimentos':'Datas e valores efetivos informados. Referência única permite reimportar sem duplicar o repasse.',
'Vínculos de recebimentos':'Alocações explícitas entre recebimentos e pedidos. Remover um vínculo preserva ambos. Esta lista mostra todo o histórico, independentemente dos filtros de datas.',
'Conciliação por pedido':'Previsão líquida do pedido comparada com recebimentos vinculados. Diferença pode refletir critério do marketplace; revise, não presuma erro ou liquidação.'}


def help_text(title):
    title={'Desempenho de produtos':'Desempenho por produto'}.get(title,title)
    if title in SUBTABS:return '# '+title+'\n\n'+SUBTABS[title]+'\n\nUse os filtros e exportações da aba principal. Nenhuma ação é executada ao abrir esta ajuda.'
    title={'Importação com revisão':'Importações','Desempenho de produtos':'Desempenho por produto'}.get(title,title)
    key=next((key for key in GUIDES if key.casefold() in title.casefold()),None)
    if key is None:return '# Como usar\n\nSelecione um registro e confira os campos antes de salvar. Dados incompletos são sinalizados; use F1 na aba principal para instruções.'
    heading,steps,note=GUIDES[key]
    return '# '+heading+'\n\n'+'\n'.join(f'{i}. {step}' for i,step in enumerate(steps,1))+'\n\n## Como interpretar\n\n'+note+'\n\n**Atalhos:** F1 abre ajuda; Ctrl+F busca global; Ctrl+N cadastra produto; Ctrl+I importa pedidos.\n\nTabelas: clique no cabeçalho para ordenar, arraste colunas e use botão direito para ocultar, copiar ou exportar.'


def show_help(parent,title):
    dialog=QDialog(parent);dialog.setWindowTitle('Como usar · '+title);dialog.resize(720,540)
    layout=QVBoxLayout(dialog);browser=QTextBrowser();browser.setMarkdown(help_text(title));layout.addWidget(browser)
    close=QPushButton('Entendi');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.exec()
