# P5 Portugal · QR individual + conta aprovada pelo parceiro + MB WAY

Data: 21/10/2026. Escopo: corrigir o primeiro scan no estabelecimento e ativar a interação P5 em EUR.

## Causa reproduzível identificada no código

O parceiro passava `preserveRaw={p5Mode}` ao QrScannerDialog; como `p5Mode` depende da pré-visualização de uma campanha (que chega apenas depois da leitura), o primeiro scan eliminava `?p5_ref=...`. Consequência: o parceiro recebia o cupão genérico, mas perdia a sessão única do seguidor.

Além disso, P5 Portugal só aparece quando as flags P5_ENABLED e P5_EUR_ENABLED estão ativas **e** a campanha é elegível (desconto 5%, comissão 5%, influencer_id preenchido). Uma campanha antiga com outras taxas permanece no fluxo legado.

## Implementação

- O scanner entrega a URL QR bruta sempre; o parser próprio valida origem e referência pessoal.
- A tentativa de validar uma referência P5 de outro domínio é rejeitada e não cai numa redenção manual.
- Cada nova sessão de seguidor recebe nova chave de idempotência.
- O seguidor vê valor, desconto e total já aprovados pelo parceiro, sem editar o valor.
- Quando Portugal ainda não pode cobrar, a opção MB WAY/cartão aparece **desativada e identificada** como pendente, em vez de simular um checkout.
- O script `scripts/rrclub_p5_portugal_ativar_qr.py` aplica um merge seletivo e liga **apenas** P5_ENABLED e P5_EUR_ENABLED no .env local, com backup e paragem em caso de conflito. Não altera P5_BRL_ENABLED, PIX_ENABLED, PT_SPLIT_* nem as chaves Stripe.
- P5 PT usa a rota financeira existente, protegida por `pt_split.automatic()`, confirmação do pagamento pela Stripe e validação do parceiro e influenciador por ID/Connect.

## Validação antes de publicar

1. `python3 scripts/rrclub_p5_portugal_ativar_qr.py --check`
2. `python3 scripts/rrclub_p5_portugal_ativar_qr.py --apply`
3. `python3 -m compileall -q backend`
4. `cd frontend && CI=true npm test -- --watchAll=false --runInBand --testPathPattern='p5Scan|P5FollowerPanel'`
5. `cd frontend && npm run build`
6. Deploy controlado; verificar QR individual no telemóvel do seguidor, scan inicial pelo parceiro, valor aprovado, estado pendente ou MB WAY, webhook de pago, sem segunda cobrança.

## Restrição financeira

**Não é autorizada cobrança live automaticamente**. A ativação da interação QR EUR é independente de PT_SPLIT_ENABLED, PT_SPLIT_LIVE_ENABLED e PT_SPLIT_AUTO_TRANSFER. Sem os dois destinatários Connect corretamente ligados e aptos, o backend devolve awaiting_connect e não abre Stripe Checkout. Não inventar transferências ou estados pagos. Não faz deploy.

## Observação

O estado real da base MongoDB/Connect no Emergent não está confirmado a partir do GitHub. A campanha deve ter exatamente as condições de elegibilidade e o ambiente publicado deve preservar as flags P5; a Stripe deve mostrar MB WAY como método elegível.
