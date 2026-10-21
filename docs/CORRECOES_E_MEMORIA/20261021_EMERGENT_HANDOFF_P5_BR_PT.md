# EMERGENT · RRClub P5 · execução objetiva, Brasil separado de Portugal
Data: 21/10/2026. Estado do código GitHub conhecido: `031498cff26cdaf61ad27982c6e80231783addec` na branch `integracao-google-rrclub-20261019`. NÃO assumir que o workspace ou o deploy já possuem esse SHA.

## Regra principal
A RRClub está em produção; NÃO reconstruir P5 nem recriar contas Stripe. Preservar alterações locais (incluindo ficheiros M/U), outros pagamentos, campanhas, dados, ambiente e webhooks. Trabalhar apenas nas falhas comprovadas; aplicar **uma** correção por causa e fazer **um** deploy após validação. Separar moeda, chave e fluxo PT/BR. Não gastar tempo em onboarding/KYC de beneficiários pendentes; eles não devem bloquear P5 de outras campanhas. Contudo, nunca transferir a esses beneficiários sem titularidade e capacidades Stripe comprovadas.

## 0 · BLOQUEADOR AGORA · routes_auth.py local
O print 23:15 mostra texto `{"message":"Robson Club API","status":"ok"}` colado **dentro** de `backend/routes_auth.py` antes do import `from datetime...`, e o editor indica um erro. O original no GitHub começa por `import re\nfrom datetime import datetime, timezone, timedelta\nfrom typing import Optional, Literal`. Isto pode impedir a importação Python e causar 5xx no próximo deploy. Corrigir primeiro.

- Guard seguro disponível: `python3 scripts/rrclub_auth_prefix_guard.py --check` e, **somente se reportar padrão JSON previsto**, `python3 scripts/rrclub_auth_prefix_guard.py --repair`. Faz backup, só remove texto indevido no cabeçalho e valida toda a sintaxe. Se não reconhecer o padrão, parar e fazer diff manual com a versão GitHub; NÃO usar `git reset --hard`, `git checkout .` ou sobrescrever o ficheiro inteiro sem preservar outras edições.
- Executar `python3 -m compileall -q backend`; se falhar, reportar caminho e linha precisos. Recuperar saúde do backend ANTES de discutir Stripe.
- A consulta pública `https://rrclub.online/api/` devolveu JSON OK numa verificação, mas isso não demonstra que o erro Cloudflare 520 tenha desaparecido. Ver logs de arranque/worker, proxy e requests 5xx. Nunca confundir falha Cloudflare com KYC.

## 1 · P5 comum, fluxo acordado (já codificado)
Seguidor recebe cupão e QR **pessoal**; apresenta-o na loja; parceiro lê QR na PRIMEIRA leitura, confirma conta original; seguidor vê 5% desconto e total líquido no telemóvel e paga; converter para `paid` somente após confirmação do servidor/webhook Stripe. Não contar scan como pagamento. Prevenir dupla cobrança via idempotência e confirmar `p5_ref`. O scanner corrigido está em PR #15, outras melhorias PRs #14–#19: NÃO reimplementar.
Regras do original: desconto 5%; parceiro 80%; influenciador 5%; RRClub 10% antes de taxas Stripe (a RRClub suporta taxas). Para uma conta original €1, seguidor paga €0,95; parceiro €0,80; influenciador €0,05; RRClub €0,10 antes de taxas. Em R$1, respetivos valores em centavos BRL se houver condição financeira verdadeira.

## 2 · BRASIL = BRL/PIX (sem tocar em Portugal)
- Usar exclusivamente `PIX_STRIPE_SECRET_KEY`, `PIX_STRIPE_WEBHOOK_SECRET`, conta plataforma Stripe **RRCLUBRASIL**, `PIX_STRIPE_PLATFORM_COUNTRY=BR`; conferir `PIX_ENABLED`, `P5_ENABLED`, `P5_BRL_ENABLED`, modo LIVE e configuração de pagamento Pix BR. Não substituir pela Stripe PT.
- Conta Connect consultada para Paulo/Maraca: `acct_1URwjTEKs764BXlZ`. Verificada na Stripe BR LIVE: país BR, `charges_enabled` e `payouts_enabled` verdadeiros, `transfers` ativo, payout diário, sem requirements pendentes. E-mail compatível com o utilizador, mas **metadata vazio** (sem `partner_id`); isto **não comprova titularidade**. Não criar outra conta.
- Verificar no Mongo do Emergent a cadeia `users.id -> users.partner_id -> partners.id -> partners.user_id -> partners.pix_stripe_account_id`, estatuto e moeda do Maraca/Paulo, e a associação do influenciador. O diagnostic `scripts/rrclub_diagnose_partner_pix.py --name "Paulo Henrique" --account acct_1URwjTEKs764BXlZ` é READ-ONLY; comparar estado sem publicar email, documento, chave ou dados KYC.
- A correção PR #19 faz `GET /partner/pix/connect/status` mostrar `requires_admin_link` em vez de tratar a associação pendente como erro indisponível; não criar novas contas e não marcar pagamentos/transferências sem confirmação.
- Pendentes de atualização pelo próprio utilizador: marcar `aguarda titular` e deixar fora do **split financeiro**; NÃO impedir registo, campanhas não financeiras ou funcionamento P5 para outros.

## 3 · PORTUGAL = EUR/MB WAY (sem tocar em Brasil)
- Usar exclusivamente `STRIPE_SECRET_KEY` PT; `P5_EUR_ENABLED`, `P5_ENABLED`; regras financeiras atuais em `backend/pt_split.py` e `backend/p5_checkout.py`. Stripe RRCLUB Portugal LIVE tem charges/payouts/MB WAY ativos e webhook `https://rrclub.online/api/stripe/webhook` ativo. Verificar que a configuração de pagamento selecionada oferece **MB WAY**, pois outra configuração da mesma conta tem MB WAY desligado.
- Duas contas Connect **tecnicamente** aptas PT: `acct_1UIajlE123roTruk` (etiqueta PT-01) e `acct_1UIacdCy6KhbVjNX` (PT-02). Ambas sem requisitos pendentes, `transfers` e payouts ativos, MAS **ambas metadata sem partner_id/influencer_id**. NÃO determinar titular a partir de `rrclub.online`, email ou etiqueta. Conferir no Mongo por ID e confirmar titular antes de definir destino. A PR #18 criou inventário administrativo `GET /admin/finance/pt-split/accounts`.
- Em PT, interação QR/conta aprovada deve funcionar independentemente de Connect pronto. Para cobrar em LIVE e fazer split, **apenas** campanhas cuja associação `partner_id` e `influencer_id` corresponda à Stripe Connect validada em `pt_split.recipients_ready`, com `PT_SPLIT_ENABLED`, `PT_SPLIT_LIVE_ENABLED`, `PT_SPLIT_AUTO_TRANSFER` corretas. Não ligar todas as flags cegamente.
- Se nenhum par for inequivocamente validado: não declarar transferências LIVE, não ativar cobrança daquele cupão; manter P5 QR operacional e exibir motivo claro. Os utilizadores pendentes são responsabilidade deles e não travam campanhas aptas. O estado de depósito **bancário** é diferente da transferência Stripe Connect.
- Examinar em `_pt_stripe_checkout` a seleção `["card","mb_way"]`; o fallback atual para apenas `card` não deve ser apresentado como “MB WAY disponível” sem evidência da Stripe.

## 4 · Execução mínima e critérios de conclusão
1. `git status --short` + confirmar branch/commit sem sobrescrever alterações locais. Corrigir apenas corrupção de `routes_auth.py` e outras falhas reproduzidas. Preservar backup.
2. `python3 -m compileall -q backend` e `cd /app/frontend && npm run build`. Se `pytest` não estiver instalado nesse Python, usar ambiente do projeto ou apenas testes disponíveis; NÃO instalar dependências às cegas em produção.
3. Consultas *read-only*: `GET /api/`, `GET /api/public/p5/config`, `GET /api/public/pix/availability`. Verificar moedas individualmente e confirmar que o ambiente do deploy é o mesmo do teste; não expor segredos.
4. Validar em ambiente autorizado fluxos QR BR e QR PT por separado; quando estiverem financeiros aptos, testar pagamento pelo seguidor e verificar webhooks, estado `paid` único, dois destinos exatos e transferências idempotentes. Não inventar transações e não usar contas pendentes para simular split.
5. Só depois, deploy controlado da branch/alterações preservadas; verificar arranque, API, painel Paulo e campanhas PT. Não mexer em RESET ALL/LIMPAR, dashboard RRClub 2.0, Pix vs MB WAY misturados ou ideias futuras.

## Relatório final obrigatório, em 6 linhas
1. Autenticação/Cloudflare: erro identificado e corrigido? Evidência.
2. P5 QR Brasil: funciona? Valores/cupão/seguidor? Código vs publicado.
3. P5 Pix: conta BR e vínculo interno? Exatamente o que impede ou permite checkout.
4. P5 QR Portugal: funciona? MB WAY mostrado/realmente elegível?
5. P5 Split EUR: campanhas realmente aptas, destinos provados, flags e webhook.
6. Arquivos alterados, testes, commit/deploy e pendências **dos utilizadores** ignoradas na priorização (sem ignorar segurança).

Proibição: não divulgar chaves Stripe, tokens, IBANs, dados fiscais ou KYC. Não afirmar que Pix/MB WAY/split real funcionam apenas porque compilação passou ou foi feito deploy.
