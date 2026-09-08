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
### Fases 1-2 completas ✅ (testado: iteration_1.json — 100%)
- Shell: sidebar escura desktop + drawer mobile, logo, perfil com role switcher, badge Mensagens, card "Indique um parceiro"
- Influencer Dashboard: saudação, seletor de período (7/30/90 dias, KPIs recalculam), sino de notificações, 4 KPI cards com variação %, gráfico de área roxo "Evolução de Utilizações", Top Parceiros, tabela Campanhas Ativas com busca + filtro de status + empty state, Cupom em Destaque (pílula roxa + QR + copiar/download/partilhar com toasts)
- Partner Dashboard: 5 KPIs computados live das redenções, leaderboard de influencers, formulário de validação (código ou scanner simulado → preview do cupom → cálculo live de desconto/comissão → validar → recibo + histórico + KPIs atualizam), taxa travada por redenção, idempotência simulada (janela 5s), export CSV real (blob download)
- Admin (leve): métricas globais, campanhas recentes com badges, Audit Log somente-leitura (recebe entradas REDENÇÃO da sessão)
- Testado E2E: iteration_1.json — 100% frontend pass

### Fases 3-4 (parcial) ✅ (testado: iteration_2.json — 100%)
- E-books Premium (`/ebooks`): grid de 8 guias com filtros por região (Lisboa/Porto/Algarve/Douro) e categoria; cards premium bloqueados (capa desfocada + badge + toast de subscrição), gratuitos com modal de preview; empty state
- Admin CRUD (`/admin/gestao`): tabs Usuários/Influencers/Parceiros/Campanhas, create/edit/delete config-driven com dialog, taxa de comissão definida na campanha, validação de campos, tudo gera entradas no audit log (CRIAÇÃO/EDIÇÃO/REMOÇÃO)
- Extrato Mensal (`/influencer/extrato`): seletor de mês, KPIs do mês, tabela por campanha com taxa travada, total de comissão, status Pago/Pendente (payout offline), export CSV
- Indicação funcional: "Indicar agora" abre formulário (nome, categoria, cidade, contacto, nota) → lead aparece no admin (card "Indicações de Parceiros" + badge) + entrada INDICAÇÃO no audit log

## Backlog priorizado
- P1 (Fase 4 restante): hub de mensagens + notificações automáticas, skeletons/estados de erro adicionais
- P2 (Fase 5): Backend real FastAPI + MongoDB (idempotência/trava de comissão/audit server-side), Stripe Connect payouts, Object Storage e-books, e-mail

## Notas
- Estado é in-memory (reset ao recarregar) — esperado no v1
- Cupons válidos no parceiro Tivoli: ROBSON-LUXE-25 (15%/10%), MARTA-SKY-10, DIOGO-SKY-15; ROBSON-DOURO-10 = Expirada
- Sem auth real — nenhuma credencial necessária
