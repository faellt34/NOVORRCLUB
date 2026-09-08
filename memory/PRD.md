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

## Backlog priorizado
- P1: recuperação de password por email (Resend), scanner de câmara real (QR), marcar mês como pago (admin) no extrato
- P2: subscrição premium dos e-books (Stripe), upload de PDF de e-books (Object Storage), Stripe Connect payouts, CORS_ORIGINS explícito em produção, i18n EN/ES

## Notas
- Seed corre só se coleções vazias; dropar DB para reseed.
- Cupões válidos no Tivoli: ROBSON-LUXE-25, MARTA-SKY-10, DIOGO-SKY-15.
