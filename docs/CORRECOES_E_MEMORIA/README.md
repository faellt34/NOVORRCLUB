# RRClub — Correções realizadas e memória de execução

Este diretório é a **fonte única de verdade** para saber o que já foi tratado, o que falta e como retomar sem repetir testes.

## Regras permanentes
- Nunca substituir a pasta `/app` do Emergent por um clone integral do GitHub sem comparar modificações locais.
- Nunca executar `git reset --hard` nem copiar integralmente ficheiros de pagamentos modificados no workspace.
- Nunca declarar um pagamento, uma transferência Stripe Connect ou um payout bancário como iguais.
- Nunca criar ou reassociar Connect por nome; validar IDs, país e moeda.
- Brasil Pix: credenciais e webhooks independentes do EUR Portugal.
- Um recebedor com KYC pendente é **um estado operacional normal**, não erro global da RRClub.
- P5: QR e aprovação do parceiro podem funcionar sem dinheiro; **checkout** exige políticas, destinatários e Stripe prontos.
- Não ativar flags `PT_SPLIT_LIVE_ENABLED` ou `PT_SPLIT_AUTO_TRANSFER` automaticamente.
- Preservar a versão publicada até verificação de pré-visualização e plano de rollback.

## Estado verificado em 21/10/2026
- **Integração V3 Emergent:** 12 ficheiros integrados com êxito na captura do Terminal; backup local criado; sem deploy.
- **Backend preview:** `GET /api/public/p5/config` respondeu HTTP 200, com `enabled=false` e moedas P5 desativadas.
- **Frontend preview:** dashboard geral abriu normalmente; não é prova de checkout, webhook ou split.
- **GitHub:** P5 QR individual e aprovação do parceiro integrados; regras de PT split 5/80/5/10 com flags estritas também foram desenvolvidas separadamente, porém **não confirmadas como sincronizadas no Emergent**.
- **Conta Connect do parceiro Portugal (leitura Stripe, 21/10):** conta associada corretamente por ID, mas `charges_enabled=false`, `payouts_enabled=false`, `transfers=inactive`, verificações KYC pendentes.
- **PT live split:** não confirmado operacional; sem prova de payout a parceiro ou influenciador.
- **Pix Brasil:** módulo separado existente; aptidão operacional real depende de configuração Pix Stripe Brasil e KYC dos dois beneficiários.

## Alterações novas desta etapa
- PR #11: `fix/p5-onboarding-independente-20261021`.
- Desacoplamento entre P5 QR e a prontidão do checkout para EUR/BRL.
- Novo estado `awaiting_connect` (recebimentos em ativação), sem cobrança nem transferência.
- Interface mantém QR e valor aprovado visíveis; pagamento bloqueado até confirmação financeira.
- **Nenhuma configuração financeira live é ligada por estas alterações.**

## Pendências por prioridade
1. Sincronizar patch P5 e flags de QR com **o workspace Emergent atual**, sem sobrescrever código local.
2. Verificar `/api/public/p5/config`: `enabled=true`; EUR/BRL QR true; checkout pode ficar false.
3. Testar o caminho seguidor → QR P5 → leitura pelo parceiro → conta aprovada → espera Stripe (sem dinheiro).
4. Confirmar autenticação, SSL, domínio, origem de checkout e estabilidade frontend antes de publicação.
5. Antes de testar dinheiro real, confirmar chave/região/webhook, beneficiários KYC, cálculo financeiro, prova de captura, transferências separadas e reconciliação.
6. Confirmar como a plataforma Emergent aplica variáveis .env ao ambiente de produção e ter rollback do último deploy.

## Links de referência
- Repositório: https://github.com/faellt34/NOVORRCLUB
- Integração P5 base: PR #10
- Correção QR + Connect pendente: PR #11
- Manual de apresentação comercial: `TREM_FODD_DEMONSTRACAO.md`

**Regra de segurança:** esta pasta não contém segredos, passwords, IBAN, e-mails privados nem dados KYC.
