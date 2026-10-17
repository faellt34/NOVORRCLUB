# RRClub Brasil — regra de negócio de vendas e divisão Pix

## Filosofia confirmada pelo responsável
- O influenciador divulga a campanha, o seguidor usa link/cupom e compra do parceiro.
- **Sem venda confirmada não há comissão nem repasse a influenciador ou RRClub.** Cliques ou cupons capturados não geram pagamentos.
- Desconto, remuneração da RRClub e remuneração do influenciador são **negociáveis por campanha** com o parceiro e o influenciador. Preservar os campos e opções de negociação que já existem no site; não impor valores nem percentuais fixos.
- Exemplo ilustrativo em BRL: compra R$100, desconto R$5, cliente paga R$95; RRClub R$10; influenciador R$5; parceiro R$80. O exemplo não define percentuais globais. **Decisão do responsável: a RRClub assume integralmente as taxas da Stripe; o parceiro recebe R$80 e o influenciador R$5 neste exemplo, sem dedução da taxa Stripe das parcelas deles. A remuneração líquida da RRClub é R$10 menos a taxa Stripe.**


## Atendimento presencial — QR Code ou cupom mostrado ao parceiro
1. O seguidor vê a divulgação do influenciador, obtém o cupom e dirige-se ao estabelecimento do parceiro.
2. No local, o seguidor pode **apresentar o QR Code do cupom** para leitura ou **mostrar o código do cupom** ao parceiro para validação manual.
3. Ambas as alternativas devem resolver a mesma campanha e atribuição do influenciador; o parceiro valida elegibilidade e valor da compra, aplica o desconto negociado e apresenta o valor final.
4. **QR Code do cupom não é QR Code Pix**: o primeiro identifica/valida benefício; o segundo é emitido pelo provedor de pagamento para o cliente pagar.
5. Se a compra for liquidada por Pix, aguardar a confirmação autenticada do Stripe antes de concluir a venda e autorizar comissões/repasses. A apresentação ou leitura do cupom isoladamente não é prova de pagamento.
6. Preservar o fluxo de resgate presencial atual, inclusive quando a venda for paga diretamente no caixa por outro meio; não presumir que tal pagamento passou pelo Stripe nem disparar repasse automático sem conciliação e regra específica.
7. Garantir que apresentação por QR e digitação manual não gerem duas vendas, duas comissões ou dois repasses para o mesmo atendimento.

## Verificação realizada no código atual
- `backend/routes_data.py`: regista campanha, cupom, parceiro, influenciador e `commission` e gera extrato de influenciador em `/statements`.
- `backend/routes_payments.py`: `/public/pay` atualmente cobra em EUR (`card`, `mb_way`) e implementa um destino Connect para parceiro; `fulfil` guarda comissão e atribui influenciador, mas **não comprova repasse automático à conta Stripe do influenciador**.
- O cálculo de comissão atual não é uma especificação completa para dividir em três beneficiários: é necessário alinhar com as regras de campanhas existentes e as taxas Stripe.

## Requisitos de implementação (pendentes)
1. Ler as condições negociadas e persistidas na campanha, sem alterar a interface de negociação existente.
2. Aguardar confirmação real de pagamento Stripe (`payment_status=paid`) e conciliar webhooks de forma idempotente.
3. Calcular desconto, valor efetivamente pago, taxas e valores atribuídos à RRClub, ao parceiro e ao influenciador; bloquear splits com total incompatível. As taxas da Stripe são absorvidas exclusivamente pela parcela RRClub; impedir operação se não houver saldo suficiente para cumprir os compromissos negociados.
4. Verificar contas Connect e permissão para receber de cada beneficiário; nunca repassar para uma conta diferente.
5. Confirmar suporte Stripe Pix BRL + Connect para a arquitetura e países envolvidos antes de aplicar cobrança/repasse real.
6. Guardar os IDs de cada transferência e os estados (pendente, transferido, falhou, estornado), garantindo reconciliação.
7. Testar exemplos com comissão variável, sem venda, desconto, webhook duplicado, falha de transferência, estorno, sem influenciador e arredondamentos.
8. Preservar integralmente o checkout EUR existente e só ativar o novo fluxo Pix em produção após testes.

**Estado**: documento de especificação; código financeiro, deploy, testes e transferências de dinheiro real ainda não executados nesta branch.
