# Apresentação da RRClub para o Trem Fodd — 22/10/2026

## Objetivo
Demonstrar como um comércio local pode converter recomendações de seguidores em visitas identificáveis, aprovar o valor de uma compra e acompanhar campanhas num painel, **sem exigir que Stripe Connect esteja já totalmente habilitada**.

## Demonstração P5 sem pagamentos
1. Apresentar o comércio, a campanha e o cupão com dados autorizados pelo estabelecimento.
2. Abrir página do cupão num telemóvel de teste (seguidor).
3. Exibir QR de sessão P5 (não o QR genérico), com referência temporária.
4. No painel do parceiro, ler o QR e confirmar **o valor original da conta**.
5. Seguidor visualiza desconto e valor final aprovados pelo estabelecimento.
6. Se a Stripe/beneficiários não estiverem habilitados: apresentar **«Recebimentos em ativação»**. Isso demonstra a ligação sem simular uma venda.
7. Mostrar que pagamento, comissão, transferência Connect e depósito bancário são fases distintas.

## Perguntas que o parceiro deve compreender
- **Precisa terminar Stripe já para entrar?** Não para participar da demonstração e configurar o perfil. Para receber dinheiro, sim.
- **O cupão ou a leitura do QR gera comissão automaticamente?** Não. O cumprimento financeiro só se calcula depois de pagamento verificado.
- **Quem determina o valor?** O parceiro confirma o total antes do seguidor ver o checkout P5.
- **E se o cartão/Pix/MB WAY falhar?** A tentativa mantém um estado identificável; não se deve cobrar novamente sem consultar o status.
- **Quem recebe o quê?** A regra-modelo P5 é 5% desconto, 80% parceiro, 5% influenciador e 10% RRClub do valor original, **antes das taxas Stripe**. Não prometer estes repasses como efetuados.
- **É uma venda garantida?** Não. O benefício para o comércio depende de visitas, adesão e volume real; medir e validar.

## Critérios mínimos para uma demonstração profissional
- Abrir a página inicial, login e painel do parceiro.
- Criar ou usar uma campanha P5 de ensaio expressamente autorizada.
- Confirmar estados sem pagamentos reais: QR criado, QR lido, conta aprovada, recebimentos pendentes.
- Sem dados pessoais de clientes ou credenciais expostas.
- Evitar demonstrar transferências como executadas, ou dizer que o split está ativo se não estiver.
- Se o ambiente estiver instável, usar apresentação guiada com capturas reais rotuladas como prévia — nunca mostrar métricas simuladas como financeiras.

## Próxima fase após a apresentação
Validar KYC dos beneficiários, verificar conectividade financeira PT e Pix BR, realizar pequena cobrança real autorizada quando prontos e reconciliar os IDs Stripe reais antes de ativar transferências automáticas.
