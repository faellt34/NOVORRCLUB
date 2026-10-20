# RRClub — auditoria do caminho financeiro (CLONE, 20/10/2026)

**Âmbito:** branch `BRANCH-copia-editar-a-vontade` de `faellt34/NOVORRCLUB`. Inspeção de código, Stripe documental e testes isolados. **Não** constitui certificação jurídica, fiscal, PCI, Stripe Connect ou de liquidação bancária. **Não** houve alteração da produção, criação de cobranças reais nem conta Connect real para Maria Eduarda.

## Rota Brasil / Pix — traçabilidade

1. `/api/partner/pix/checkout`: campanha BRL ativa, desconto P5 e comissão 5%, parceiro e influencer distintos, destinatários Connect verificados; só parceiros geram novas sessões Pix.
2. `/api/public/pix/checkout`: cliente retoma uma referência já criada pelo parceiro, não cria cobrança arbitrária.
3. Stripe Checkout BRL com configuração exclusiva Pix, chave brasileira segregada, `request_id` e `idempotency_key`.
4. `/api/stripe/pix/webhook`: assinatura Stripe verificada; `paid` + moeda/valor/metadados conferidos. Redenção idempotente.
5. `execute_split`: parceiro 80% bruto, influencer 5% bruto, plataforma 10% bruto (antes das taxas Stripe), após desconto 5%; destinatários Connect obrigatoriamente aptos. Não afirmar que a liquidação bancária ocorreu apenas por sucesso do transfer.
6. Reembolsos Pix, tentativas repetidas, disputa, retenção de comissões e reversões têm testes isolados. Ainda requerem confirmação em sandbox real e reconciliação de saldos.

## Rota Portugal / EUR / MB WAY — traçabilidade

1. `/api/public/pay`: campanha e parceiro em EUR; Checkout com 5% de desconto quando a campanha assim estiver configurada.
2. Origem HTTPS verificada por allowlist; Checkout usa os métodos configurados na conta PT (MB WAY não é garantido só por existir a capacidade).
3. Webhook assinado `/api/stripe/webhook`: sessão `paid` conferida contra ID, EUR, cêntimos, metadados da campanha/parceiro e modo live/test. A mesma verificação é aplicada à consulta de status.
4. Os registos de redenção/comissão são **registos contabilísticos da aplicação**, não prova de transferência ao influencer.
5. O componente MB WAY sandbox está segregado; qualquer pagamento simulado devolve `paid_test`, não cria compras, transferências ou recibos verdadeiros.

## Perfis Maria Eduarda

Existem apenas **fixtures fictícias distintas** para BR e PT na pasta `backend/tests/fixtures`. Nenhum e-mail real, conta Stripe verdadeira ou utilizador de produção foi criado. Os testes validam rejeição de destinatários não verificados e não contam indicações de terceiros como vendas pagas. Isto **não** implica que o website esteja a filtrar automaticamente todos os referrals de perfis não aptos.

## Correções aplicadas exclusivamente ao clone

- Normalização de recursos StripeObject devolvidos pelo SDK (Pix, Portugal e webhooks).
- Verificação de HTTPS/allowlist no Checkout genérico de produtos/subscrições.
- Reconciliação de valores, moeda, identidade da campanha/parceiro e modo Stripe antes de reconhecer pagamento EUR.
- Tratamento seguro de campos opcionais ausentes da Session.
- `/api/admin/reset-all` e `/api/admin/test-run/clear-all` bloqueados (403), para impedir apagamentos globais em ambiente de testes.
- Regressões HTTP reais em memória, com assinaturas de webhook verificadas pela biblioteca Stripe; **sem dinheiro real**.

## Bloqueios para conformidade ponta a ponta (não aprovar deploy)

| Prioridade | Ponto | Risco e trabalho necessário |
|---|---|---|
| CRÍTICO | Split Portugal | `public_pay` usa `transfer_data` para 1 parceiro e `application_fee_amount` para plataforma; **não transfere automaticamente comissão ao influencer**. Sem Connect apto, cai em pagamento à plataforma, sem demonstração de repasse posterior. Desenhar e testar split PT real sem misturar países e sem prometer 80/5/10 antes de implementar. |
| CRÍTICO | Recuperação de falhas após `paid` | No EUR, `fulfil` marca a transação como paga antes de concluir a escrita da redenção e efeitos posteriores; erro temporário pode deixar venda paga sem redenção e sem retry efetivo. Exigir reconciliação/ledger idempotente, com testes de falhas intermédias. |
| ALTO | Reembolsos e disputas EUR | Falta reconciliação da redenção/comissão após charge refunded/disputed e eventual reversão de Connect no fluxo EUR; não afirmar que há repasse líquido correto. |
| ALTO | Elegibilidade e indicações | A rota pública de cupões regista cliques sem confirmar a aptidão Connect do influencer. Separar métricas de interesse de receita real e filtrar benefícios/transferências por beneficiário apto; perfis incompletos são responsabilidade dos titulares, não bloqueiam testes de outros perfis. |
| ALTO | Pix onboarding 502 | O helper `provider()` converte erros Stripe em HTTP 502 genérico, o que pode esconder `account_links` ou requisitos Connect. Obter classificação de erro/Request ID em logs sanitizados; testar onboarding no sandbox, **sem criar contas Stripe live fictícias**. |
| ALTO | Isolamento operacional | Não existe ainda verificação com credenciais `sk_test_` reais para as duas contas, nem DB exclusiva comprovada na Emergent. Não reutilizar a prévia/editor operacional para testes financeiros. |
| ALTO | Contas e plataforma | Algumas contas PT ainda possuem requisitos `past_due`; completar via onboarding hospedado pela Stripe. Aceitação do Connect Platform Profile permanece sujeita a verificação do administrador. |
| MÉDIO | Dados de demonstração | `seed.py` possui utilizadores de demonstração com credenciais padrão se o piloto estiver ativo; a configuração deve impedir estas contas em ambientes de produção. |
| MÉDIO | Impostos/recibos | Verificar endereço fiscal e imposto de vendas em Stripe Tax; recibo da app não substitui obrigação documental/faturação aplicável. |
| MÉDIO | Tarifas e margem | Taxas Stripe reais variam; os 10% do fluxo Pix são receita bruta estimada da plataforma **antes** das taxas, não lucro garantido. |

## Critérios de saída

1. Ambiente de teste independente com chaves `sk_test_` PT/BR, DB própria e origins apenas do clone.
2. Checkout Pix e MB WAY test criados e pagos em simulação Stripe; webhooks recebidos/verificados com rastreio de IDs.
3. Repartição e reversões reconciliadas na mesma transação sem pagadores/recebedores errados; ausência de duplo pagamento após retry.
4. Testes de falha na DB após confirmação Stripe, estorno parcial/total, disputa, email falhado e confirmação tardia.
5. Restrições de beneficiários incompletos e filtragem de campanhas/cupões validadas.
6. Confirmação da plataforma Connect, responsabilidades legais, privacidade (RGPD/LGPD), impostos, termos com parceiros e processamento de dados por responsáveis adequados.

**Política:** nenhuma chave, identidade pessoal, documento, teste com dinheiro ou aprovação de requisitos Stripe é guardado neste relatório público. Qualquer lançamento em produção exige aprovação explícita.
