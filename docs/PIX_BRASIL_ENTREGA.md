# Pix Brasil — entrega e bloqueios de ativação

Base: `mainNNOVO`, commit `627acfa`. Branch de trabalho: `codex/pix-brasil-readiness`.
Data: 17/10/2026. Sem deploy, cobrança, criação de conta ou alteração Stripe nesta revisão.

## O que foi confirmado diretamente na Stripe

Consulta autorizada, apenas leitura, à conta RRCLUB em produção:

- País PT, liquidação EUR; cobranças e depósitos habilitados; capacidade `pix_payments` ativa.
- Existem duas configurações de métodos: a configuração própria permite Pix e vários outros métodos; a configuração vinculada a uma aplicação está com Pix indisponível/desligado. Nenhuma é exclusiva para Pix.
- Foram listadas seis contas conectadas, todas PT/EUR. Não foi disponibilizada uma plataforma brasileira nesta sessão. Não associar esses resultados a um estabelecimento específico sem correspondência de IDs confirmada.
- Dois webhooks habilitados: `/api/stripe/webhook` (todos os eventos) e `/api/webhooks/stripe` (eventos PaymentIntent). Nenhum endpoint `/api/stripe/pix/webhook` listado nessa conta.
- O endpoint genérico não substitui automaticamente o handler dedicado: este usa `PIX_STRIPE_WEBHOOK_SECRET` e a conciliação de `pix_coupon`.

Pix ativo numa conta portuguesa permite um contexto diferente de cobrança; não comprova a permissão de transferir BRL para restaurantes e influencers brasileiros. Não foi feito teste externo da liquidação transfronteiriça. O fluxo atual exige plataforma BR e destinatários BR; não removemos esse bloqueio nem usamos chaves portuguesas como brasileiras.

A consulta pública do site nesta revisão devolveu `configured=false`, `enabled=false`, `accepting_new_payments=false`. Não foram lidos valores de segredos.

## Funcionamento já existente e preservado

O influencer divulga o cupom. No estabelecimento, o parceiro autenticado informa o valor original e gera uma cobrança. O cliente abre o checkout Stripe e paga pelo QR Pix ou copia e cola. O QR/link da campanha não é uma cobrança financeira.

Sobre R$100 originais: cliente paga R$95, parceiro R$80, influencer R$5, plataforma retém R$10 brutos antes de custos. O servidor calcula em centavos; não usa tarifas inventadas. A RRCLUB suporta custos de processamento e transferências. Campanhas com desconto/comissão diferentes de 5% continuam bloqueadas neste fluxo fixo.

A confirmação assinada ou a consulta do servidor à Stripe verifica pedido, sessão, valor e moeda antes de registar a venda. Os dois repasses são independentes e usam referências idempotentes. Se um repasse falhar, o cliente não deve pagar novamente. Reembolsos e disputas têm registo e retenção próprios. Repasse ao saldo Stripe e depósito bancário são momentos diferentes.

## Mudanças nesta entrega

- Pasta `backend/payments/pix/`: verificações puras, eventos obrigatórios e modelo de configuração sem segredos.
- Antes de cobrar: país BR, BRL, cobranças e Pix ativos na plataforma; configuração ativa só Pix e modo consistente; destinatários BR distintos, habilitados e sem metadados de outro cadastro.
- Proteção de associação e suspensão também na rota de cobrança Pix e no onboarding do parceiro.
- Estado de recebimento considera transferências e depósitos; não exige que o destinatário receba cartões diretamente. Falhas de consulta preservam estado guardado.
- Novo diagnóstico administrativo com chamadas GET à Stripe, incluindo webhook registado. Não ativa Pix nem prova entrega real de eventos.
- Cliente HTTP com timeout de 15 segundos e sem repetição automática; idempotência preservada. QR financeiro expira 10 minutos após confirmação do PaymentIntent.
- Removido `integration_identifier` da chamada de criação: a versão Stripe 14.4.1 do projeto usa versão de API anterior ao parâmetro. Não alteramos a dependência preservada pelo Emergent.
- Painel brasileiro deixa de prometer transferência manual por IBAN; passos numerados corretamente; botão de cobrança explica e bloqueia Pix ainda desativado.

## Como concluir a ativação

1. Confirmar uma plataforma Stripe brasileira elegível para esta divisão local, ou obter da Stripe uma alternativa formalmente suportada antes de mudar a arquitetura. Pix disponível na conta PT não resolve sozinho os repasses BR.
2. Configurar em ambiente de teste isolado os campos do `backend/payments/pix/pix.env.example`: chave da operação BR, configuração `pmc_` exclusiva Pix, webhook dedicado e origens HTTPS reais. Nunca publicar chaves no GitHub/chat/frontend.
3. Completar o onboarding dos destinatários brasileiros pelo fluxo existente. Preservar `stripe_account_id` de Portugal; as contas BR usam `pix_stripe_account_id`. Antes de criar outra conta para alguém já conectado, confirmar país e plataforma da conta existente; não duplicar por suposição.
4. No painel de Definições, usar **Verificar Stripe sem cobrar**. Um resultado positivo valida configuração, não substitui homologação.
5. Em sandbox: ativar Pix apenas nesse ambiente; simular pagamento, demora, expiração, evento duplicado, resposta interrompida, repasses, reembolso e disputa. Conferir valores 95/80/5/10 e custos reais do contrato. Confirmar chegada do webhook dedicado e contas destinatárias habilitadas.
6. Só após homologação e configuração real confirmada: usar segredos live corretos e autorizar a ativação em produção. `PIX_ENABLED=false` não foi alterado por esta entrega.
7. Carregar esta branch/commit no Emergent preservando alterações atuais e configurações; o proprietário republica. Salvar no GitHub não atualiza o workspace do Emergent automaticamente.

Eventos do endpoint dedicado: `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `charge.refunded`, `charge.dispute.created`, `charge.dispute.updated`, `charge.dispute.closed`.

## Limites

Não foram acessados segredos do Emergent, alterados cadastros ou destinos financeiros, criadas contas Stripe ou feitas cobranças. Não há certificação de Pix BR real a partir de testes mockados. A repetição concorrente dos webhooks, reembolsos e repasses deve ser homologada com MongoDB e Stripe de teste antes de liberar produção. A migração global de Accounts v1 para v2 não integra este patch.

## Referências oficiais consultadas

- https://docs.stripe.com/payments/pix
- https://docs.stripe.com/payments/pix/accept-a-payment?payment-ui=checkout
- https://docs.stripe.com/payments/payment-methods/payment-method-connect-support
- https://docs.stripe.com/connect/separate-charges-and-transfers
- https://docs.stripe.com/connect/cross-border-payouts
- https://docs.stripe.com/checkout/fulfillment

## Validação local

95 testes backend passaram com `stripe==14.4.1` (a versão preservada pelo Emergent); 22 testes frontend passaram; build de produção compilou com sucesso. Os testes executados usam mocks; nenhum custo de IA ou pagamento de teste real.

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_pix_service.py backend/tests/test_pix_readiness.py backend/tests/test_pix_registration.py backend/tests/test_payment_policy.py backend/tests/test_partner_association_repairs.py backend/tests/test_partner_iban_association.py backend/tests/test_partner_flow_repairs.py backend/tests/test_story_jobs.py -q
cd frontend
CI=true npm test -- --watch=false --runInBand
CI=true GENERATE_SOURCEMAP=false npm run build
```
