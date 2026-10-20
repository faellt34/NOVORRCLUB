# Tarefa 1 — P5: regras e privacidade
Destino: NOVORRCLUB / BRANCH-copia-editar-a-vontade / Copiar e Editar. Não alterar produção.

## Cinco regras aprovadas
1. Parceiro confirma valor bruto (exemplo 100 EUR), desconto de campanha de 5% produz 95 EUR; atualizar automaticamente apenas a sessão individual do seguidor, valor bloqueado para edição, aproveitando checkout existente.
2. Sem telemóvel, exigir código individual de uso único associado ao cupão; apenas dizer nome da campanha ou influenciador não basta. Auditar parceiro, data, valor e validação. Definir recuperação segura sem código.
3. Campanhas com prémio: minicadastro mínimo vinculado ao cupão para contactar vencedor. Informar o tratamento necessário à participação; consentimento de marketing separado, facultativo e não pré-selecionado.
4. Testar no clone e não duplicar funcionalidades; produção e original intocados até aprovação.
5. Dinheiro e Stripe preservam atribuição de campanha e influenciador, mas reconciliação e liquidação separadas; pagamento em dinheiro não liquida automaticamente comissões, evitar duplicações.

## RGPD (Portugal/UE) e LGPD (Brasil) — critérios de conformidade
- Inventariar dados, finalidades, responsáveis e operadores, bases legais específicas e prazos de retenção.
- Aviso de privacidade antes da recolha: identificação do responsável, contacto, finalidades, bases legais, destinatários, conservação, direitos, reclamações e transferências internacionais.
- Consentimento de marketing livre, específico, informado, revogável, documentado e independente da participação.
- Minimização, controlo de acessos, medidas de segurança, auditoria, eliminação e atendimento dos direitos dos titulares.
- Avaliar transferências entre Portugal e Brasil, prestadores de pagamento, dados de menores e necessidade de avaliação de impacto.
- Rever regulamentos, autorizações aplicáveis a sorteios/prémios e impostos nos países envolvidos antes de lançamento.
- Revisão jurídica local é necessária; esta checklist não constitui parecer legal nem prova conformidade.

## Verificações técnicas
- Confirmado ficheiro backend/routes_pix.py na branch de cópia, com lógica Stripe/Pix Brasil.
- Caminhos backend/routes_coupons.py e backend/routes_checkout.py não encontrados; não significa que as funcionalidades não existam noutros módulos.
- Não estão validados os fluxos completos QR, cupão, checkout e comissões.

## Aceite
[x] Regras e checklist documentadas no clone real.
[ ] Localizar e rever os módulos reais restantes.
[ ] Verificar implementação e testes de segurança e privacidade.
[ ] Obter revisão jurídica apropriada antes de afirmar conformidade integral.
Estado: tarefa 1 em execução; documentação concluída, validação pendente.


## Atualização de implementação e critérios de aceitação — 20/10/2026
- O desconto de 5% no exemplo de EUR 100 para EUR 90 pertence ao fluxo de campanha P5; não substituir automaticamente os 5% fixos do Pix BR encontrados em backend/routes_pix.py.
- Checkout P5: parceiro valida montante bruto; backend calcula desconto em unidades monetárias inteiras (cêntimos), guarda a origem da validação e associa valor líquido a uma única sessão/cupão, sem permitir edição pelo seguidor.
- Cupão individual: gerar identificador aleatório não previsível; armazenar apenas representação protegida do segredo, estado, validade, campanha e seguidor; resgate atómico de uso único, sem conceder desconto por nome de influenciador.
- Prémios: cadastro mínimo vinculado ao resgate e contacto para prémio, com aviso de privacidade e consentimento publicitário separado. Não tratar registo como prova de pagamento.
- Dinheiro e Stripe: mesmo campaign_id e influencer_id; payment_method e settlement_status distintos; comissão só após reconciliação e nunca duplicada para o mesmo resgate.
- Não foi demonstrado que estes critérios estejam implementados em todos os módulos; não ativar em produção sem testes de concorrência, isolamento de sessão, reembolsos, permissões e revisão jurídica.

## Retificação aprovada pelo responsável — 20/10/2026
- Desconto P5 confirmado: **5%**, não 10%, para campanhas P5 aplicáveis. Exemplo: 100 EUR brutos -> 5 EUR de desconto -> 95 EUR a pagar.
- Preservar separadamente a percentagem de comissão do influenciador e a política de liquidação; não inferir comissão a partir do desconto.
- Esta correção substitui referências documentais anteriores a 10%; não altera por si só a configuração de campanhas existentes ou pagamentos em produção.
- Verificar em testes de clone que QR, cupão, checkout e pagamentos obtêm o desconto da campanha aprovada no servidor e não de entrada do cliente.
