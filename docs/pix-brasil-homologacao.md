# RRClub Brasil — homologação Stripe Pix (SEM produção)

Estado em 17/10/2026: **55 testes automatizados concluídos com sucesso**, mas **nenhum Pix real nem sandbox ponta a ponta foi executado**. Não fazer merge/deploy para produção enquanto faltar a validação externa.

## Arquitetura revista
- A RRClub Brasil cobra em BRL, por Pix, em sua própria conta Stripe BR.
- Usar a modalidade **separate charges and transfers** após confirmação autenticada da cobrança para repassar duas parcelas, quando o esquema de contas/capacidades Connect for comprovado. Uma cobrança com `transfer_data.destination` única não divide automaticamente entre parceiro e influenciador.
- Beneficiários: parceiro e influenciador em contas Connect **individuais**, com país e titularidade comprovados. A RRClub retém a parcela de plataforma e **suporta integralmente** a tarifa Stripe com sua própria parte.
- Exemplo negociado, não padrão: original R$100; desconto R$5; cobrança R$95; parceiro R$80; influenciador R$5; RRClub R$10 antes da tarifa Stripe.
- Nunca usar um clique ou QR do cupom como prova de cobrança Pix. A confirmação de pagamento deve ser `payment_status=paid` após assinatura verificada, e o evento não pode liquidar duas vezes.
- `transfer_group` da cobrança sandbox é uma **etiqueta para conciliação**, não uma transferência; **nenhum repasse é executado por este código**.
- Manter PT isolado: EUR, cartão/MB WAY e credenciais portuguesas, sem fallback para conta BR.

## Configurar SOMENTE em ambiente privado de homologação (não na produção)
- Não copiar chaves para GitHub nem para mensagens do chat.
- `STRIPE_SECRET_KEY_BR=sk_test_...` da conta **RRCLUBRASIL**.
- `STRIPE_WEBHOOK_SECRET_BR=whsec_...` do endpoint sandbox BR.
- `PIX_ENABLED=true` e `PIX_SANDBOX_ENABLED=true` exclusivamente nesse ambiente de teste. O checkout só aceita `sk_test_`; uma chave live bloqueia a operação.
- `FRONTEND_URL=https://<URL-DA-HOMOLOGACAO>` (a aplicação constrói URLs de retorno a partir desse valor). Sem credenciais PT reutilizadas.
- Configurar webhook Stripe **modo teste** com endpoint `https://<BACKEND-HOMOLOGACAO>/api/pix/br/test/webhook` e eventos `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`.
- Confirmar na Stripe que Pix está disponível e permitido para esse tipo de conta/Checkout em sandbox antes de continuar.

## Pré-condições no banco de homologação
1. Parceiro de teste com `pais=BR`, campanha de teste `pais=BR` e `status=Ativa`.
2. Cupom único, desconto e comissão do influenciador explícitos, `comissao_rrclub` explícita. Nenhum percentual é inferido.
3. Não associar automaticamente contas Connect sem onboarding e confirmação independente de titularidade.
4. Executar `POST /api/pix/br/test/checkout` no backend de homologação com `{"code":"CUPOM_DE_TESTE","amount":100}`. Resposta esperada: `currency=brl`, `amount_cents=9500` para uma campanha com desconto 5%; URL Checkout de teste.
5. Confirmar QR e conclusão Pix no ambiente simulado da Stripe; verificar evento assinado, mudança idempotente de `payment_status=pending` para `paid` somente quando a Stripe informar `paid`.
6. Verificar `GET /api/pix/br/test/status/<session_id>`, incluindo `transfers_executed=false`.
7. Reenviar webhook pago, falhou e expirado: nenhuma segunda venda, nenhum repasse e nenhuma reclassificação de pago para falho.
8. Testar paralelismo de várias sessões; `session_id` provisório é exclusivo por tentativa.
9. Testar BR com chave live, país PT/conflitante, webhook sem assinatura, valor incorreto, comissão ausente, desconto inviável: todos devem bloquear.
10. Registar prova da sessão `cs_test_...`, IDs de eventos (sem segredos), status e resultados antes de autorizar implementação de transferências reais.

## Quando liberar fase de repasses (ainda não implementada)
- Cada conta Connect de parceiro e influenciador em BR precisa de validação independente, capacidade `transfers=active` e `payouts_enabled`.
- Persistir `payment_intent`, `charge`, `transfer_group`, `source_transaction`, IDs de transferências, estados de falha, estorno e reconciliação. Usar chaves de idempotência persistentes por venda/beneficiário.
- Verificar saldo disponível, tarifa Stripe a cargo da RRClub e capacidade de cobrir os valores prometidos. Usar a arquitetura validada pelo planejamento Stripe, não atribuir `split_executado` como prova de transferência.
- Testar ambos os destinos em sandbox e simular falha parcial, webhook duplicado e reembolso. **Só depois** propor deploy de BR; Portugal permanece intacto.

## CI atual
`.github/workflows/pix-sandbox-safety.yml`: compilação Python, testes de regras, isolamento de moeda, webhook/session matching, validação de cadastro e sintaxe JSX. **CI verde não valida Pix bancário nem uma transferência real.**
