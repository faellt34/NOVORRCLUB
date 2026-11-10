# RRClub V1 · Homologação de acesso único (plano de implementação seguro)

Estado em 2026-11-10: a prévia Render é um **site estático** e bloqueia todas as chamadas da API centralizada. A entrada existente é demonstrativa e **não autentica**. A aplicação original já tem `GoogleSignIn.jsx` com Google Identity Services e API `/auth/google/config`, `/auth/google`, `/auth/me`. Este documento não ativa o login em produção.

## Resultado obrigatório

Um utilizador autenticado por Google com identidade administrativa e permissão explícita de revisão consegue navegar por três contextos: `admin`, `partner` e `influencer`. Cada vista mostra a identidade real da sessão, o papel que se está a **visualizar** e dados de teste. **Ver um painel não concede as permissões transacionais daquele papel.** As permissões reais continuam no servidor e nunca se baseiam no estado React, email visível ou `user_metadata`.

## Infraestrutura isolada

- Criar **projeto próprio RRClub Staging** (não reutilizar `motorede-dev`; não copiar dados reais).
- Criar serviço backend exclusivo de homologação, com `GOOGLE_CLIENT_ID` e validação de tokens Google pelo servidor; configurar os domínios e origens autorizados para a URL de preview.
- Segredos só no backend; não guardar client secret, private key, service role ou credenciais no GitHub ou `REACT_APP_*`.
- Estabelecer conjuntos de dados sintéticos de campanha/QR/checkout; sem pagamentos reais. Stripe deve ficar desligado até configuração própria de **test mode**, testes de webhook e aprovação de riscos.
- Configuração fail closed: se backend/Google não estiverem disponíveis, mostrar `Acesso indisponível`, não conceder administração.
- Não ligar `REACT_APP_BACKEND_URL` da prévia à API oficial e não permitir logout/login misturado entre preview e produção.

## Modelo de autorização

- `auth_identity`: `user_id`, `google_sub` único, email verificado, estado (ativo/revogado).
- `assigned_roles`: `user_id`, `role` (`admin|partner|influencer`), `workspace_id` de homologação, `active`; gestão exclusivamente por operações administrativas auditadas. Nunca atribuir `admin` a partir de email fornecido na UI.
- `reviewer_grants`: `user_id`, `can_impersonate_view`, âmbito permitido e validade; a permissão `can_impersonate_view` só dá acesso a **vistas de revisão de dados sintéticos**, não a ações financeiras ou de escrita em nome de terceiros.
- `audit_events`: identidade real, papel/vista escolhida, ação, resultado, timestamp UTC, `request_id` de correlação.
- RLS ativa para todas as tabelas expostas; validar `auth.uid()` e vínculos ao workspace. Não usar `raw_user_meta_data` para permissões.

## Contrato de relatórios

Para qualquer operação P5: `operation_id`, `campaign_id`, `partner_id`, `influencer_id`, `market`, `currency`, `base_amount_minor`, `discount_minor`, `state`, `created_at`, `updated_at`, `source`, `verified_at`, `payment_processor_ref` apenas quando confirmado e redigido em relatórios. Unicidade por `operation_id` e por identificador idempotente de evento.

Estados independentes: `qr_scanned`, `coupon_validated`, `checkout_opened`, `payment_started`, `payment_confirmed`, `payment_failed`, `expired`, `refunded`. Uma validação QR ou checkout aberto **não** deve somar receita confirmada. Sem backend de pagamentos testado, qualquer estado `payment_confirmed` deve permanecer indisponível, e não simulado como receita real.

## Critérios de aceite antes de dizer 'login Google validado'

1. Abrir URL de preview em sessão privada e entrar via Google; servidor valida assinatura, `iss`, `aud`, expiração, `sub`, nonce e email verificado.
2. Um Google `sub` autorizado visualiza as três áreas sem iniciar três sessões; identificação inequívoca na UI de **Admin / Parceiro / Influenciador (revisão)**.
3. Google `sub` comum não consegue chegar à vista administrativa (API deve devolver 403). Bloqueios persistem alterando URLs e pedidos diretos.
4. Trocar de papel não altera a identidade da conta nem permite receber, transferir, reembolsar, alterar dados de parceiro ou criar pagamentos.
5. Histórico sintético partilhado entre telemóvel/desktop e compatível com o workspace de homologação; acesso de outro utilizador não revela esses dados.
6. Logout invalida a sessão; testes de expiração/revogação do token e tentativa de replay.
7. Monitor de dados: sem duplicações, falhas de autorização, eventos de origem desconhecida, mistura de PT/BR ou dinheiro fictício contabilizado como receita.
8. Todas as verificações registadas com prova do ambiente e data; só então marcar **validado**.

## Pendências atuais

- A prévia já tem entrada de revisão sem password e seleção de perfis locais; isto NÃO é Google Sign-In.
- O único projeto Supabase conectado e verificado no momento é `motorede-dev`, portanto não será utilizado.
- Falta criar conta/projeto RRClub Staging sob uma organização escolhida pelo titular e configurar Google OAuth para o endereço da prévia.
- Não iniciar faturação, novas subscrições ou autenticação na produção sem concordância explícita.
