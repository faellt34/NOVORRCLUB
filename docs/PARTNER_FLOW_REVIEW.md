# Revisão para aprovação — parceiros, IBAN, cupões e Connect

Data: 17/10/2026. Repositório: faellt34/NOVORRCLUB.
Base verificada no GitHub: `codex/pix-current-integration`, commit `8e90ad34377c9a99a291b581e65d62ff623c74e2`.
Branch de preparação: `codex/partner-flow-repairs`.

## Resultado da análise

| Problema | Evidência no código da base | Preparação entregue |
| --- | --- | --- |
| IBAN devolve 500 | `set_iban` acedia diretamente a `user['partner_id']` | Validação da associação, existência/proprietário do estabelecimento, atualização condicionada e verificação de sucesso. Acrescentada validação de checksum do IBAN. |
| Conta criada sem ligação ao negócio | Gestão cria utilizadores e parceiros separadamente; não havia uma ação para os associar | Ação explícita `Gestão → Parceiros → Associar conta`, exclusiva de administrador, com escolha por conta identificada, proteção contra conflitos e sem mudanças de IBAN, Stripe, moeda ou aprovação. |
| Cupão parece inexistente numa conta órfã | A pesquisa usava `partner_id=None` | Dashboard, pré-visualização e validação exigem associação válida. O painel passa a mostrar o problema de acesso em vez de ficar eternamente a carregar. |
| Repetição de venda podia expor outro parceiro | A consulta por idempotency_key devolvia um registo sem conferir parceiro/cupão/valor | Validação dos três campos, inclusive quando existe colisão de inserção. Também rejeita valores não finitos. |
| Falha Stripe modifica diagnóstico | Falha da consulta era convertida em estado e gravada, incluindo payouts=False | Em falha, devolve estado desconhecido e preserva flags. Só uma consulta bem-sucedida atualiza capacidades e data da sincronização. Metadata contraditória impede atualização. |
| Risco de duplicar onboarding e retorno externo | Criação sem chave idempotente e URL de retorno fornecida pelo browser | Reutiliza conta existente, chave estável de criação por parceiro, verificação da associação, retorno limitado às origens configuradas e timeout do SDK. Não foram alterados os destinos financeiros. |
| Maraca aparece de formas diferentes | Diagnóstico usava campos locais e não distinguia cache de consulta atual | Diagnóstico identifica fonte local, moeda, conta, flags e última consulta confirmada. Não afirma que isto comprova o estado real no Stripe. |
| Fonte e demora em vídeo | A base já inclui duas fontes, fallback, cache atómica e fila com resposta 202 | Mecanismos preservados; testes acrescentados para fontes incluídas e fonte ausente. Testes existentes confirmam processamento, isolamento de campanha e falhas sem cache parcial. Não se reimplementou o gerador. |

A origem exata das contas órfãs em produção não está comprovada. A criação administrativa separada é um caminho que produz essa situação; registo direto já cria as duas ligações. Podem existir também registos legados ou alterados. Nenhuma associação foi deduzida por email, nome ou valor financeiro.

## Ficheiros

- `backend/partner_access.py`: regras comuns de acesso e normalização/checksum do IBAN.
- `backend/routes_payments.py`: IBAN e fluxo Connect.
- `backend/routes_admin.py`: associação explícita; impede alterar os campos de ligação pelo CRUD genérico.
- `backend/routes_data.py`: dashboard, pré-visualização e validação de cupão.
- `backend/diretor_tools.py`: proveniência e detalhe do diagnóstico local do Connect.
- `frontend/src/pages/AdminManage.jsx`: seleção e confirmação da conta do parceiro.
- `frontend/src/pages/PartnerDashboard.jsx`: erro de acesso visível e estado desconhecido de Connect.
- `frontend/src/components/PartnerOnboarding.jsx`: não incentivar ativação quando o estado não foi verificado.
- Testes novos e regressões em `backend/tests/test_partner_iban_association.py`, `test_partner_flow_repairs.py` e `test_story_jobs.py`.

## Verificações concluídas

- 40 testes backend locais aprovados; MongoDB em memória, Stripe simulado, sem cobranças nem chamadas à conta real.
- 19 testes frontend aprovados.
- Build de produção aprovado, com avisos de source maps da dependência de QR já existentes.
- Navegador: associação enviada com os identificadores selecionados; acesso não administrativo bloqueado; erro claro para conta órfã; estado Stripe desconhecido sem induzir ativação; verificação mobile a 390 px sem overflow.
- Geração real local de MP4 de teste com 2 frames, ffmpeg e fontes incluídas: ficheiro válido com 62.025 bytes. Este teste confirma o encoder local, não mede o desempenho do vídeo completo na infraestrutura de produção.

Comando backend: `PYTHONPATH=backend python -m pytest backend/tests/test_partner_iban_association.py backend/tests/test_partner_flow_repairs.py backend/tests/test_story_jobs.py backend/tests/test_payment_policy.py -q`.
Dependências de testes: pytest, pytest-xdist, mongomock-motor, httpx e dependências normais do backend. As opções de pytest.ini foram preservadas.

## O que esta aprovação não deve assumir

1. Não se consultou nem alterou a base de produção. Ainda faltam o email/ID da conta do amigo, o estabelecimento correto e a confirmação administrativa para aplicar a associação depois da publicação.
2. Não se consultou a conta Stripe real do Maraca. Estado CONNECTED não comprova, por si só, todas as capacidades ativas. É necessário consultar a conta já existente, conferir identificadores e data e resolver qualquer divergência. Nenhuma conta real foi criada ou redirecionada.
3. A versão efetivamente publicada no Emergent não foi comparada byte a byte com esta base. Os erros de fonte/latência podem corresponder a uma versão antiga, mas isso é uma hipótese. O container final deve conter fontes/ffmpeg, e o cliente deve usar a resposta 202 com polling, já presentes nesta base.
4. As alterações mais amplas de sessão, confirmação assíncrona de pagamentos e limites de IA permanecem preservadas na worktree `codex/audit-remediation`, ainda fora deste pacote. Não se deve considerar toda a auditoria encerrada nem fazer uma publicação geral sem a revisão dessas pendências.
5. Países/cidades/bairros e configuração do email do domínio continuam assuntos separados. Não foi ativado Google, Pix nem alterado o visual da cópia CONEKTA.
6. Em erro de rede entre as duas gravações da associação, pode haver estado parcial a rever. A operação é idempotente para a mesma conta/estabelecimento e os acessos conflitantes são bloqueados; não tenta reassociar outro proprietário automaticamente.

## Sequência para aplicar após aprovação

1. Confirmar qual branch/commit o Emergent tem realmente carregado e preservar mudanças que só existam nesse ambiente. Não substituir cegamente por esta base.
2. Rever o diff desta branch contra `8e90ad3` e integrar as alterações na versão correta.
3. Confirmar `FRONTEND_URL`, `PAYMENT_ALLOWED_ORIGINS`, dependências e fontes/ffmpeg no ambiente final. Manter Portugal/EUR e `PIX_ENABLED=false`.
4. Validar em preview os percursos e a preservação dos dados. Publicar só depois de autorização e de resolver as pendências de release identificadas acima.
5. Com os registos corretos confirmados, administrador usa Associar conta para o amigo. Depois o parceiro atualiza a página, verifica IBAN, capacidades Stripe e campanha LUCAS2027 correspondente. Não se deve validar uma venda ou fazer cobrança apenas para verificar a interface.

## Custos e limites

A documentação oficial do Emergent informa que Re-publish da mesma app não tem cobrança adicional por republicação, mas o alojamento mantém a tarifa mensal em créditos. Usar o agente para carregar/rever código pode consumir créditos. Um commit no GitHub não atualiza automaticamente o workspace do Emergent, e republicar código não repara, por si só, os dados da base.
Fontes consultadas: https://help.emergent.sh/glossary-of-emergent-terms e https://help.emergent.sh/deploying-web.

Estado da entrega: código e testes preparados para revisão. Sem deploy, alteração de dados reais, cobrança, teste pago ou aumento de orçamento.
