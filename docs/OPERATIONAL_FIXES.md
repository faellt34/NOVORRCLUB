# Revisão das falhas operacionais — 16/10/2026

Branch consolidada: `codex/pix-current-integration`, baseada em `mainNNOVO` (`fb7ae71`), no mesmo pacote do Pix. A branch antiga `codex/pix-payments` foi superada como opção de implantação. Sem deploy, alteração de orçamento ou operação financeira.

## Prioridades corrigidas

| Prioridade | Constatação no código | Alteração |
| --- | --- | --- |
| 1 — sessão | `frontend/src/pages/Messages.jsx` existe nesta revisão. Ele e `AppContext.jsx` consultavam mensagens/notificações periodicamente, sem encerrar a sessão ao receber 401. | Um 401 da sessão atual remove o token e encerra a sessão. O polling para sem token, aborta ao sair da tela, pausa em abas ocultas e agenda a próxima consulta após concluir a anterior. Uma resposta antiga não encerra uma sessão nova. |
| 2 — vídeo | A requisição aguardava renderização e codificação completas. Pedidos simultâneos podiam gerar o mesmo arquivo e ler uma saída incompleta. | Geração limitada a uma tarefa por processo, com fila limitada e deduplicação. Durante a preparação, retorna 202 e o frontend aguarda. A saída só entra no cache quando completa; trava de arquivo protege processos do mesmo servidor. Quadros JPEG e codificação limitada reduzem trabalho e arquivos temporários são removidos. |
| 3 — chat | O prompt dizia parceiro 75% e Stripe 10%, divergindo da regra acordada do Brasil. Somava registros de moedas diferentes. | Prompt corrigido: original 100, cliente paga 95, parceiro 80, influencer 5, plataforma 10 antes das taxas reais. Contexto e conversas separados por moeda; reembolsos não contam como vendas novas. Falhas do provedor mostram mensagem clara, sem expor detalhes técnicos ou aumentar orçamento. |

## Evidência local

- 49 testes Python: Pix, relatórios, cadastro, tarefas de vídeo e tratamento da IA.
- 19 testes frontend: tela Pix, polling e tratamento de 401.
- Build de produção do frontend concluído.
- MP4 real gerado localmente: H.264, 720×1280, 3 segundos; geração medida em aproximadamente 2,05 segundos. Não é uma previsão do tempo de produção.
- Nenhuma chamada paga à IA, cobrança Stripe ou deploy foi usada para essas verificações.

Os testes unitários usam dados simulados. Os antigos testes HTTP de vídeo foram adaptados para aguardar 202, mas não foram executados contra o site publicado.

## O que o relatório recebido não comprova

- Os 5.761 avisos, o IP, o pico de 64 segundos e o estado atual dos estabelecimentos são informações fornecidas pelo relatório. Os logs atuais do ambiente publicado não foram inspecionados nesta revisão.
- A causa do pico específico de vídeo pode incluir CPU, disco, concorrência ou infraestrutura. A correção remove a longa espera HTTP e protege a geração, sem afirmar uma causa única para aquele pedido.
- Connect incompleto depende do titular fornecer os dados exigidos. Não foi contornado nem considerado validado.
- A falta de orçamento do provedor não se resolve apenas com código. Foi melhorado o tratamento da falha; saldo e limites não foram alterados.

## Pix: esclarecimento do relatório

O código já contém dois repasses separados: parceiro e influencer. Não falta criar o repasse dos 5% neste pacote. Pagamento confirmado e repasses concluídos são estados diferentes.

Receber Pix, transferir saldo entre contas Stripe e depositar no banco são etapas distintas. Não prometer ao usuário uma modalidade bancária específica como “TED/DOC”; apresentar recebimento na conta bancária conforme condições da Stripe.

Uma Stripe portuguesa elegível também pode aceitar Pix com liquidação em EUR. A estrutura acordada da RR Club permanece Brasil/BRL separado de Portugal/EUR. Referências: https://docs.stripe.com/payments/pix e https://docs.stripe.com/payouts.

## Um único deploy, quando autorizado

Usar esta branch para frontend e backend juntos: a nova resposta 202 do vídeo exige o frontend correspondente. Manter `PIX_ENABLED=false` até a futura configuração e homologação brasileira. Preservar a configuração de Portugal. A `main` não foi alterada.

Não é necessário pedir aos agentes do site para reimplementar estas correções. Eles só serão necessários para investigar ocorrências que persistam no ambiente publicado ou conferir suas configurações e logs.

## Preservação da versão mais recente do GitHub

A integração conserva sem alterações os arquivos principais do Diretor IA, ferramentas do Diretor, motor de patches, observabilidade, núcleo de autenticação e `routes_payments.py` com Connect v2. As rotas e a página do Diretor permanecem registradas. As fontes de vídeo incluídas em `backend/assets/fonts` permanecem. O WebSocket mantém autenticação por mensagem, sem token na URL. O logout continua enviando o token ao servidor para revogação, enquanto interrompe o polling local imediatamente. O cadastro conserva as regras atuais de senha e limitação de tentativas.

Nenhum arquivo existente em `mainNNOVO` foi removido. Esta comparação identifica a versão mais recente encontrada no GitHub; não comprova qual revisão está publicada no Emergent.
