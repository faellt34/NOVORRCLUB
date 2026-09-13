# Robson Club — PRD

## Problema original
Multi-Tenant SaaS que conecta influencers de experiências de luxo com parceiros (restaurantes, hotéis, rooftops, passeios) em Portugal e internacional. Influencers geram vendas via cupons/QR; parceiros validam e recebem atribuição de receita mensurável; comissão travada por redenção. PT-PT, EUR, comissão padrão 10% (configurável por campanha), track-only (payout offline).

## Arquitetura (atual — backend real)
- Frontend: React 19 + Tailwind + shadcn/ui + Recharts + qrcode.react + axios. `src/lib/api.js` (axios, token em localStorage `robson_token`), `src/context/AppContext.jsx` (auth + contadores unread).
- Backend FastAPI + MongoDB (motor): `server.py`, `core.py` (JWT/bcrypt/RBAC/audit/notify), `seed.py` (seed idempotente, datas relativas a hoje), `routes_auth.py`, `routes_data.py`, `routes_admin.py`, `routes_leads.py`, `routes_messages.py`.
- Auth: email+password, bcrypt, JWT 7d (Bearer + cookie), brute-force 5/15min. RBAC por papel: admin / influencer / partner. Sem role switcher.
- Idempotência: índice único `redemptions.idempotency_key` + guarda 10s partner+cupom+valor. Audit log append-only (sem endpoints de edição/remoção). Notificações automáticas server-side (redenção, lead, aprovação/rejeição, mensagem).
- Rotas frontend: `/login`, `/influencer`, `/influencer/extrato`, `/parceiro`, `/admin`, `/admin/gestao`, `/mensagens`, `/notificacoes`, `/ebooks`.
- Design: tema claro #F8F9FC + roxo #7C3AED, sidebar #0C0A14 (ver /app/design_guidelines.json).
- Credenciais: /app/memory/test_credentials.md

## Implementado
### 2026-06 · Fases 1-4 protótipo mock (iteration_1/2 — obsoletos)
### 2026-09 · Backend real + Login + Aprovações + Mensagens ✅ (iteration_3.json — 100% backend 25/25, 100% frontend)
- Página de login (split premium, botões de demo), rotas protegidas por papel, logout
- Dashboards Influencer/Partner/Admin calculados a partir de redenções reais (KPIs, tendências, gráfico diário, top parceiros, leaderboard)
- Validação de cupom com preview server-side, redenção idempotente, taxa travada, persistência após reload, CSV
- Extrato mensal gerado das redenções (payouts marcados em `payouts`)
- Admin CRUD (usuários c/ password, influencers, parceiros, campanhas c/ resolução de parceiro/influencer, e-books) + audit
- Indicações: formulário → admin aprova/rejeita com nota → aprovação cria parceiro automaticamente + conta de acesso (parceiro123) se contacto for email → notificação ao indicador
- Hub de mensagens: contactos permitidos por papel, conversas 1:1, unread, polling 8s; badges na sidebar
- Notificações: página + badge; e-books com país/idioma/preço (12 guias: PT, Espanha, Itália, França, Emirados)

### 2026-09 · Scanner real + Pagamentos + Recuperação de password + Stripe e-books ✅ (iteration_4.json — 100% backend 19/19, 100% frontend)
- Scanner QR com câmara real (html5-qrcode), extrai código de links `/c/CODE`, fallback amigável sem câmara
- Admin `/admin/pagamentos`: marca extrato mensal como pago / reverte → influencer vê "Pago em" no extrato + notificação
- Recuperação de password sem email: `/esqueci-password` → admin vê pedidos no painel e copia link `/redefinir-password?token=` (24h, uso único)
- Stripe (sandbox reclamável, país PT, tax mode "full"/managed): compra individual `ebook_{id}` (preço do admin) + subscrição `club_monthly` 9,90€/mês; `/payment/success` faz polling com fallback ao Stripe; entitlements/subscriptions no Mongo
- Upload de PDF pelo admin (Emergent Object Storage) e leitor in-app (blob → iframe) com gating server-side (gratuito/comprado/subscrito/admin)

### 2026-09 · Lançamento: Email, Cancelar subscrição, PDF extrato, i18n, Privacidade, Sugestões, Registo, Cupom público, Rebrand ✅ (iteration_5 13/13 + iteration_6 11/11, 100% frontend; deployment_agent: pass)
- Email via Resend (`mailer.py`) para reset de password e notificações importantes — ativa quando `RESEND_API_KEY` for preenchida; sem chave o fluxo funciona com link copiado pelo admin
- Cancelar subscrição Premium (cancel_at_period_end no Stripe) na área de E-books
- Extrato mensal em PDF (reportlab) `GET /api/statements/{mês}/pdf`
- i18n PT/EN/ES (`I18nContext`, switcher no login e sidebar; cobre navegação, login, e-books, sugestões — conteúdos de dados continuam PT)
- Página pública `/privacidade` (PT/EN/ES, RGPD) com link no login/sidebar/registo
- Sugestões de melhoria: botão na sidebar → `/api/feedback`; admin gere estados no painel
- Registo no site `/registar`: influencer ativo imediato; parceiro fica Pendente até admin ativar em Gestão › Parceiros (login bloqueado com mensagem; notificações automáticas)
- Cupom público `/c/:code` (QR aponta para o site) regista "clientes que receberam cupom" (dedup IP+UA/12h) → KPI real no dashboard do influencer + coluna "Receberam"
- Rebrand visível: "ןןClub" (título, sidebar, login, emails, PDF)

### 2026-09 · Produção: Definições admin, Zerar piloto, PWA, i18n de conteúdos ✅ (iteration_7 13/13, 100% frontend)
- `/admin/definicoes`: configurar chave Resend + remetente pela UI (guardado em `settings`, sem redeploy), testar email, zerar dados piloto (confirmação "ZERAR")
- **Piloto zerado em 2026-09-09**: só o admin dono existe; seed de demo desativada (`settings.pilot.demo_disabled`); botões de demo removidos do login
- PWA: manifest, ícones 192/512, service worker (só em produção), meta iOS, botão "Instalar app" na sidebar; atalho "Validar Cupom"
- i18n de conteúdos (categorias, países, cidades, estados, badge Premium) em EN/ES via `tc()`
- Deployment check: pass

### 2026-09 · Pagamento pelo cliente via QR + IBAN do parceiro ✅ (iteration_8 7/7, 100% frontend)
- `/c/CODIGO`: cliente indica o valor da conta → Stripe Checkout (cartão + MB WAY quando ativo na conta Stripe) cobra o valor já com desconto → redenção criada automaticamente (staff "Pagamento online (QR)", `paid_online`) com comissão travada + notificações
- Parceiro define IBAN de recebimento no dashboard (`POST /api/partner/iban`); admin edita IBAN em Gestão › Parceiros; KPI "recebido online"
- Nota: o dinheiro entra na conta Stripe do dono; a transferência ao parceiro (IBAN) é offline/track-only (Stripe Connect fica no backlog)
- Dados de exemplo em produção: Parceiro Exemplo, @exemplo, campanha CLUB-10 (o admin pode apagar em Gestão)

### 2026-09 · Stripe Connect (split automático) + Recibo do cliente ✅ (iteration_9 8/8, 100% frontend)
- Parceiro liga conta bancária via Stripe Connect Express (`POST /api/partner/connect/onboard`, `GET /api/partner/connect/status`); quando `charges_enabled`, o checkout do QR usa destination charge + `application_fee_amount` = comissão → parte do parceiro vai direta ao banco dele
- Connect só funciona depois do dono reclamar a conta Stripe e ativar Connect (dashboard.stripe.com/connect); até lá o endpoint responde `available:false` com explicação e o fluxo manual (IBAN) continua
- Recibo: cliente indica email opcional; após pagar vê recibo no ecrã (conta/desconto/pago/ref) com imprimir; email de recibo via Resend quando configurado. SMS não implementado (requer Twilio)

### 2026-09 · Capa com globo animado + IBAN da plataforma + domínio theclub.pt ✅
- Login hero: globo de pontos a girar com arcos de ligação animados (canvas, `GlobeCanvas.jsx`, inspirado na referência Cloudflare); também no fundo da página pública do cupom
- Admin › Definições: IBAN + titular da plataforma (`/api/admin/settings/iban`, `GET /api/public/bank`) para receber comissões/pagamentos por transferência manual
- Domínio escolhido: **theclub.pt** — `FRONTEND_URL`, remetente `noreply@theclub.pt` e placeholders atualizados (ligar em Publish › Domain)

### 2026-09 · Globo interativo + GIF ✅
- `GlobeCanvas` reage ao rato (velocidade e inclinação), marca as cidades dos parceiros ativos (`GET /api/public/cities`, coords em `CITY_COORDS`) com pulso âmbar e etiqueta "Cidade · nº parceiros"
- Globo estilo Cloudflare (sem etiquetas/interação por pedido do utilizador); IBAN também para influencers (extrato + Gestão + visível em Pagamentos). GIF do globo (600×600, 72 frames, PIL) em `/globe.gif` para redes sociais/apresentações

## Backlog priorizado
- P1: reclamar Stripe + ativar Connect e MB WAY; colar chave Resend; Publish + domínio
- P2: recibo por SMS (Twilio), push notifications, relatórios por parceiro em PDF

## Notas
- Seed corre só se coleções vazias; dropar DB para reseed.
- Cupões válidos no Tivoli: ROBSON-LUXE-25, MARTA-SKY-10, DIOGO-SKY-15.
