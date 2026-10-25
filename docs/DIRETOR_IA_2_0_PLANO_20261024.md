# RRClub — Diretor IA 2.0 · Estratégia funcional (24/10/2026)

> **Estado:** plano técnico; não implementado ou publicado. Branch isolada do trabalho P5. Preservar associações parceiro–influencer, Stripe Connect, pagamentos e dados históricos.

## Missão

O Diretor deve funcionar como um **diretor executivo digital**, que transforma fatos verificados em decisões operacionais e comerciais: **o que ocorreu, por que importa, o que fazer, impacto esperado, evidência e se precisa da aprovação do administrador**. Não deve ser apenas mais um chat.

## O que já existe

- `backend/routes_diretor.py`: conversa, modelos selecionáveis, limites de chamadas, ferramentas de dados, subagentes Marketing/Frontend/Backend, fila de ações, aprovação/rejeição e lições aprendidas.
- `backend/diretor_tools.py`: briefing, métricas, funil QR, logs e diagnóstico.
- `frontend/src/pages/Diretor.jsx`: tela `/admin/diretor` com briefing, chat e ações pendentes.
- `backend/routes_ai.py`: outro analista, com uma abordagem parcial de separação de moeda e simulações.

## Correções de lógica prioritárias

1. **Contexto real da RRClub:** não restringir a hotéis. Parceiros são restaurantes, comércio, serviços, hotéis e negócios locais, em Portugal e Brasil. Preferir termos `parceiro` e `influenciador`.
2. **Eliminar números financeiros incorretos:** `consultar_financeiro()` em `routes_diretor.py` tem `hotel_75pct`, `stripe_fees_estimadas_10pct` e `iva_23pct_incluido`. Estes números **não são dados reais de repasses ou impostos** e não podem fundamentar recomendações ou contratos. Rever também `gerar_contrato()` e `criar_campanha()`, que usam percentuais-padrão diferentes do P5 vigente.
3. **Separação forte de dados:** toda análise precisa de `país`, `moeda`, `período`, `is_test`, `status real do pagamento`, `reembolso`, `disputa`, `origem`, `última atualização`. **Nunca somar EUR com BRL** nem misturar simulação com venda paga. O padrão deverá usar dados reais; testes apenas por escolha explícita do CEO.
4. **Estados financeiros honestos:** distinguir `QR aberto`, `QR lido`, `conta aprovada`, `checkout criado`, `pagamento confirmado`, `transferência Connect confirmada` e `depósito bancário confirmado`. Uma etapa não comprova a seguinte.
5. **Pendência individual != falha geral:** cadastro Stripe/Connect incompleto bloqueia **apenas a cobrança/repasso que requer aquele beneficiário**, não o QR, aprovação pelo parceiro, marketing, painel nem funcionamento para outros parceiros. **Não flexibilizar titularidade das contas nem transferir para destinatários não verificados**.
6. **Diagnóstico sem suposições:** logs anteriores a deploy não devem ser automaticamente tratados como «erro resolvido» sem evidências de correção e testes. Fontes e momentos de verificação visíveis.
7. **Histórico e privacidade:** conversas e ações por administrador; permissões, auditoria, retenção e limitação da exposição de dados pessoais/segredos.

## Estrutura dos especialistas

| Especialista | Dados | Entrega prioritária | Limite |
| --- | --- | --- | --- |
| Diretor Geral | Resumo integrado | 3 decisões prioritárias por impacto + evidência | Só recomenda ou encaminha ação para aprovação |
| Operações P5 | QR → scan → aprovação → cobrança → pagamento | Gargalos por campanha/país, sem confundir etapas | Não cria pagamentos como teste |
| Finanças BR | BRL, Stripe Pix, tarifas efetivas, reembolsos, repasses | Conciliado / não comprovado / pendente por transação | Sem transferências automáticas novas |
| Finanças PT | EUR, MB WAY/cartão, Connect, contabilização local | Relatório EUR separado e fluxo comprovado | Não inventa IVA, Stripe fee ou split |
| Marketing & Crescimento | Cliques, QR, conversão, ticket, campanha | Ações comerciais mensuráveis e experimentos pequenos | Não publica campanhas sem aprovação |
| Pesquisa de Mercado | Fontes externas públicas atualizadas | Oportunidades locais e shortlist de parceiros/influencers | Citar fonte e data; não inventar reputação |
| Engenharia & Segurança | Git, logs, APIs, testes | Diagnóstico + patch proposto + risco + testes | Sem deploy/patch financeiro sem aprovação |

## Interface recomendada

Na página existente `/admin/diretor`, manter chat e aprovação; acrescentar:
- **Situação do negócio** por EUR/BRL, data e fonte, com Receita Paga, Comissão Devida, Transferido, Pendente e Confirmado.
- **Funil P5** sem inflar vendas: QR aberto → lido → aprovado → checkout → pago → split.
- **3 alertas acionáveis** com gravidade e link para a origem; contas Stripe incompletas aparecem em «pendências dos utilizadores», não como pane geral.
- **Oportunidades de crescimento**: campanha com cliques mas poucas vendas, parceiro sem atividade, influência local, projeção de resultados baseada em premissas explícitas.
- **Fila de decisões**: visualizar proposta, evidência, efeito, custo, risco; aprovar/rejeitar e histórico; nunca executar movimentação financeira sem autorização específica.
- **Limite de créditos** com chamadas por dia, custo e modo diagnóstico sem LLM.

## Estratégia de baixo custo

1. Primeiro consultar dados estruturados existentes, **sem chamar modelo** quando a resposta é determinística.
2. Se precisar de interpretação, enviar só dados mínimos, agregados e filtrados; um especialista por solicitação, com cache/limite.
3. Consultas externas apenas quando pesquisa expressamente necessária; incluir fontes verificáveis, avaliação e data.
4. Gerar plano e recomendações antes de ações; cada escrita depende de aprovação; guardar lições sem repetições.
5. Evitar duplicar `routes_diretor` e `routes_ai`: partilhar camada de métricas verificada.

## Ordem de implementação após estabilizar o P5

**Fase 1 — Precisão e segurança (prioridade máxima):**
- Corrigir narrativa, remuneração, IVA, taxas e separação EUR/BRL / teste vs real, sem modificar `p5_checkout.py`, `routes_pix.py` ou `pt_split.py`.
- Testes automáticos para não misturar moeda, simulações, reembolsos e status de pagamento.
- Revisar segurança da fila de ações, auditoria e limites de créditos.

**Fase 2 — Diretor operacional:**
- Painel do funil P5 por fase, saúde dos serviços e alertas baseados em fatos; sem confundir pendências Connect individuais com plataforma indisponível.
- Diagnóstico de conversão por campanha e sugestões de ação com impacto esperado.

**Fase 3 — Crescimento e pesquisa:**
- Especialistas de marketing e pesquisa de influenciadores/parceiros; fontes externas e aprovação de campanha.
- Briefing executivo periódico opcional; nenhuma automação de cobrança.

**Critérios de aceitação:** diretor sem números inventados; EUR/BRL separados; 0 ações financeiras sem aprovação; fonte/data de cada alerta; testes para simulações e status; limites de custo; relatórios úteis ao CEO.

**Observação:** o simples fato de existir um endpoint ou uma chave Stripe não comprova pagamento, liquidação, repasse bancário ou rentabilidade. Todas as métricas exigem provas.
