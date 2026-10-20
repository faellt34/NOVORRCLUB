# Tarefa 2 — preparação técnica P5 (clone, sem ativação)

Estado: preparação iniciada; implementação ponta a ponta bloqueada até critérios de saída da Tarefa 1. Branch: BRANCH-copia-editar-a-vontade. Não modificar produção.

## Regra comercial corrigida
- Desconto P5: **5%**. Exemplo: 100,00 EUR -> 95,00 EUR a pagar.
- Comissão do influenciador é uma regra separada; não inferir a sua taxa a partir do desconto.
- Não modificar campanhas existentes nem fluxo Pix BR por esta preparação.

## Inventário confirmado no código
- backend/p5_quote.py: cotação monetária sem cobrar; percentagem recebida por argumento, exigindo validação no servidor da campanha.
- backend/p5_cash_rules.py: cálculo e confirmação de dinheiro; pagamento começa pendente, comissão devida pelo parceiro.
- backend/payments/pt_split.py: liquidação experimental Portugal apenas com chave de teste e opt-in; calcula 5% de desconto, com transferências idempotentes, mas não prova checkout P5 completo.
- backend/routes_pix.py: fluxo brasileiro Pix separado, com desconto de 5%; não o confundir com P5 Portugal.

## Sequência de implementação, sujeita à Tarefa 1
1. Mapear rotas reais e modelos de campanha/cupão/sessão, sem criar funcionalidades duplicadas.
2. Validar QR e cupão único, com segredo não previsível, resgate atómico e registo de auditoria.
3. Integrar cotação P5 5% exclusivamente a partir da campanha aprovada, vinculada a uma sessão individual, sem edição pelo seguidor.
4. Cadastro mínimo de prémios com aviso de privacidade e marketing opcional separado.
5. Unificar atribuição de campanha e influenciador para dinheiro e Stripe, mantendo estados de liquidação separados e evitando dupla comissão.
6. Executar testes isolados de concorrência, replay, permissões, reembolsos, idempotência e privacidade.

## Critérios de bloqueio
Não iniciar implementação com efeitos em pagamentos, não ativar em produção e não declarar Tarefa 2 concluída sem evidência dos testes. Revisão jurídica da Tarefa 1 continua pendente.
