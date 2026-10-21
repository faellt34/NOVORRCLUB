# Correção do estado Connect — 21/10/2026

PR #13 corrige dois diagnósticos enganosos em Definições: perfil não confirmado era apresentado como erro; parceiros associados eram contados por charges_enabled.

Perfil desconhecido agora é informativo. Contagem de associação usa stripe_account_id em parceiros ativos, sem declarar aptidão financeira. Connect acessível não significa split concluído.

Validação: sintaxe Python e execução isolada do endpoint com perfil desconhecido e 2/5 contas associadas; pontuação exclui itens informativos. Não foram alterados KYC, associações, contas Stripe, cobranças ou transferências.

Estado: correção no GitHub; requer sincronização seletiva de backend/routes_payments.py e frontend/src/components/StripeStatusCard.jsx com o workspace atual do Emergent e publicação. Não substituir modificações locais sem comparação.
