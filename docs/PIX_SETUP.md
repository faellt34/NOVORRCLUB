# Pix Brasil: implementação para homologação

Base: `faellt34/NOVORRCLUB`, revisão `1c8131a` da branch main.
O Google ficou separado na branch local `codex/google-login-local`. Não integra esta alteração.
Nenhum push, deploy ou pagamento real foi feito.

## Percurso implementado

1. O administrador cria o parceiro brasileiro com moeda `brl` e campanha vinculada. A moeda da campanha é salva e deve corresponder ao parceiro.
2. O influencer distribui o QR/link da campanha. O cliente recebe o cupom; isso ainda não é pagamento.
3. No estabelecimento, o parceiro autenticado lê o cupom e confirma o valor original da conta.
4. “Gerar cobrança Pix” chama `POST /api/partner/pix/checkout`. O servidor verifica que a campanha pertence ao parceiro e calcula desconto e taxa em centavos.
5. O parceiro mostra o QR/link da cobrança. O cliente abre essa cobrança e segue para o checkout Stripe, com QR Pix e copia e cola. O cliente não escolhe nem altera o valor da cobrança.
6. O webhook com assinatura ou a consulta autenticada à API Stripe confirma pagamento. Apenas `paid` com valor/moeda corretos gera registro de venda. Ler o cupom/gerar cobrança não confirma compra.
7. Reembolsos parciais e totais produzem ajuste negativo idempotente; disputas retêm a comissão para revisão manual.

O QR de campanha/cupom é diferente do QR da cobrança Pix. A tela do parceiro também pode apresentar um QR de link para abrir a cobrança no celular do cliente; dentro do checkout a Stripe fornece o QR financeiro Pix.

## Configuração de homologação

Preservar a configuração de Portugal. Não substituir chaves de produção para testar. Usar uma instância e banco de homologação.

Backend:

```dotenv
PIX_ENABLED=false
PIX_STRIPE_PLATFORM_COUNTRY=BR
PIX_STRIPE_SECRET_KEY=<chave de TESTE da conta BR habilitada para Pix/Connect>
PIX_STRIPE_WEBHOOK_SECRET=<segredo do webhook Pix BR de TESTE>
PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION=pmc_<configuração de TESTE somente Pix>
FRONTEND_URL=https://rrclub.online
PAYMENT_ALLOWED_ORIGINS=https://rrclub.online,https://www.rrclub.online
CORS_ORIGINS=https://rrclub.online,https://www.rrclub.online
```

Autorizar a origem exata de homologação se ela for diferente. Não colocar chaves no GitHub ou no frontend.
Manter `MONGO_URL`, `DB_NAME`, `JWT_SECRET` e `REACT_APP_BACKEND_URL` conforme ambiente.

No Stripe, verificar Pix ativo e compatibilidade da plataforma com a conta conectada brasileira e as transferências de destino. A elegibilidade precisa ser conferida na conta; Portugal funcionando com cartão/MB WAY não comprova Pix/Connect Brasil.
O onboarding Pix cria conta Express BR. O recebimento exige `charges_enabled` e `payouts_enabled` verificados. A disponibilidade de criação de conta BR depende da plataforma e do contrato Stripe.

Webhook dedicado brasileiro: `POST /api/stripe/pix/webhook`. Preservar chaves e endpoint de Portugal; utilizar as variáveis PIX_STRIPE_* somente no Brasil.
Habilitar:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `checkout.session.expired`
- `charge.refunded`
- `charge.dispute.created`, `charge.dispute.updated`, `charge.dispute.closed`

Após configuração, ativar `PIX_ENABLED=true` somente em homologação para testar. Continuar com `false` na produção até aprovação.

## Cadastro antes da ativação

O cadastro permite escolher Brasil (BRL) ou Portugal (EUR) sem chamar a Stripe. Parceiros brasileiros continuam sujeitos à aprovação; influencers podem entrar na plataforma. Vincular recebimentos é uma etapa posterior. A escolha inicial define a moeda dos relatórios no login.

As contas Connect brasileiras ficam nos campos `pix_stripe_account_id` e `pix_stripe_*`, separados dos campos portugueses `stripe_account_id`. Um influencer pode ter os dois cadastros financeiros.

O painel Definições mostra a configuração local do Pix, sem revelar segredos. `GET /api/public/pix/availability` informa disponibilidade sem consultar o provedor; isso não certifica a validade das credenciais. A integração verifica o país real da plataforma antes de criar contas conectadas. O checkout exige configuração exclusiva para Pix e rejeita uma sessão que ofereça outro método.

## Divisão e custos: condição de liberação

Regra acordada: sobre o valor original100, desconto5, cliente paga95, parceiro80, influencer5 e RR Club10. A RR Club assume as tarifas de processamento, Connect, repasses e IOF aplicável dentro dos10. Os repasses devem ser registrados separadamente, com IDs e estado de liquidação. A confirmação da compra não comprova que ambos os repasses já foram concluídos. Validar essa divisão integralmente no sandbox brasileiro antes da produção.

Na cobrança Pix a opção `amount_includes_iof=always` evita acrescentar IOF ao valor apresentado ao cliente em pagamentos internacionais; o custo é absorvido na liquidação quando aplicável. Validar suporte e custos com a conta Stripe. Tarifas, impostos e conversão cambial podem reduzir o valor líquido; nenhum valor de tarifa foi inventado no código.

## Validação local e externa

Testes locais:

```bash
PYTHONPATH=backend python -m pytest -c /dev/null backend/tests/test_payment_policy.py backend/tests/test_pix_service.py backend/tests/test_pix_registration.py -q
python -m compileall -q backend
cd frontend
CI=true npm test -- --watch=false --runInBand --testPathPattern=PublicCoupon.test.jsx
CI=true GENERATE_SOURCEMAP=false npm run build
```

Testes locais usam mocks de Stripe/Mongo; não certificam conexão bancária ou pagamento real. A instalação local de build utiliza AJV8 para a cadeia de ferramentas instalada por npm; o contrato de dependências original continua no yarn.lock.

Antes do deploy pago, validar em homologação Stripe: parceiro BR verificado; cobrança e QR reais de teste; sucesso; espera; expiração; resposta interrompida e repetição do mesmo pedido; webhook duplicado; reembolso parcial e total; disputa; recebimento e taxa na conta destino. Conferir também que o checkout EUR continua igual.

Os relatórios possuem seletor EUR/BRL e não somam moedas. Históricos sem moeda continuam EUR. A migração de startup inclui moeda na chave dos registros mensais de repasse; testar com backup do banco de homologação antes da produção.

O botão antigo “Novo Teste” é simulação local e não comprova a integração Pix.

## Limites ainda não certificados

- Credenciais, habilitação Pix e permissão Connect BR da conta real.
- Execução em MongoDB real, inclusive migração e concorrência de webhooks.
- Execução externa dos repasses nos valores80/5/10, com cliente pagando95.
- Correspondência entre a revisão GitHub usada e o código atualmente publicado no Emergent.

Até essas verificações, o estado é **código preparado para homologação**, não produção validada.
