# RRClub Portugal — auditoria real Stripe e transição para Emergent

**Data:** 2026-10-21 · **Situação:** código testado/integrado na branch GitHub `integracao-google-rrclub-20261019`; **NÃO foi republicado no Emergent**.

## 1. Evidência financeira confirmada na conta RRCLUB Portugal (live, leitura apenas)

- Campanha/cupão: `RR-BBB7`; campanha `c-ec83746e4e`.
- Parceiro associado: Robson Gomes · ID interno `p-1ada8c7688` · Connect `acct_1UNAuwCxuyve5XrI`.
- Conta Stripe Connect do parceiro: metadata.partner_id corresponde ao parceiro. `charges_enabled=false`, `payouts_enabled=false`, `transfers=inactive`, `requirements.past_due`. A correção desses requisitos compete ao titular da conta.
- Checkout live: `cs_live_a1A1UKtTz0NPsTI635tuY8uryR6dsHU1GaLI0bxPb9ZAOqSI3v0RGmakWM`; PaymentIntent `pi_3USkyNCZnwrqCuCt0BiJG67n`, pago.
- Charge `py_3USkyNCZnwrqCuCt07GW88AV`: método **MB WAY**; pago **€0,90**; sem destination Connect; não reembolsado nem contestado quando consultado.
- BalanceTransaction `txn_3USkyNCZnwrqCuCt0yjSrhxG`: bruto **€0,90**, taxa Stripe **€0,26**, líquido deste movimento **€0,64**, estado do saldo `pending` no momento da consulta.
- Lista de transferências da plataforma Stripe Portugal: **0** na consulta. Nenhuma transferência ao parceiro nem ao influenciador foi comprovada.
- A RRClub comunicou comissão de **€0,05** para esta redenção. Este valor é inferior à taxa Stripe de €0,26. A diferença é **€0,21**, mas **não deve ser tratada automaticamente como prejuízo contabilístico final** sem validar acordos de comissionamento e possíveis custos adicionais.
- Influenciador da campanha: referido operacionalmente como Lucas, mas **o Checkout antigo não guardou snapshot de influencer_id**. Não alterar o beneficiário nem pagar por correspondência de nomes; conciliar primeiro os IDs e a venda. O Portugal Checkout não contém transferência independente e automática ao influenciador.

## 2. GitHub: alterações executadas

- PR #7: auditoria read-only EUR; estado Connect por parceiro; proteção contra comissões sem beneficiário; snapshot de taxa e influencer para novos checkouts; eventos de redenção deixam de declarar split financeiro; manutenção da moeda e Pix BRL; verificação Stripe independente do ledger local. Merge no ramo de integração: `39373743a65fced0aed3b05dfc15a6f83ac9fa9e`.
- PR #8: auditoria da taxa de processamento Stripe e valor líquido com prova por BalanceTransaction; aviso quando taxa excede comissão; estado `pending` separado de dinheiro disponível; testes de UI e Python. Merge: `cdbcbc28a73df9f8312becb4300b618184b8c023`.
- CI das duas PRs: testes financeiros, compilação do React e teste do painel de auditoria **aprovados**.
- PR #6 foi integrada à `main` do GitHub, mas **não implica que o Emergent tenha sincronizado a main**. A publicação de interesse está no ramo de integração com Pix.

## 3. Passo obrigatório antes de publicar no Emergent

No editor Emergent, os prints mostraram o workspace local no commit `da9a1d4`, branch `integracao-google-rrclub-20261019`, **sem origin configurado**. Já se fez um `git fetch` manual da main do GitHub, mas isso não é deploy. Já foram adicionados localmente os ficheiros `backend/routes_finance.py`, `backend/finance_evidence.py`, alterações no `backend/server.py` e `FinanceReconciliationPanel.jsx` (versões anteriores à presente integração).

**Não fazer `git pull`, `git reset --hard`, `git restore` global, `checkout -f` nem substituição do projeto inteiro.** Há divergência entre a base GitHub e o workspace Emergent; até ficheiros já adicionados localmente podem ter nomes iguais e conteúdo diferente.

O agente que possui acesso real ao workspace deve:
1. Guardar backup sem segredos dos ficheiros de código alterados e registar o HEAD/estado do Git local.
2. Trazer o commit remoto **`cdbcbc28a73df9f8312becb4300b618184b8c023`** apenas para comparação, não para substituição automática.
3. Fazer integração seletiva de auditoria, `routes_ops.py`, `routes_payments.py`, `routes_data.py`, `server.py`, ecrãs de comissões e teste, preservando `routes_pix.py`, todas as rotas Pix BRL, token/sessão, Google e funcionalidades adicionais do Emergent. Resolver conflitos de ficheiros já existentes antes de aplicar.
4. Confirmar no código do Emergent a rota admin `/api/admin/finance/reconciliation` e a importação do componente atualizado (sem duplicar a antiga auditoria inserida manualmente).
5. Executar compilação backend, testes financeiros e build/testes React na máquina do Emergent, e verificar proteção de endpoints admin.
6. Num ambiente de testes, confirmar os estados *pago na Stripe, não recebido localmente, não transferido*, parceiro Connect bloqueado, moeda EUR, e Pix Brasil sem alterações.
7. Validar política económica antes de autorizar novos splits automáticos: as taxas de processamento podem superar a comissão da campanha. Não modificar preços, taxas ou fazer transferências reais sem aprovação da política pela empresa.
8. Só então avaliar republicação do serviço existente, com verificação de logs. **Não gerar cobrança real de teste** para confirmar aquilo que já foi provado na Stripe.

## 4. Precauções de dados

- Não criar payout fictício, repasse Stripe nem "Marcar como pago" para `influencer_id=null`.
- As duas redenções antigas com total €0,10, influenciador exibido como "—", **permanecem por conciliar** e não podem ser automaticamente atribuídas ao Lucas.
- Não exportar IBAN completo, dados fiscais, segredos Stripe ou dados pessoais para GitHub.
- Não confundir pagamento recebido, transferência Connect, payout bancário, reembolso, disputa e comissão contabilizada.
- **Sem publicação ou movimentações financeiras durante estas alterações de código.**
