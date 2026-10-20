# Tarefa 1 — P5: regras e privacidade
Destino: NOVORRCLUB / BRANCH-copia-editar-a-vontade / Copiar e Editar. Não alterar produção.

## Cinco regras aprovadas
1. Parceiro confirma valor bruto (exemplo 100 EUR), desconto de campanha de 10% produz 90 EUR; atualizar automaticamente apenas a sessão individual do seguidor, valor bloqueado para edição, aproveitando checkout existente.
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
