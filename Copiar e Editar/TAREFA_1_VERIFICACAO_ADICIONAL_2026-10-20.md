# Tarefa 1 — verificação adicional do código (20/10/2026)

Escopo: leitura estática da branch BRANCH-copia-editar-a-vontade. Nenhuma alteração de produção. Não é parecer jurídico nem teste de execução.

## Evidências novas
- backend/p5_quote.py: função quote calcula descontos a partir de percentagem recebida, devolve pagamento 'not_paid' e métodos candidatos por país. O próprio comentário exige que a percentagem venha de campanha aprovada no servidor; a função isolada não verifica a origem nem executa checkout/QR.
- backend/p5_cash_rules.py: quote_cash regista pagamento 'pending_cash', comissão 'owed_by_partner' e Stripe 'not_applicable'; confirm_cash exige parceiro autorizado, correspondente e confirmação de recebimento. Não prova integração com base de dados nem idempotência.
- backend/payments/pt_split.py: split PT experimental apenas quando PT_SPLIT_V2_ENABLED=true e chave sk_test_; verifica contas Connect e possui chaves de idempotência para transferências. ATENÇÃO: quote exige desconto fixo de 5%, incompatível com o exemplo P5 de 10%; não reutilizar sem decisão explícita sobre a campanha.
- backend/routes_pix.py: o relatório anterior identificou 5% fixos no Pix BR, fluxo separado do P5 a 10%.
- Existem backend/routes_payments.py, backend/routes_diretor.py, backend/routes_data.py e testes/workflows no repositório; é incorreto concluir que não há módulos de pagamento apenas porque routes_checkout.py não existe.

## Lacunas ainda não comprovadas
- Encadeamento ponta a ponta QR -> sessão -> cupão de uso único -> checkout EUR com desconto aprovado.
- Ligação de dinheiro e Stripe a uma única transação/atribuição, reconciliação, reembolsos e proteção contra dupla comissão.
- Minicadastro de prémios e prova dos avisos, bases legais, retenção e direitos dos titulares.
- Testes funcionais e revisão jurídica de promoções/prémios, fiscalidade, RGPD e LGPD.

## Critério de saída
Não marcar tarefa 1 concluída com base em documentação ou leitura estática. Requer evidências dos fluxos e testes; conformidade jurídica definitiva depende de avaliação competente. Tarefa 2 permanece bloqueada.
