# Pix e parceiros — verificação operacional de 17/10/2026

Publicação deste diagnóstico autorizada explicitamente pelo proprietário na conversa.
Registro sem credenciais, documentos, dados bancários ou identificação individual de parceiros.

## Estado verificado
- Consultas realizadas pelo plugin Stripe, somente GET; nenhuma transferência, cobrança ou alteração bancária.
- A conexão disponibiliza RRCLUB em produção e teste; RRCLUBRASIL somente em teste. Isso não prova inexistência ou desativação da produção brasileira.
- Na RRCLUB de produção há uma configuração geral com Pix disponível e ligado, junto a outros meios. Não é a configuração exclusiva de Pix exigida por backend/routes_pix.py.
- Os webhooks consultados nessa plataforma são gerais; não foi encontrado /api/stripe/pix/webhook.
- Na RRCLUBRASIL de teste, a configuração padrão tem Pix indisponível/desligado e não há endpoints de webhook registrados.
- As contas conectadas brasileiras consultadas são genéricas de teste, sem metadata.partner_id, com transferências e depósitos desabilitados. Não demonstram ligação aos parceiros do site.
- Foram encontrados cadastros de parceiros em Portugal/EUR com requisitos pendentes e duplicidade de cadastro. A conciliação nominal deve permanecer privada.
- O site abriu na tela de login; ainda não foi possível consultar a lista administrativa nem os campos efetivos do banco publicado.

## Conciliação necessária
1. Consultar parceiros e influenciadores no banco publicado em sessão administrativa.
2. Comparar ID interno, metadata.partner_id e ID Stripe salvo. Para Pix usar pix_stripe_account_id e preservar as contas de Portugal.
3. Confirmar identidade/titularidade antes de associar. Não associar por email/nome isolado ou usar contas genéricas de teste.
4. Conferir BR/BRL, capabilities.transfers=active, payouts_enabled=true e agenda diária conforme o fluxo existente. Banco cadastrado não comprova habilitação.
5. Em duplicidades, verificar qual ID o site utiliza; não excluir, substituir ou criar duplicatas automaticamente.
6. Reutilizar onboarding e status existentes em /api/partner/pix/connect/onboard e /api/partner/pix/connect/status. Os titulares devem concluir as exigências no Stripe.
7. Conferir também o influenciador da campanha; os destinatários devem ser distintos.

## Configuração e conclusão
Seguir docs/PIX_BRASIL_CONFIGURACAO_EMERGENT.md; configurar segredos exclusivamente no servidor, na conta e modo corretos.
Criar/reutilizar configuração exclusiva para Pix, sem alterar configurações gerais de outros pagamentos.
Registrar webhook dedicado com os eventos de backend/payments/pix/checks.py; guardar assinatura apenas nos segredos do servidor.
Consultar /api/admin/pix/readiness e /api/admin/pix/provider-readiness como administrador.
Manter PIX_ENABLED=false em produção até concluir requisitos e homologação.
Preservar original R$100 → cobrança R$95 → parceiro R$80, influenciador R$5, plataforma R$10 brutos; taxas Stripe da plataforma.
Não fazer transferências manuais sobre vendas já divididas automaticamente.
Entregar conciliação privada, revisão carregada no servidor, diagnósticos, homologação e pendências.
Este documento não configura o servidor nem comprova funcionamento ponta a ponta. Nenhum código foi alterado por este registro.

## Atualização autorizada — produção brasileira, 17/10/2026, 20:26 Lisboa

O proprietário autorizou explicitamente a publicação destes novos resultados
na conversa, após ser informado de que o repositório é público.
Esta seção substitui a limitação de acesso anterior. RRCLUBRASIL de produção
agora está acessível em leitura; as observações anteriores sobre teste são históricas.

Consultas GET completas (has_more=false):
- Pix disponível e ligado nas duas configurações da produção brasileira.
- Ambas também oferecem outros meios; nenhuma satisfaz Pix exclusivo exigido pelo código.
- Nenhum webhook cadastrado nesta conta de produção.
- Duas contas conectadas: uma com transferências ativas e depósitos habilitados;
  outra com transferências inativas, depósitos desabilitados e cadastro pendente.
- Ambas sem metadata.partner_id. A associação aos parceiros e influenciadores
  do site precisa ser comprovada no painel administrativo/banco publicado.
- Um cadastro na lista Customers; cadastro de cliente não comprova habilitação
  como destinatário de repasses.

Falta preparar configuração exclusiva de Pix e webhook dedicado
/api/stripe/pix/webhook, gravar os segredos diretamente no servidor, conciliar
destinatários e executar os diagnósticos administrativos e homologação.
A conexão atual é de leitura; mudanças exigem permissões específicas de escrita.
Não criar destinatários nem associar contas por suposição.
Não habilitar cobranças antes da conclusão dos requisitos.
Nenhuma configuração Stripe foi alterada e nenhuma transferência foi executada.
