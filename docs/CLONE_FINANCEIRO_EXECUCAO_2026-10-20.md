# RRClub — execução e segurança financeira (clone)

## Implementado exclusivamente na branch BRANCH-copia-editar-a-vontade

- Isolamento obrigatório antes do primeiro acesso à BD: RRCLUB_CLONE_ISOLATED=true, DB_NAME começando com rrclub_clone_, FRONTEND_URL HTTPS fora do domínio oficial e segredos Stripe apenas sk_test_.
- Arranque: não modifica Stripe Tax, não cria produtos/preços Stripe automaticamente e não inicia storage externo por defeito.
- Utilizadores: seed com logins de demonstração desativada salvo RRCLUB_DEMO_DATA_ENABLED=true e sk_test_ configurada.
- Maria Eduarda BRL/EUR: fixtures sintéticas separadas, sem contas Stripe Connect reais nem alteração de utilizadores de produção.
- Checkout EUR: Decimal, verificação de campanha ativa/não expirada, valor e metadados, origin HTTPS autorizado.
- Webhook EUR: assinatura, montante, moeda, modo, ID, campanha/parceiro verificados antes de qualquer venda contabilizada.
- Confirmação EUR: guarda redenção idempotente antes de marcar transação paga, permite retry após falha na base de dados e recupera registos pagos sem redenção de versões anteriores.
- Split Portugal opcional: PT_SPLIT_V2_ENABLED=true é aceite SÓ com chave sk_test_ PT. Requer dois beneficiários Stripe Connect PT aptos, verificando estado e titularidade por metadata. 80% gross ao parceiro, 5% gross influencer, 10% gross à plataforma antes das taxas.
- Reembolsos PT no novo split: reversões proporcionais, ledger negativo idempotente, retenção de comissões em disputa; nenhum pagamento em produção.
- Pix Brasil: separado do EUR, com elegibilidade Connect obrigatória, idempotência, assinatura, refund/reverse e testes offline.
- Administração: RESET ALL e LIMPAR negam sempre (HTTP 403), preservando histórico.

## AINDA NÃO VERIFICADO OU AUTORIZADO

- Sem transações reais, sem criação de contas Connect reais e sem cobrança; os testes automáticos usam assinaturas locais e mocks.
- Sandbox Stripe TEST remoto requer Secrets PT e BR com sk_test_, configuração de Pix TEST, webhooks TEST e ambiente Mongo isolado.
- O preview antigo da Emergent e a branch operacional integracao-google-rrclub-20261019 NÃO são clones e NÃO podem ser alterados para o teste.
- A rota EUR legada ainda não faz split automático completo de influencer; apenas a nova versão sandbox opt-in suporta simulação do 80/5/10.
- A auditoria jurídica/fiscal, RGPD/LGPD, obrigações Connect Platform Profile e liquidação bancária não são certificadas por testes unitários.
- Perfis Connect incompletos são bloqueados na nova rota PT e na rota Pix. Cliques históricos não significam comissão paga.
- Deploy produção e merge não autorizados.

## Configuração obrigatória de novo clone Emergent (sem colar chaves nesta conversa)

1. Novo projeto a partir do repositório faellt34/NOVORRCLUB, branch BRANCH-copia-editar-a-vontade (não reutilizar o projeto rrclub).
2. Mongo separado e DB_NAME=rrclub_clone_dev; RRCLUB_CLONE_ISOLATED=true.
3. FRONTEND_URL=https://DOMINIO-CLONE.preview.emergentagent.com e PAYMENT_ALLOWED_ORIGINS apenas com essa origem.
4. STRIPE_SECRET_KEY=sk_test_... Portugal; STRIPE_WEBHOOK_SECRET=whsec_... para o clone.
5. PIX_STRIPE_SECRET_KEY=sk_test_... Brasil; PIX_STRIPE_PLATFORM_COUNTRY=BR; PIX_STRIPE_WEBHOOK_SECRET=whsec_...; PIX_STRIPE_PAYMENT_METHOD_CONFIGURATION=pmc_... só TEST.
6. PT_SPLIT_V2_ENABLED=false inicialmente. Ligar true apenas no sandbox com duas contas PT Connect TEST já verificadas.
7. Opcional: MBWAY_PT_SANDBOX_ENABLED=true; MBWAY_PT_SANDBOX_SECRET_KEY=sk_test_...; MBWAY_PT_SANDBOX_ALLOWED_ORIGINS apenas clone.
8. Verificar assinaturas, fluxo pago em teste, duas transferências, refunds e disputas; não simular com contas live.

Estado: IMPLEMENTAÇÃO E TESTES SIMULADOS APROVADOS; TESTE COM STRIPE REMOTA PENDENTE; PRODUÇÃO NÃO ALTERADA.
