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

## Backlog priorizado
- P1: envio real de email de recuperação (Resend), cancelamento de subscrição pelo utilizador, i18n EN/ES
- P2: Stripe Connect payouts automáticos, CORS_ORIGINS explícito em produção, relatório PDF do extrato

## Notas
- Seed corre só se coleções vazias; dropar DB para reseed.
- Cupões válidos no Tivoli: ROBSON-LUXE-25, MARTA-SKY-10, DIOGO-SKY-15.
