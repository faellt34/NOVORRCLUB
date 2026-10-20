# P5 Brasil — ligação parceiro → seguidor (especificação de implementação)

Base: branch RRClub-Brasil. Referência portuguesa: frontend/src/pages/PublicCoupon.jsx e backend/routes_payments.py. Esta branch é isolada e NÃO altera produção.

## Fluxo
1. Seguidor abre /c/:code, podendo introduzir valor e iniciar checkout diretamente.
2. Em alternativa, parceiro autenticado lê QR e informa valor bruto. POST /partner/p5/charges cria intenção PENDENTE com idempotency_key, campaign_id, partner_id, claim/session token, gross_minor, discount_minor, net_minor, currency=brl e expires_at. Não criar redenção nem comissão nesse momento.
3. Página do seguidor consulta GET /public/p5/charges/current?code=... usando token de posse do cupão/sessão (não confiar apenas no código público); mostrar valor bruto, desconto, líquido e botão Pagar. Atualizar por SSE ou polling. Não enviar push/SMS sem consentimento e infraestrutura apropriada.
4. POST /public/p5/charges/:id/checkout cria uma ÚNICA Stripe Checkout Session associada à intenção; oferecer pix e card quando habilitados para a conta BRL; Apple Pay apenas quando disponível via card/Stripe Checkout no dispositivo e domínio elegíveis. Não prometer sempre Apple Pay.
5. Webhook Stripe verificado por assinatura marca 'paid' somente em evento de pagamento realmente confirmado (inclusive métodos assíncronos), de forma idempotente; cria uma redenção financeira única, calcula comissão conforme regra existente e executa Connect apenas quando a conta e o método o permitirem. Tratar expiração, falha e reembolso.
6. Ambas as rotas de pagamento convergem na mesma intenção; impedir dupla cobrança com índice único e bloqueio atómico. Não aceitar valor/desconto/comissão do browser como fonte de verdade.

## Regras financeiras
Para bruto 10000 centavos BRL e desconto 5%, desconto 500, líquido 9500. Usar Decimal/inteiros de centavos; arredondamento definido no servidor. Não usar valores em euros no checkout brasileiro. Validar regras de split e compatibilidade de Pix com Connect antes de habilitar repasses.

## Atenção: comportamento existente
- backend/routes_data.py POST /redemptions cria redenção/comissão logo após leitura. A nova opção P5 deve evitar esse endpoint para pagamentos online e não transformar scan em pagamento.
- backend/routes_payments.py POST /public/pay atualmente fixa currency='eur', payment_method_types=['card','mb_way'] e contém split em EUR. Não reutilizar sem parametrização por país e validação Stripe.
- frontend/src/pages/PublicCoupon.jsx mostra euros e MB WAY. Adaptar apresentação BRL/Pix sem quebrar Portugal.
- QR de campanha partilhável não identifica, por si só, o telemóvel do seguidor: é necessário token de claim/sessão e autorização da cobrança.

## Critérios de aceitação (a verificar antes de deploy)
- Pagamento direto e após scanner chegam ao mesmo fluxo financeiro.
- R$100 com 5% mostra R$95; a comissão só nasce após confirmação Stripe.
- Atualização da página do seguidor sem refrescar manualmente.
- Repetição de scanner, webhook ou clique não cria cobrança/redenção duplicada.
- Cartão e Pix conforme capacidades da conta; Apple Pay condicional.
- Checkout português permanece inalterado.

Estado: especificação adicionada à branch de desenvolvimento; implementação e deploy ainda pendentes.