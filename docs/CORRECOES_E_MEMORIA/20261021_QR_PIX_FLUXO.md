# QR P5 e associação Pix — 21/10/2026

## Problemas confirmados
- PublicCoupon desativava Guardar QR com P5 ativo, sem oferecer download do QR de sessão.
- O download antigo podia selecionar o SVG do ícone Download e anunciava sucesso antes da conversão.
- O verificador Pix exigia partner_id também para influenciadores.
- Falhas de configuração/consulta da Stripe eram apresentadas como onboarding pendente do destinatário.

## Correções
- Botão próprio no QR P5; exportação PNG do SVG efetivamente apresentado, partilha de ficheiro quando suportada e fallback para download.
- QR P5 contém scan_ref, nunca o session_token privado.
- Influenciador aceita influencer_id e o partner_id legado apenas quando coincide exatamente com o seu ID. Conta diferente ou vínculo ausente continua bloqueado.
- Novo onboarding de influenciador passa a usar influencer_id.
- Razão financeira persistida e mostrada sem afirmar que toda falha é KYC.
- Inclui correção visual da PR #13.
- Diagnóstico local de leitura mostra campanha, IDs internos, contas associadas, vínculos e verificações da plataforma. Não cria/reassocia contas, não altera metadata e não movimenta dinheiro.

## Validação
- 73 testes backend e 9 subtestes aprovados (Pix e políticas P5).
- 6 testes frontend aprovados (sessão P5 e exportação QR).
- Build produção aprovado com avisos existentes de source maps do scanner e dependência de hook de PublicCoupon.

## Limite operacional
Não há acesso autenticado à base de produção neste ambiente. As contas Stripe consultadas estavam aptas, mas sem metadata de vínculo. É necessário confirmar os IDs reais antes de qualquer reconciliação; não associar por nome ou email. O instalador aplica merge seletivo com backup e emite diagnóstico da campanha SHEYSO-7182.
