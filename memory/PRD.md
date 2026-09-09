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

## Backlog priorizado
- P1: preencher RESEND_API_KEY e domínio verificado; traduzir conteúdos de dados (categorias/cidades) em EN/ES
- P2: Stripe Connect payouts automáticos, relatórios por parceiro em PDF, app mobile (PWA)

## Notas
- Seed corre só se coleções vazias; dropar DB para reseed.
- Cupões válidos no Tivoli: ROBSON-LUXE-25, MARTA-SKY-10, DIOGO-SKY-15.
