# RRClub — Diretor IA 2.0 · Implementação isolada (25/10/2026)

**Branch:** `feat/diretor-ia-2-operacional-20261025` sobre `mainNNOVO` (`af2a110`).
**Estado:** código preparado em branch de revisão; **não fez deploy, não alterou P5 nem transacionou dinheiro**.

## Entregue nesta primeira fase

- Rota `GET /api/diretor/estrategia?dias=30`: leitura só de `payment_transactions` associadas ao novo P5, com moeda distinta, rejeição de simulações, reembolsos e disputas. Diferencia pago local, Connect confirmado no registo local e depósito bancário desconhecido. Zero chamadas LLM.
- Novo painel executivo na página existente, separa BRL/EUR, funil P5, parcelas devido ao parceiro/influenciador/RRClub, pendência Connect, 3 decisões e especialistas.
- Sete especialidades organizadas e identificadas; Executivo/Operações/Finanças têm dados determinísticos; Marketing/Frontend/Backend conservam a colaboração IA existente. Pesquisa externa automática **ainda não está implementada** e exige fontes; nenhuma análise inventada.
- `ler_dashboard`, `consultar_financeiro`, consultas por parceiro e `/diretor/metricas` já não somam valores de `redemptions` como receita. Removidas estimativas erradas de 23% IVA, 10% tarifas Stripe e 75% hotel.
- Briefing do Diretor passou a reportar funil por moeda e evitar tratar onboarding Connect de terceiros como pane geral; relatório não afirma que erro antigo foi corrigido sem validação.
- Criar campanha pelo Diretor (após aprovação admin): desconto 5%, comissão 5%, moeda do parceiro e proteção contra mesmo nome/parceiro/influenciador duplicado. Minutas usam regra 80/5/10/5; não são contratos assinados.
- Histórico de conversa filtrado ao administrador que o criou. Subagente utiliza modelo económico existente por defeito.

## Limitações deliberadas

- Os valores vêm do livro local depois de webhook: **não há consulta Stripe ao vivo, conciliação bancária, nem confirmação de tarifas reais**.
- `payment_transactions` limitadas a 20 mil/país/90 dias nesta leitura; avaliar paginação e agregações no crescimento.
- Contagem de fases do funil é observacional e não uma taxa de conversão estritamente atribuída aos mesmos utilizadores.
- Regras de repartição em produção continuam governadas pelos módulos P5 já existentes; nada foi reescrito nesse mecanismo.
- O Diretor não envia pagamentos, não associa destinatários Stripe, não publica campanhas automaticamente.
- Tarefas futuras: validação integrada com base de staging, permissões de pesquisa, ligação às fontes externas e eficácia das recomendações.

## Testes executados no ambiente isolado

`backend/tests/test_diretor_estrategia.py`: 8 testes unitários aprovados (pagamento vs histórico, BRL/EUR, simulação, não pago, disputa/reembolso, transferência Connect, split e integridade de valores). Os ficheiros Python foram analisados sintaticamente. **Ainda não houve teste de API com MongoDB real, teste frontend compilado nem teste funcional em produção**.

## Deploy seguro

Revisar diff da branch, executar CI/staging com ambiente não financeiro, confirmar que o painel da RRClub atual e as rotas P5 continuam intactos; só depois integrar e publicar mediante confirmação do administrador.

## Fase 2 — Copiloto do parceiro (25/10/2026)

- Rota `GET /api/partner/insights-p5`, protegida por `require_role("partner")` e `partner_record`. A identidade do parceiro vem da sessão e nunca de um ID escolhido pelo cliente.
- Apenas pagamentos P5 com status local pós-webhook, moeda certa, snapshots consistentes e sem `is_test`, disputas ou reembolsos entram nas vendas pagas do parceiro.
- Calcula parcela do parceiro, valor efetivamente cobrado pelo checkout, ticket médio e top campanhas com pagamentos, sempre por moeda e sem tarifa inventada.
- Fornece até 3 ações comerciais baseadas em evidências, por exemplo verificar checkout quando há scans sem pagamento no recorte, acompanhar Connect pendente ou aumentar amostra antes de concluir ROI.
- Em `/partner` aparece o novo **Copiloto de crescimento**. Os KPIs antigos de resgates passam para uma seção recolhida por padrão, com aviso de que não foram conciliados e podem incluir dados fictícios. Nenhum registo foi apagado.
- 5 testes unitários da Fase 2 aprovados: isolamento por parceiro, exclusão de outra moeda, testes/reembolsos/legado, percentuais devidos e recomendações sem ROI fabricado.

**Pendente:** teste integral autenticado em staging com utilizador parceiro (incluindo Josicleide/Sheyson apenas após consentimento), compilação React e validação do deploy. A interface atual permanece inalterada em produção.

## Etapa 1 da consolidação — testes seguros (25/10/2026)

- `backend/tests/test_iter27_diretor.py` deixa de conter credenciais fixas e de herdar automaticamente o URL de produção. Os testes externos só são executáveis mediante `RRCLUB_RUN_DIRECTOR_INTEGRATION_TESTS=1`, URL definido em `RRCLUB_DIRECTOR_INTEGRATION_BASE_URL` e host local explícito. Os logins vêm de variáveis `RRCLUB_TEST_ADMIN_*` / `RRCLUB_TEST_PARTNER_*`.
- Removida a limpeza abrangente de campanhas pelo texto `Diretor`. Os testes integrados permanecem opt-in e não devem apontar para a RRClub real; uma base local isolada continua necessária.
- O verificador `_verify` de correções aprovadas deixa de procurar testes na pasta raiz (que não tinha casos) e executa uma lista curta de `unittest` sem rede nem escrita financeira. A suite externa inteira nunca é chamada automaticamente quando se verifica um patch.
- Adicionados 2 testes de regressão da segurança dos testes. **17/17 testes unitários de Diretor e Copiloto aprovados**, sem ligação à Stripe/MongoDB real.
- Credenciais de versões anteriores podem continuar no histórico Git. Se corresponderem a acessos ainda válidos, o titular deve revogá-las ou alterá-las; esta atualização não altera contas nem remove histórico Git.
- **Ainda pendente:** compilação frontend, testes autenticados em staging e validação de rotas e permissões. Nenhum deploy ou movimento financeiro nesta etapa.

## Etapa 2 da consolidação — orçamento e lotes IA (25/10/2026)

- `backend/diretor_orcamento.py` centraliza os limites e seleciona lotes de auditoria sem duplicados. A auditoria deixa de iniciar dezenas de chamadas em paralelo: analisa até **3 ficheiros por confirmação**, com posição do próximo lote e número total no retorno.
- O contador diário passa a reservar chamadas de forma atómica em `llm_quota`, inicializando com o histórico de `llm_usage`. Uma conversa contabiliza **cada** interação com o modelo, e não apenas um pedido HTTP. Isto reduz risco de ultrapassar o limite quando há pedidos simultâneos.
- O ecrã do Diretor avisa do consumo por lote, permite continuar o lote seguinte e identifica que os resultados são parciais. O indicador é agora **Chamadas IA**, porque não representa despesa real em euros.
- Limite de 4.000 caracteres por mensagem e recorte do histórico enviado ao modelo. Corrigido o exemplo de split nos comandos do Diretor para 80% parceiro, 5% influencer, 10% RRClub e 5% desconto sobre bruto, sem transformar o desconto em uma transferência financeira.
- **22/22 testes Python aprovados**, incluindo reservas concorrentes e limites de auditoria. Não foi contactada a Stripe nem usado um modelo LLM pago nestes testes.
- **Ainda pendente:** build React (as dependências de frontend não estão instaladas no ambiente de teste), validação com utilizador admin em staging e conferência de custos reais por modelo. O limite de chamadas não é um limite garantido em euros. Nenhum deploy na RRClub real.

## Etapa 3 — painéis de produção e revisão final (25/10/2026)

- Administração: padrão de visualização `verified_only=true` obtém somente pagamentos P5 locais pós-webhook da moeda atual, sem somar resgates históricos. Modo antigo acessível separadamente com aviso de não verificação.
- Influenciador: padrão `verified_only=true` mostra apenas pagamentos P5 atribuídos ao utilizador autenticado e respetivas parcelas. Sem vínculo de `influencer_id`, devolve 403, nunca mistura as identidades. Eventos WebSocket apenas provocam nova leitura autenticada, sem fabricar receita/contagens.
- Parceiro: copiloto P5 comprovado destacado; valores antigos ficam numa secção histórica recolhida, explicitamente sem conciliação. QR não é prova de pagamento.
- Extrato mensal legado: avisos visíveis; não é declarado comprovativo Stripe ou pagamento financeiro apenas por constar no histórico.
- Cupom público: aberturas do link deixam de ser descritas como pessoas pagas/beneficiadas.
- Ferramentas GitHub do Diretor: por omissão consultam `faellt34/NOVORRCLUB` na branch `mainNNOVO`, que é a branch do projeto, sem confundir com a branch de nome `main`; ambiente pode sobrescrever esses valores.
- Falha de ciclo IA: ao atingir o limite interno de chamadas, devolve um resumo parcial honesto, sem afirmar que concluiu uma análise incompleta.

### Validação local no último ciclo

- 34/34 testes Python passaram (estratégia, parceiros, orçamento IA, segurança dos testes, regras P5 e ativação).
- 47/47 testes React passaram em 11 suites.
- Build React produzido com sucesso na cópia isolada; avisos não bloqueantes de sourcemap do leitor QR e hooks existentes.
- Sintaxe Python da rota de dados, rota do Diretor e estratégia validada por AST.
- Nenhum pagamento real, transferência Connect, webhook, limpeza física da base de dados, ou publicação foi executado durante estes testes.

**Pendente para afirmar operação em produção:** disponibilizar o código no servidor, confirmar uma sessão real autenticada com o Diretor, autorizações corretas, ligação Mongo/LLM e exibição de EUR/BRL, sem produzir cobrança de teste involuntária. Testes unitários não substituem esta validação integrada.
