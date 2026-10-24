# RRClub · Pix Brasil · Configuração do backend

A integração Pix Brasil usa **exclusivamente** a conta Stripe brasileira.
Nunca coloque chaves reais, segredos de webhook ou dados bancários em Git,
no chat, em capturas de ecrã ou no código-fonte.

## Ambiente de execução

Os seguintes valores devem ser fornecidos **no ambiente de execução do backend**
por um gestor de segredos aprovado; o terminal de desenvolvimento e o backend
publicado podem ter variáveis diferentes.

| Variável | Função |
| --- | --- |
| `PIX_ENABLED=true` | Habilita Pix quando as outras verificações passarem |
| `PIX_STRIPE_PLATFORM_COUNTRY=BR` | Exige plataforma Brasil |
| `PIX_STRIPE_SECRET_KEY` | Chave secreta/restrita da **conta brasileira**, nunca igual à portuguesa |
| `PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION` | ID `pmc_...` da configuração de pagamento com Pix |
| `PIX_STRIPE_WEBHOOK_SECRET` | Signing secret `whsec_...` do endpoint Pix Brasil |
| `PAYMENT_ALLOWED_ORIGINS` | Origens HTTPS autorizadas; sem caminhos ou query strings |

`STRIPE_SECRET_KEY` pertence ao fluxo português existente e não deve ser
substituída pela chave brasileira.

**Importante:** o código não cria nem recupera credenciais secretas.
`pmc_...` identifica a configuração Pix; `whsec_...` verifica assinaturas
dos eventos Stripe no endpoint `/api/stripe/pix/webhook`.

## Diagnóstico seguro

O endpoint existente `/api/admin/pix/readiness` mostra apenas booleanos.
O endpoint `/api/admin/pix/provider-readiness` verifica o fornecedor Stripe
somente quando a configuração local está completa. Ambos requerem sessão
administrativa. O endpoint público `/api/public/pix/availability` mostra
apenas um resumo, **não** comprova cobrança, entrega de webhook ou repasse.

No arranque, `server.py` regista apenas os **nomes** dos checks ausentes;
não imprime valores ou credenciais. Configuração ausente impede novas cobranças
Pix Brasil, mas **não** deve derrubar o resto da RRClub ou o P5 Portugal.

## Antes de autorizar deploy financeiro

- Garantir as credenciais no ambiente real correto (não copiar segredos para Git).
- Confirmar que Stripe Brasil está em BRL, com Pix ativo e métodos exclusivos.
- Confirmar a URL exata, estado e eventos do webhook na Stripe; testar entrega
  autenticada e processamento idempotente.
- Conciliar `pix_stripe_account_id` de parceiro e criador com metadata Stripe e
  com os registos internos, sem adivinhar proprietários e sem duplicar contas.
- Confirmar que só pagamentos `paid` geram conversão e transferências.
- Validar reembolsos, disputas, reversões e idempotência em sandbox.
- Executar testes no mesmo ambiente de dependências do backend.
- Não executar cobrança ou repasse real sem autorização operacional específica.

## Teste unitário de configuração

```bash
cd /app
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -p 'test_pix_config.py'
```

O teste usa credenciais **fictícias**, não comunica com a Stripe.
