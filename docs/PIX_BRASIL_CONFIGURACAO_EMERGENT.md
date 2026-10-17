# Pix Brasil — instrução para o Emergent

Preparado em 17/10/2026. Repositório: `faellt34/NOVORRCLUB`.
Branch: `codex/pix-brasil-readiness`; incorpora as correções de `9c0137f`.

Este documento organiza a configuração já suportada pelo código. Guardá-lo
no GitHub não configura o servidor, ativa pagamentos ou associa parceiros.
Nenhuma chave ou documento de identidade deve ser incluído no repositório.

## Instrução para executar no projeto Emergent

Concluir a configuração da integração Pix existente. Antes de carregar o
código, verificar e preservar alterações locais; não substituir código mais
recente. Confirmar que o projeto incorpora as correções de `9c0137f`.
Preservar dados, `.env`, configuração Portugal e `stripe==14.4.1`.
Não usar a antiga branch `codex/pix-payments`.

Configurar os seguintes valores exclusivamente em Gerenciar → Segredos:

| Variável | Valor a configurar |
| --- | --- |
| `PIX_STRIPE_SECRET_KEY` | Chave da conta brasileira aprovada, com as permissões exigidas pelo backend. |
| `PIX_STRIPE_PLATFORM_COUNTRY` | `BR` |
| `PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION` | ID de configuração da plataforma, exclusiva para Pix, da mesma conta e modo da chave. |
| `PIX_STRIPE_WEBHOOK_SECRET` | Segredo de assinatura do endpoint Pix dedicado, na mesma conta e modo. |
| `PIX_ENABLED` | `false` durante a preparação e validação. |

O modelo sem credenciais já está em
`backend/payments/pix/pix.env.example`. Não substituir as variáveis Stripe
de Portugal. Se um segredo estiver ausente, indicar ao proprietário qual
campo preencher diretamente no painel; não inventar valores nem pedir que
sejam escritos numa conversa ou ficheiro versionado.

Preservar as origens HTTPS reais em `PAYMENT_ALLOWED_ORIGINS` e/ou
`FRONTEND_URL`. Não usar curingas ou destinos de terceiros.

## Checkout e confirmação automática

Criar ou reutilizar uma configuração da plataforma exclusiva para Pix.
Não desligar outros meios numa configuração utilizada por pagamentos
existentes. Guardar o ID em `PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION`.

Registar o endpoint dedicado:

`https://rrclub.online/api/stripe/pix/webhook`

Subscrever os eventos exigidos por `WEBHOOK_EVENTS`, em
`backend/payments/pix/checks.py`:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `checkout.session.expired`
- `charge.refunded`
- `charge.dispute.created`
- `charge.dispute.updated`
- `charge.dispute.closed`

Copiar o segredo de assinatura diretamente para os Segredos do servidor.
O webhook geral de Portugal não substitui este endpoint dedicado.

## Diagnóstico e associação dos destinatários

1. Consultar `GET /api/admin/pix/readiness` como administrador para localizar
   variáveis em falta, sem revelar os seus valores.
2. Executar `GET /api/admin/pix/provider-readiness`: apenas leituras Stripe,
   sem cobranças, transferências ou criação de contas de diagnóstico.
3. Informar cada verificação pendente: país, moeda, cobranças, Pix,
   depósitos habilitados e automáticos, checkout exclusivo, modo consistente
   e webhook registado. Não alterar agendas ou contas bancárias automaticamente.
4. Verificar a associação explícita Paulo → Maraca e a moeda BRL, preservando
   relações válidas. Nunca criar a associação apenas por correspondência de email.
5. Usar o onboarding existente do parceiro e do influenciador para concluir
   os recebimentos brasileiros. Reutilizar `pix_stripe_account_id` válido;
   não criar duplicatas nem substituir contas portuguesas.
6. Confirmar transferências habilitadas, depósitos habilitados e agenda
   automática dos destinatários. Ter uma conta criada não comprova aprovação.

O cadastro dos destinatários usa `/api/partner/pix/connect/onboard` e
`/api/partner/pix/connect/status`. A preparação do onboarding não deve exigir
que cobranças reais sejam previamente ativadas.

## Validação e entrega

Homologar em ambiente separado de teste, com chaves, configuração, webhook,
cadastros e base de teste compatíveis; nunca misturar objetos de teste com
produção. Cobrir pagamento, assinatura do webhook, evento duplicado,
expiração, repasse interrompido e reembolso. Distinguir pagamento confirmado,
divisão em saldo Stripe e depósito bancário.

O fluxo do cliente mantém a referência do pedido e não cobra novamente se
o pagamento já foi confirmado. Preservar as percentagens existentes:
compra original de R$100 → cliente paga R$95 → parceiro R$80,
influenciador R$5 e plataforma R$10 brutos, antes das despesas da plataforma.

Manter `PIX_ENABLED=false` em produção até concluir os requisitos e a
homologação. Não executar cobranças reais, testes pagos de IA, criação de
contas duplicadas ou deploy. Não reimplementar a integração.

Entregar: commit efetivamente carregado, nomes das variáveis presentes ou
ausentes, resultado dos diagnósticos, estado dos destinatários, testes
executados e pendências. O proprietário faz a republicação. Publicar este
documento não comprova configuração do servidor nem autorização da Stripe.

## Referências no projeto

- `backend/routes_pix.py`: checkout, onboarding, estado, webhook e divisão.
- `backend/payments/pix/checks.py`: verificações da operação e destinatários.
- `backend/payments/pix/pix.env.example`: modelo sem segredos.
- `docs/VALIDACAO_PAGAMENTOS_2026-10-17.md`: correções e validação local.
