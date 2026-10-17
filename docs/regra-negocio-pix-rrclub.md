# RRClub Brasil — regra de negócio de vendas e divisão Pix

## Filosofia confirmada pelo responsável
- O influenciador divulga a campanha, o seguidor usa link/cupom e compra do parceiro.
- **Sem venda confirmada não há comissão nem repasse a influenciador ou RRClub.** Cliques ou cupons capturados não geram pagamentos.
- Desconto, remuneração da RRClub e remuneração do influenciador são **negociáveis por campanha** com o parceiro e o influenciador. Preservar os campos e opções de negociação que já existem no site; não impor valores nem percentuais fixos.
- Exemplo ilustrativo em BRL: compra R$100, desconto R$5, cliente paga R$95; RRClub R$10; influenciador R$5; parceiro R$80. O exemplo não define percentuais globais, nem decide quem suporta as taxas Stripe.

## Verificação realizada no código atual
- `backend/routes_data.py`: regista campanha, cupom, parceiro, influenciador e `commission` e gera extrato de influenciador em `/statements`.
- `backend/routes_payments.py`: `/public/pay` atualmente cobra em EUR (`card`, `mb_way`) e implementa um destino Connect para parceiro; `fulfil` guarda comissão e atribui influenciador, mas **não comprova repasse automático à conta Stripe do influenciador**.
- O cálculo de comissão atual não é uma especificação completa para dividir em três beneficiários: é necessário alinhar com as regras de campanhas existentes e as taxas Stripe.

## Requisitos de implementação (pendentes)
1. Ler as condições negociadas e persistidas na campanha, sem alterar a interface de negociação existente.
2. Aguardar confirmação real de pagamento Stripe (`payment_status=paid`) e conciliar webhooks de forma idempotente.
3. Calcular desconto, valor efetivamente pago, taxas e valores atribuídos à RRClub, ao parceiro e ao influenciador; bloquear splits com total incompatível.
4. Verificar contas Connect e permissão para receber de cada beneficiário; nunca repassar para uma conta diferente.
5. Confirmar suporte Stripe Pix BRL + Connect para a arquitetura e países envolvidos antes de aplicar cobrança/repasse real.
6. Guardar os IDs de cada transferência e os estados (pendente, transferido, falhou, estornado), garantindo reconciliação.
7. Testar exemplos com comissão variável, sem venda, desconto, webhook duplicado, falha de transferência, estorno, sem influenciador e arredondamentos.
8. Preservar integralmente o checkout EUR existente e só ativar o novo fluxo Pix em produção após testes.

**Estado**: documento de especificação; código financeiro, deploy, testes e transferências de dinheiro real ainda não executados nesta branch.
