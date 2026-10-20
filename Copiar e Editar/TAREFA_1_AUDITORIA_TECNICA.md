# Tarefa 1 — auditoria técnica complementar (20-10-2026)

Branch analisada: BRANCH-copia-editar-a-vontade. Produção não modificada.

## Evidência verificada: backend/routes_pix.py
- Linhas 172–194: endpoint público apenas retoma pedido já criado; parceiro autenticado inicia cobrança e valida titularidade da campanha.
- Linhas 197–237: pedido identificado por UUID, valida código de cupão, estado e validade de campanha, moeda BRL, contas Stripe Connect e grava atribuição da campanha, parceiro e influenciador.
- Linhas 138–150: função totals exige desconto de 5% e comissão de 5% no fluxo Pix BR; portanto não aplicar automaticamente desconto P5 de 10% ao Pix.
- Linhas 245–252: Stripe Checkout recebe valor líquido em centavos e metadados de pedido.
- Linhas 506–520: webhook Stripe verifica assinatura.
- Linhas 228–233: transação armazena montantes de parceiro, influenciador e plataforma, com split pendente e bloqueio de pagamento manual.

## Lacunas e limites
- Ainda não verificados os módulos de checkout EUR, QR, código único offline, registo de prémios, pagamento em dinheiro, nem o fluxo completo de reconciliação.
- Caminhos backend/routes_checkout.py e backend/routes_coupons.py não existem, mas podem ter nomes diferentes.
- A análise de código é estática; não foram executados testes funcionais.
- RGPD/LGPD: checklist documental preparada, sem comprovação de aviso de privacidade, bases legais, retenção, consentimento, direitos e transferências em todos os fluxos reais.
- Prémios/sorteios e obrigações fiscais exigem validação jurídica local antes de publicação.

## Decisão
Manter Tarefa 1 aberta até identificação dos módulos restantes, testes e revisão jurídica. Não iniciar tarefa 2 nem tocar produção.
