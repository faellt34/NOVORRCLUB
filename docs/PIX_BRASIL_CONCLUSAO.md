# RRClub Brasil — cobrança, conversão e recebimentos automáticos

Revisão de 17/10/2026, sobre `codex/pix-brasil-readiness` (`5b2f284`). Sem deploy ou operações financeiras.

## Solução para o fluxo existente

1. O seguidor apresenta o cupom/QR da campanha na loja.
2. O parceiro autenticado lê o cupom e confirma o valor original da compra.
3. O servidor calcula o desconto, guarda a campanha e os destinatários e gera uma cobrança Pix identificada.
4. O cliente abre a cobrança e paga no aplicativo do banco. O QR do cupom e o QR financeiro têm funções diferentes.
5. O webhook assinado confirma o pagamento; uma consulta do servidor pode reconciliar a mesma cobrança. Gerar QR ou abrir uma página de sucesso não confirma a venda.
6. A conversão é registada uma vez. O servidor transfere as partes do parceiro e influencer; a parte da RRClub permanece no saldo da plataforma, antes das despesas.
7. Os depósitos automáticos enviam os saldos disponíveis às contas bancárias cadastradas. Não é preciso enviar para chaves Pix. Confirmação do Pix, divisão e chegada ao banco são etapas distintas.

Regra preservada: numa compra original de R$100, desconto de R$5, cliente paga R$95, parceiro recebe R$80 no saldo Stripe e influencer R$5; RRClub retém R$10 brutos e suporta custos. Não foram alteradas percentagens nem inventadas tarifas. Margem líquida depende do contrato e dos custos reais.

## Correções desta revisão

- Verificar depósitos bancários habilitados e agenda automática diária da plataforma brasileira, além de BRL e Pix ativo.
- Verificar a agenda diária e os recebimentos habilitados de ambos os destinatários antes de criar cobrança. Configuração desconhecida não é tratada como aprovada.
- Painel do parceiro acompanha o pedido, confirma o pagamento e distingue repasses pendentes/concluídos. Após pagamento confirmado, deixa de mostrar QR/link para pagar.
- Falha temporária de repasse não apaga confirmação de pagamento. A consulta devolve o pagamento confirmado e a divisão pendente; nova tentativa retoma os repasses usando as mesmas referências.
- Consultas no painel não se sobrepõem, param após cinco minutos ou estado final, e podem ser retomadas manualmente. Webhooks continuam a ser o mecanismo principal de confirmação.

Estas verificações não configuram contas bancárias, não mudam agendas na Stripe e não comprovam chegada de dinheiro ao banco. A agenda é lida em `settings.payouts.schedule` de Accounts v1, preservando `stripe==14.4.1` e a arquitetura existente.

## Pesquisa de alternativas

| Opção | Confirmação na documentação oficial | Aplicação à RRClub |
| --- | --- | --- |
| Stripe Connect | Cobrança com transferências para vários destinatários; no Brasil, depósitos automáticos diários do saldo disponível. | Aproveita cobrança, reconciliação e repasses já implementados. Exige operação brasileira elegível neste código. |
| Asaas | Checkout Pix com divisão para contas identificadas por `walletId`, valores fixos/percentuais e eventos de pagamento/divisão. | Alternativa técnica; exige novos cadastros, integração e homologação. Percentuais incidem sobre o líquido após taxas, não diretamente sobre o valor original da compra. |
| Pagar.me | Pix com dois ou mais recebedores e notificação do pagamento por webhook. | Alternativa técnica; exige recebedores, contratação compatível, implementação e homologação. |

Recomendação de engenharia: concluir a configuração Stripe Brasil primeiro, por reaproveitar o código existente. Isso é uma avaliação de esforço, não confirmação de aprovação comercial nem comparação de tarifas. Nenhum fornecedor alternativo foi contratado ou integrado nesta revisão.

## O que falta antes de operar com dinheiro real

- Disponibilizar uma operação Stripe brasileira elegível e os seus segredos no ambiente do servidor. Abrir apenas uma conta bancária brasileira não cria essa operação.
- Aprovar/cadastrar os destinatários brasileiros e as suas contas bancárias, incluindo a da RRClub. Verificar elegibilidade da atividade perante o processador.
- Configurar o checkout Pix, o webhook dedicado e as origens HTTPS do site; executar o diagnóstico administrativo existente.
- Homologar confirmação, evento duplicado, expiração, repasse interrompido, reembolso e disputa com MongoDB e Stripe de teste.
- Depois da homologação, configurar produção, ativar e verificar o primeiro ciclo real com autorização específica para a transação. Não foi feita cobrança nesta revisão.

`PIX_ENABLED=false` permanece preservado. Republicar a branch sozinha não substitui estes requisitos. Portugal mantém as suas contas e configurações.

## Verificação local

- 59 testes backend específicos de Pix/cadastros passaram, incluindo novos cenários de depósitos automáticos e interrupção de repasse.
- 6 testes do novo componente passaram com React 19/Jest 29: pendente, pago, repasse pendente, falha de rede, expiração, cancelamento e não sobreposição.
- JSX do painel e do componente compilado isoladamente com Babel; não foi executado novo build completo da aplicação nesta revisão.
- Testes usam mocks; não comprovam movimentação externa nem autorização do processador. Nenhuma chamada paga de IA.

## Fontes oficiais consultadas

- https://docs.stripe.com/payments/pix
- https://docs.stripe.com/connect/separate-charges-and-transfers
- https://docs.stripe.com/payouts#payout-schedule
- https://docs.stripe.com/connect/manage-payout-schedule
- https://docs.asaas.com/docs/checkout-com-split-de-pagamento
- https://docs.asaas.com/docs/split-de-pagamentos
- https://docs.pagar.me/docs/pix-1

## Carregamento no Emergent

Integrar a versão mais recente de `codex/pix-brasil-readiness` preservando alterações atuais e segredos do ambiente. Se houver conflitos, apresentar antes de sobrescrever. Não criar outra integração em paralelo e não publicar automaticamente; o proprietário republica. Depois, executar o diagnóstico Stripe no painel antes de habilitar cobranças.
