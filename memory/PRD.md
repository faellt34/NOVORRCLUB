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

### 2026-09 · Capa noturna yin-yang + vídeo story ✅
- Login hero: metade roxo #5B21B6 → metade céu noturno #08061A com estrelas a piscar (`@keyframes twinkle`), globo por cima
- Vídeo MP4 para stories (1080×1920, 5s, 30fps, logótipo ||Club, slogan, theclub.pt) em `/globe-story.mp4`; gerado por `/tmp/story.py` (PIL + ffmpeg) — não persistente, regenerar se necessário

### 2026-09 · Vídeo story personalizado por influencer ✅
- `GET /api/influencer/story-video/{campaign_id}` gera MP4 720×1280 (3 s, 30 fps, ~8 s de render, cache em `backend/media/`) com nome, handle, cupom, desconto/parceiro e `theclub.pt/c/CUPOM` (`story_video.py`, PIL + ffmpeg)
- Botão "Vídeo Story personalizado (MP4)" no cartão do cupom em destaque do dashboard do influencer
- Contas de exemplo em produção: influencer.exemplo@club.pt / influencer123 e parceiro.exemplo@club.pt / parceiro123 (apagar quando quiser)

### 2026-06 · QR finalizado: imagem PNG, partilha nativa, QR por campanha, scanner com foto ✅ (iteration_10: 5/5 backend, frontend 100%)
- `CouponQrDialog.jsx`: cartão PNG 1080×1350 com marca ||Club + QR + código + desconto/parceiro + link; botões Copiar / PNG / Partilhar (Web Share API com ficheiro → fallback WhatsApp) / Imprimir
- Botão QR em cada linha da tabela de campanhas do influencer e em Admin › Gestão › Campanhas (`qr-<id>`); cartão em destaque descarrega PNG em vez de SVG
- Scanner: mensagens de erro específicas (permissão / sem câmara / em uso / HTTPS), qrbox responsivo, fallback "Usar foto do QR" (`scanFile`, `capture=environment`) — validado E2E com upload de imagem
- Câmara real ainda por confirmar pelo utilizador num telemóvel (requer HTTPS + permissão)

### 2026-06 · Globo no telemóvel + Cartaz A5 ✅ (self-tested: curl PDF 200 + screenshots)
- Login mobile (<lg): fundo roxo/noite com `GlobeCanvas` centrado (modo portrait no canvas) atrás do painel de login em vidro (`login-hero-mobile`, `login-panel`)
- `GET /api/campaigns/{id}/poster.pdf?site=` (influencer/parceiro/admin, `poster.py` reportlab+qrcode): cartaz A5 com marca, desconto, QR, código, link; botão "Cartaz A5 para mesa / balcão" no diálogo QR (`coupon-qr-poster`)
- Publish + teste de câmara/partilha em telemóvel real: **ação do utilizador** (só possível após Publish no domínio HTTPS)

### 2026-06 · Rebrand RRclub + Checklist pós-Publish ✅ (iteration_11: backend 7/7, frontend 100%)
- Logo novo: `BrandLogo.jsx` / `BrandMark` (círculo de rede com nós/ligações — pessoas, redes sociais, influencers) + wordmark "RRclub"; substituiu coroa + "ןןClub" em login, sidebar, header mobile, registo, privacidade, recuperação, cupão público, manifest/index, PDFs, emails, story video e cartaz; ícones PWA regenerados (`brand.py`)
- Admin › Definições: card "Checklist pós-Publish (theclub.pt)" (`GET /api/admin/launch-check`, 11 itens: domínio, HTTPS, login, campanha ativa, cupão público no domínio final, scanner/partilha manuais, Resend, IBAN plataforma, IBAN parceiros, Stripe live) com pontuação e ações sugeridas
- Nota: domínio/cupão público ficam vermelhos até o utilizador fazer Publish + ligar theclub.pt (esperado)

### 2026-06 · Domínio rrclub.online + Onboarding parceiro 3 passos + QR no painel do parceiro ✅ (iteration_12)
- Domínio definitivo **rrclub.online** (FRONTEND_URL, remetente, cartaz, story, checklist); theclub.pt abandonado
- `PartnerOnboarding.jsx`: guia IBAN → Stripe Connect → primeiro cupão com estado por passo; desaparece quando 3/3
- Painel do parceiro: tabela "Os seus cupões QR" (`campaigns` no `/api/dashboard/partner`) com botão QR/Cartaz (mesmo `CouponQrDialog`); toasts para `?connect=return|refresh`
- Checklist admin: item `connect` (Stripe Connect ativo na conta da plataforma) → 12 itens
- **Stripe Connect continua indisponível**: a conta Stripe ligada à chave do projeto (acct_…gKY, modo test) não tem Connect ativado — o dono tem de ativar em dashboard.stripe.com › Connect (na MESMA conta) e depois colocar a chave live nos secrets de produção

### 2026-06 · Logo oficial Vesica Piscis ✅ (iteration_13)
- Marca do utilizador ("LOGO A PENSAR1.html"): dois círculos sobrepostos gradiente #B47BFF→#6E2BFF + ponto central, fundo #08040E→#1A0F2E; aplicada em `BrandMark`, ícones PWA (`brand.py`), cartaz A5, story video, manifest (theme #6E2BFF)

### 2026-06 · Bug: links de cupão com domínio errado ✅ (iteration_14)
- Causa: `FRONTEND_URL` no `backend/.env` estava `https://theclub.pt`; `story_video.py` tinha default `site="theclub.pt"`; `poster.py` tinha texto `THECLUB.PT`; frontend usava `window.location.origin` (preview) e o cartaz aceitava `?site=` do cliente
- Fix: tudo deriva de `FRONTEND_URL` (`GET /api/public/site` → `getSiteUrl()` no frontend; cartaz/story/checklist só leem env; sem fallbacks hardcoded); cache de vídeos antigos removida

### 2026-06 · Checklist email + RESEND_FROM ✅ (iteration_16)
- Bug: `launch_check` chamava `mailer.configured()` sem `load_settings()` → "Email não configurado" falso; corrigido
- `mailer.py` lê remetente por ordem: settings (Admin UI) → `RESEND_FROM` → `SENDER_EMAIL`; `.env` tem `RESEND_FROM="RRclub <pedidos@rrclub.online>"` (RESEND_API_KEY do .env está vazio; a chave ativa está em settings via Admin › Definições)
- Nota: remetente atual guardado nas settings é um gmail — alterar para pedidos@rrclub.online em Admin › Definições depois de verificar o domínio no Resend

### 2026-06 · Dashboard Admin em tempo real (WebSocket) ✅ (iteration_17: backend 7/7, frontend 100%)
- `backend/realtime.py`: `/api/ws/dashboard?token=` (só admin, fecha 4401), `emit()`/`broadcast()`; eventos `split_executado` (redenção loja + pagamento QR), `indicacao_criada`, `cupons_gerados`, `erro_transferencia` (webhook Stripe failed/transfer.failed)
- Frontend: `services/ws.js` (`useRealtime`, URL = origin→ws + `/api/ws/dashboard`, reconnect exponencial, ping 20s), `services/live.js` (`useCountUp`, `useFlash`), `KpiCard` com `live`/`flash`, `AdminDashboard` com estados, audit log limitado a 8, `.enter`, `.amt`, badge `ws-status`
- CSS: `.stat-val.updating`/`numFade`, `.stat.live-updated`, `.audit-item.enter`, `.amt`
- Dados de teste (redenções/claims/audit de CLUB-10) limpos

### 2026-06 · Tempo real influencer/parceiro + Cliques Recentes ✅ (iteration_18: backend 10/10, frontend 100%)
- `realtime.py` com filtro por papel (admin tudo; influencer/parceiro só os seus `influencer_id`/`partner_id`); novo evento `clique_cupao` (com `origem`); `split_executado` inclui `record`
- Influencer: KPIs ao vivo (usos, clientes, receita, comissão) + toast de venda; Parceiro: KPIs ao vivo + nova redenção entra no histórico com `.enter`; badges "ao vivo"
- Admin › "Cliques Recentes" (`RecentClicks.jsx`, `GET /api/admin/clicks?period=today|7|30`, máx 100): Data/hora · Origem (`?src=`/UA/referer → Instagram/WhatsApp/Facebook/TikTok/QR direto) · Influencer · Campanha · Status (Converteu = redenção da campanha até 7 dias após o clique) + Export CSV; atualiza ao vivo
- Dados de teste limpos

### 2026-06 · KPIs de funil no Admin ✅ (iteration_19)
- `/api/dashboard/admin` → `funnel` {clicks, uses, not_used, conversion, ticket, origins[]}; 2.ª linha de KPIs: Pessoas que usaram cupom · Cliques · Clicaram e não usaram · Taxa de Conversão · Ticket Médio; card "Origens dos cliques" com barras; tudo atualiza ao vivo

### 2026-06 · Análise de Abandono em tempo real ✅ (iteration_20: backend 6/6, frontend 100%)
- `coupon_claims` ganha `qr_downloaded/_at`, `converted/_at`, `valor`, `cliente`, `created_at`; `GET /api/public/coupon/{code}` devolve `claim_id`; `POST /api/public/coupon/{code}/qr-downloaded`; redenção marca o clique mais recente da campanha como convertido (`mark_converted`)
- `GET /api/admin/cliques/analysis?period=hoje|7d|30d` → {total, sem_download, qr_sem_scan, convertidos, lista}; estados: Converteu / QR sem scan / Sem download / Abandonou (+48h)
- WS: novos eventos `novo_clique{dados}`, `qr_baixado`, `venda`, `cupom_gerado` (mantidos os antigos); `useRealtime` devolve `{status, eventos}`; badge `ws-indicator` WS · Conectado/Reconectando/Offline
- `AbandonAnalysis.jsx` (substitui RecentClicks): 4 KPIs clicáveis que filtram, tabela "Cliques Individuais" com timeline por linha, Export CSV filtrado, animações 700ms + flash violeta
- Botão "Guardar QR" na página pública `/c/CODE` (regista download)
- **Todos os dados de teste apagados** (redemptions, claims, audit, notificações, leads, feedback, mensagens, payouts, transações QR) — contas/campanhas/e-books mantidos

### 2026-06 · Reset-all + Modo Teste completo + venda_validada ✅ (iteration_21: backend 9/9, frontend 100%)
- `routes_test.py`: `POST /api/admin/reset-all {confirm:"RESET-ALL"}` (apaga dados operacionais; mantém users/campanhas reais/settings) — **executado, dashboard a 0**
- `POST /api/admin/test-run {influencer_id, partner_id, valor}` simula campanha `is_test` TEST-XXXXXX → clique → QR → pagamento (simulado, sem Stripe real) → split 75/5/10/10; emite `teste_passo` 1..6 + todos os eventos reais; `DELETE /api/admin/test-run/{run_id}`; `POST /api/admin/test-run/clear-all {confirm:"LIMPAR"}`
- Frontend: botão "🎬 Novo Teste" + `TestRunDialog.jsx` (passo-a-passo ao vivo, split, Ver dashboard / Limpar este teste); botão fixo "🗑️ Limpar TODOS os testes" com confirmação LIMPAR; `useRealtime` devolve `ultimoEvento`, backoff até 30s; evento `venda_validada`

### 2026-06 · Claude AI Analista + botão RESET-ALL ✅ (iteration_22)
- `routes_ai.py`: `POST /api/admin/ai/ask` (SSE streaming, Claude Sonnet 4.6 via emergentintegrations + EMERGENT_LLM_KEY, contexto = dados reais 30d, histórico em `ai_messages`), `GET /api/admin/ai/history`
- `AiAnalyst.jsx` no Admin: sugestões, chat com streaming, multi-turn por sessão, reset
- Botão "🧨 Apagar TODOS os resultados" (RESET-ALL) no header do Admin → zera qualquer ambiente (útil para produção rrclub.online)

### 2026-06 · Legendas IA para influencer ✅ (iteration_25)
- `POST /api/influencer/ai/captions {campaign_id, tom}` → 2 legendas × PT/EN/ES via Claude Sonnet 4.6 (JSON estrito); `CaptionDialog.jsx` no cartão em destaque do influencer (tons elegante/divertido/urgente, tabs de idioma, copiar com link)

### 2026-06 · Gemini (Nano Banana) imagem de story para influencer ✅ (iteration_26)
- `POST /api/influencer/ai/story-image {campaign_id, estilo}` → imagem 9:16 (gemini-3.1-flash-image-preview) com prato/ambiente do parceiro, "X% OFF", código e marca RRclub; `StoryImageDialog.jsx` (estilos Luxo/Fresco/Noite, guardar PNG, partilhar nativo)

### 2026-06 · Chat "Diretor" (Gemini 2.5 Flash) com aprovação do CEO ✅ (iteration_27: backend 6/6, frontend 100%)
- `routes_diretor.py` (`/api/diretor/*`, admin): loop de function-calling em JSON; leitura (ler_dashboard, listar_hoteis, listar_influencers, analisar_performance_hotel, consultar_financeiro) executa direto; escrita (criar_campanha, gerar_contrato, enviar_email, gerar_qr_code) vai para `acoes_pendentes` → aprovar executa (campanha real com cupão + WS; contrato em `contratos_gerados`; email via Resend; qr_code_url) / rejeitar
- Coleções: `conversas_diretor`, `acoes_pendentes`, `contratos_gerados` (+ `campaigns` existente com `data_inicio`, `formato`, `qr_code_url`)
- Página `/admin/diretor` ("Diretor IA" na sidebar): chat com histórico + painel Ações Pendentes/Aprovadas/Rejeitadas
- Nota: stack real é FastAPI+React+Mongo (não Next.js); usa EMERGENT_LLM_KEY (não GEMINI_API_KEY). Dados de teste limpos. **Não publicado** — aguarda teste do utilizador.

### 2026-06 · Subagentes reais do Diretor ✅ (iteration_28)
- `subagente_marketing(pergunta)` (dados de campanhas/funil/financeiro), `subagente_frontend(pergunta, ficheiro?)` e `subagente_backend(pergunta, ficheiro?)` (leem código real em `frontend/src` e `backend/`, só leitura, com índice + seleção de ficheiros por palavras-chave) — cada um chama Claude Sonnet 4.6; o Diretor (Gemini) integra as conclusões; `chamadas[].resumo` mostrado em painéis "🧩 Subagente" na página Diretor
- Achados do subagente Backend a considerar: `/payments/status/{session_id}` sem auth; webhook aceita payload se `STRIPE_WEBHOOK_SECRET` vazio; token JWT em query string no PDF de e-books

## Backlog priorizado
- P1: reclamar Stripe + ativar Connect e MB WAY; colar chave Resend; Publish + domínio
- P2: recibo por SMS (Twilio), push notifications, relatórios por parceiro em PDF

## Notas
- Seed corre só se coleções vazias; dropar DB para reseed.
- Cupões válidos no Tivoli: ROBSON-LUXE-25, MARTA-SKY-10, DIOGO-SKY-15.
