# Robson Club — PRD

## Problema original
Multi-Tenant SaaS que conecta influencers de experiências de luxo com parceiros (restaurantes, hotéis, rooftops, passeios) em Lisboa/Porto/Algarve/Douro. Influencers geram vendas via cupons/QR; parceiros recebem atribuição de receita mensurável. Modo de build: protótipo front-end revisável (React + Tailwind, dados/auth mock) arquitetado para receber backend FastAPI + MongoDB depois. PT-PT, EUR, comissão padrão 10% (configurável por campanha), track-only v1, redenção via scan de QR pelo staff.

## Arquitetura
- Frontend-only: React 19 + Tailwind + shadcn/ui + Recharts + qrcode.react + lucide-react + sonner
- Camada de dados trocável: `src/context/AppContext.jsx` (mock agora → API depois), `src/lib/mockData.js`
- RBAC simulado com profile switcher (Admin / Influencer / Partner) na sidebar
- Rotas: `/influencer`, `/parceiro`, `/admin`, `/mensagens` e `/ebooks` (placeholders)
- Backend `server.py` intocado (template) — fase 5
- Design: tema claro #F8F9FC + acento roxo #7C3AED, sidebar escura #0C0A14 (ver /app/design_guidelines.json)

## Personas
- Admin: gere plataforma, entidades, audita
- Influencer (Robson): promove campanhas, acompanha conversões + comissão
- Partner (Tivoli Sky Bar): valida cupons, vê receita atribuída e comissões devidas

## Implementado (2026-06)
### Fases 1-2 completas ✅
- Shell: sidebar escura desktop + drawer mobile, logo, perfil com role switcher, badge Mensagens, card "Indique um parceiro"
- Influencer Dashboard: saudação, seletor de período (7/30/90 dias, KPIs recalculam), sino de notificações, 4 KPI cards com variação %, gráfico de área roxo "Evolução de Utilizações", Top Parceiros, tabela Campanhas Ativas com busca + filtro de status + empty state, Cupom em Destaque (pílula roxa + QR + copiar/download/partilhar com toasts)
- Partner Dashboard: 5 KPIs computados live das redenções, leaderboard de influencers, formulário de validação (código ou scanner simulado → preview do cupom → cálculo live de desconto/comissão → validar → recibo + histórico + KPIs atualizam), taxa travada por redenção, idempotência simulada (janela 5s), export CSV real (blob download)
- Admin (leve): métricas globais, campanhas recentes com badges, Audit Log somente-leitura (recebe entradas REDENÇÃO da sessão)
- Testado E2E: iteration_1.json — 100% frontend pass

## Backlog priorizado
- P0 (Fase 3): Admin CRUD completo (Usuários, Influencers, Parceiros, Campanhas), audit log persistente
- P1 (Fase 4): E-books/Guias premium (tags de local + categorias, preview público + premium bloqueado), hub de mensagens + notificações, formulário de indicação de parceiro funcional, skeletons/estados de erro
- P2 (Fase 5): Backend real FastAPI + MongoDB (idempotência/trava de comissão/audit server-side), Stripe Connect payouts, Object Storage e-books, e-mail

## Notas
- Estado é in-memory (reset ao recarregar) — esperado no v1
- Cupons válidos no parceiro Tivoli: ROBSON-LUXE-25 (15%/10%), MARTA-SKY-10, DIOGO-SKY-15; ROBSON-DOURO-10 = Expirada
- Sem auth real — nenhuma credencial necessária
