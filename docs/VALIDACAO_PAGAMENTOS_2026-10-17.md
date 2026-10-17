# Validação para republicação — 17/10/2026

Base: `codex/pix-brasil-readiness`, commit `6ec0ae8`. Esta revisão acrescenta
correções à preparação Pix existente; não substitui a integração nem altera
os destinatários ou percentagens dos pagamentos.

## Correções

- A rota geral de estado só confirma pagamentos com `payment_status=paid`.
  `status=complete` por si só não confirma recebimento. O cenário anterior
  foi reproduzido localmente com checkout completo e pagamento não pago.
- O webhook geral exige o campo de pagamento explicitamente pago; campo
  ausente não é presumido como pago.
- Cobranças `pix_coupon` são excluídas da confirmação e expiração gerais.
  Usam `/api/payments/pix/status/{identifier}` e
  `/api/stripe/pix/webhook`, com a chave e segredo brasileiros próprios.
  Isso impede o fluxo geral de criar uma subscrição a partir de um Pix.
- A consulta de configuração Stripe deixa de criar/fechar contas de
  diagnóstico. Usa leituras e identifica aprovação do perfil como não
  verificada; o painel indica a necessidade de conferência na Stripe.

## Fontes dos vídeos

As fontes `LiberationSans-Bold.ttf` e `LiberationSans-Regular.ttf` já estão
versionadas em `backend/assets/fonts/`. O carregamento já tem fallback PIL.
Os testes confirmaram a leitura das duas fontes e desenho de texto português
quando o caminho de uma fonte opcional não existe. Não foram substituídas
fontes nem reimplementadas correções existentes.

## Validação executada

- 118 testes de backend passaram: confirmação de pagamentos, Pix,
  disponibilidade do provedor, registo, regras monetárias, associação de
  parceiros, IBAN e geração de vídeos.
- 28 testes de frontend passaram, em seis suites.
- Compilação de produção do frontend concluída: `main.2199d2ab.js`.
- `git diff --check` sem erros.
- Backend executado com `stripe==14.4.1`; não houve atualização de SDK.
- Testes usam simulações e base em memória: sem Stripe real, banco,
  pagamentos, email ou IA pagos.

## Estado observado e limites

- O site respondeu a `/api/public/pix/availability` com `configured=false`,
  `enabled=false`, `accepting_new_payments=false` durante a análise.
- A área restrita RRCLUBRASIL está autorizada para leitura; nela o Pix ainda
  aparece indisponível/desligado e não existem endpoints de webhook.
- Na conta RRCLUB de produção autorizada não foi encontrado o Pix de R$1
  mostrado pelo proprietário na conta P Sphere Tec. Não há acesso autorizado
  a essa conta; não foi confirmada a divisão dessa transação.
- A consulta dos logs de produção expirou. Não foi realizada auditoria de
  todos os logs nem certificação do estado da base de produção.
- Testes locais e build não comprovam entrega de webhooks, aprovação KYC,
  liquidação, depósitos bancários ou concorrência num MongoDB real.

## Republicação

Carregar a versão atualizada de `codex/pix-brasil-readiness` no projeto
Emergent antes de republicar, preservando eventuais alterações locais,
dados e segredos. Republicar uma cópia antiga não importa automaticamente
o código novo do GitHub.

Manter `PIX_ENABLED=false`, configurações de Portugal, `.env` e
`stripe==14.4.1`. A aprovação da produção brasileira deve ser confirmada
na Stripe após a verificação documental e restantes requisitos. A ativação
real exige configurar as chaves no servidor, checkout Pix, webhook dedicado,
destinatários e homologar o fluxo completo em teste. Não inserir segredos no
GitHub. Esta revisão não executa deploy nem altera a Stripe ou dados reais.

Referências oficiais para confirmação e operação:

- https://docs.stripe.com/checkout/fulfillment
- https://docs.stripe.com/payments/pix
- https://docs.stripe.com/connect/separate-charges-and-transfers
- https://docs.stripe.com/webhooks
