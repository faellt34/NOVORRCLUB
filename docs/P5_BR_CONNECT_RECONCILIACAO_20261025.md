# RRClub Brasil — reconciliação segura de dois beneficiários P5 (25/10/2026)

Estado: preparado para execução **manual e supervisionada**, nunca executado por commit/deploy.

## Evidências recolhidas

- RRCLUBRASIL (live): `acct_1URXWqEKAxcuX59L`, BRL, Pix ativo, cobranças e depósitos habilitados, payout diário.
- Existe uma configuração live ativa que disponibiliza **somente Pix**.
- Webhook ativo em `https://rrclub.online/api/stripe/pix/webhook` com os oito eventos exigidos em `backend/payments/pix/checks.py`.
- Sheyson: `acct_1URxAICihW3I0NpA`, BRL, transferências ativas, depósitos habilitados, diário, metadados vazios.
- Amor Gostoso/Josicleide: `acct_1URwhrCiKOcSLJUr`, BRL, transferências ativas, depósitos habilitados, diário, metadados vazios.
- Os IDs internos `if-da6af205f9` (Sheyson) e `p-fc194b8f5c` (Josicleide) foram confirmados **em registos anteriores do MongoDB Viewer Production** em 18–19/10. Necessitam **reconfirmação na base live atual** antes de qualquer alteração.

## Procedimento

Executar no backend da RRClub, com as credenciais BR já normalmente configuradas:

1. Leitura sem alterações (obrigatória): `python scripts/reconcile_br_connect_metadata.py`
2. Confirmar que mostra **ambas** as associações aptas, nomes das coleções e base de produção certa. Se houver `BLOQUEADO`, parar; não criar contas nem tentar adivinhar IDs.
3. Apenas após revisão/consentimento da operação e com o nome exato da base apresentado no passo 1: `python scripts/reconcile_br_connect_metadata.py --apply --confirm-db NOME_DA_BASE`
4. O comando valida novamente ambos os cadastros e contas **antes** de escrever metadados; reconsulta cada conta após escrita. Se estiver já correto, não altera.

Nunca executar no `test_database` nem usar contas de países diferentes. O script só pode adicionar o metadado de identificação ao destinatário existente; não toca em IBAN, KYC, descontos, campanhas, cobranças, transferências, reembolsos ou registos Mongo.

**Mesmo após reconciliação:** ainda é necessário um teste P5 real consentido (QR → scan → Pix pago → webhooks → dois IDs Stripe Transfer) para confirmar o funcionamento. A existência da chave ou do metadado não prova liquidação.
