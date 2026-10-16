# Resultado da validação local — Pix Brasil

16/10/2026. Branch local: `codex/pix-payments`. Base: `1c8131a`.

**Estado: preparado para homologação; não validado na Stripe real/sandbox da RR Club.**

- 38 testes Python passaram (31 do Pix, 3 dos relatórios e 4 do cadastro).
- 12 testes da tela de pagamento passaram.
- Build de produção do frontend: compilado com sucesso.
- Compilação Python e verificação de diff: sem erro.
- Nenhum push, deploy ou movimento financeiro real.
- `backend/routes_payments.py` de Portugal permanece igual à base.

## Regra financeira testada

Preço original R$100: desconto R$5; cliente paga R$95; parceiro R$80; influencer R$5; RR Club R$10 antes de pagar os custos. Todos os custos do processamento/repasses são da RR Club. Para centavos, o residual de arredondamento fica na parcela da plataforma, mantendo a soma igual ao valor cobrado.

## Evidências automatizadas

Os testes usam Stripe e Mongo simulados: cobrem autorização do parceiro, impedimento de cobrança criada pelo cliente, configuração brasileira,5/80/5/10, referências repetidas, alteração indevida de pedido, confirmação com valor/moeda incorretos, snapshot do influencer, reembolso parcial/total, disputa, falha no segundo repasse e retomada sem repetir o primeiro, e preservação da chave de Portugal. Também verificam cadastro brasileiro sem credenciais Stripe, separação dos IDs brasileiros e portugueses, bloqueio sem webhook/configuração exclusiva Pix e disponibilidade sem chamadas externas.
Na tela, cobrem valor confirmado pelo parceiro sem edição pelo cliente, espera, repetição da mesma referência, recibo mesmo com campanha expirada e confirmação do pagamento independente do andamento dos repasses.

## Falta verificar externamente

1. Conta Stripe brasileira habilitada para Pix e Connect.
2. Conta conectada brasileira do parceiro e do influencer, com recebimentos/transferências ativos.
3. Cobrança Pix no modo de teste e webhook brasileiro entregue com assinatura válida.
4. Dois repasses de teste nos valores80 e5; retenção10 menos tarifas reais.
5. Reversões parciais/totais e recuperação depois de falha.
6. Migração de índices e concorrência em MongoDB de homologação.
7. Correspondência da base GitHub com o projeto atualmente publicado no Emergent.

Não usar o antigo botão “Novo Teste” como comprovativo: ele não executa uma cobrança na Stripe.

Configuração e roteiro detalhado: `docs/PIX_SETUP.md`.
