# Pix Brasil — regra financeira e pendências de validação

Estado: especificação, NÃO implementação ou teste de pagamento.

## Regra definida para ticket bruto em reais
- Seguidor: desconto de 5% sobre o ticket.
- Parceiro restaurante/hotel: 80% do ticket bruto.
- RRclub: 10% do ticket bruto, antes das tarifas de processamento.
- Influenciador: 5% do ticket bruto.
- Cliente paga 95% do ticket bruto.
- Taxas de processamento devem sair da parcela RRclub, se forem economicamente suportáveis.

Exemplo: ticket R$ 100; desconto R$ 5; cliente paga R$ 95; parceiro R$ 80; RRclub R$ 10 menos taxas; influenciador R$ 5.

## Constatações do código atual
- backend/routes_payments.py, endpoint /public/pay: cria Checkout em EUR, com cartão e MB WAY; não implementa Pix BRL.
- O código de comissões usa o campo comissao por campanha e registra a comissão para o influenciador nos extratos. A regra acima exige separar explicitamente as parcelas de plataforma e influenciador para evitar duplicação.
- O Stripe Connect existente cria contas Express em PT, não garante repasses a contas brasileiras.

## Bloqueios antes de ativar
1. Confirmar elegibilidade Pix, BRL, tarifa efetiva, IOF/câmbio e condições da conta Stripe da plataforma.
2. Verificar se o cliente pode pagar exatamente R$ 95 sem sobretaxas; caso haja IOF ou outro encargo, determinar absorção pela plataforma ou provedor brasileiro.
3. Validar capacidade legal/técnica de repasse a parceiro e influenciador no Brasil, sem assumir Connect transfronteiriço.
4. Testar geração de QR Pix/Copia e Cola, webhook de pagamento confirmado, idempotência, reembolsos, reconciliação e divisão.
5. Manter main e produção intactas até testes e autorização explícita de publicação.

Referências para validação: https://docs.stripe.com/payments/pix e https://docs.stripe.com/connect/separate-charges-and-transfers

Nenhuma transação real foi testada e nenhum método Pix foi ativado por este documento.
