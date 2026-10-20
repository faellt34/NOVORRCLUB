# P5 Portugal — cobrança validada pelo parceiro

**Regra aprovada:** o seguidor apresenta o QR; o parceiro autenticado confirma o valor bruto; o backend calcula desconto e bloqueia o valor líquido; a página do seguidor apresenta a cobrança vinculada à sessão; o seguidor paga por MB WAY/cartão/Apple Pay quando disponível; somente a confirmação Stripe marca pagamento e gera comissão.

Exemplo: €100, desconto 10%, cobrança €90. O valor é imutável pelo seguidor tanto na interface como no servidor.

## Mudanças necessárias
- Vincular claim do seguidor a token de sessão privado; QR público de campanha isoladamente não identifica um telemóvel.
- POST /partner/p5/charges cria cobrança pendente idempotente; não chama /redemptions.
- GET /public/p5/charges/current retorna apenas cobrança da sessão autorizada; página faz polling/SSE.
- POST /public/p5/charges/{id}/checkout cria sessão Stripe a partir do valor guardado no servidor.
- Webhook Stripe assinado e idempotente converte cobrança em redenção financeira somente quando o pagamento for confirmado; tratar pagamentos assíncronos, cancelamentos e reembolsos.
- Desativar caminho de pagamento direto não validado ou exigir aprovação do parceiro antes de capturar valor. Preservar apresentação do cupão e email opcional.
- Verificar regras Connect antes de transferir; nunca inferir pagamento a partir da leitura do QR.

**Estado:** especificação gravada na branch Portugal. Não é funcionalidade já implementada, testada ou publicada.
