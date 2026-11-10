# RRClub V1 — ambiente de pré-visualização isolado

Esta branch foi criada exclusivamente para construir uma cópia de homologação da RRClub, sem alterar a produção.

## Estado inicial (2026-11-10)
- Base provisória: `mainNNOVO`. **Não confirmado** que corresponda ao commit atualmente publicado em rrclub.online.
- Branches de referência: `rrclub-mobile-20261029`, `fix/mobile3-safe-20261029`.
- URL proposta: `preview.rrclub.online` (ainda não configurada).
- Nenhum deploy, alteração DNS, migração de dados ou transação financeira foi realizado.

## Requisitos da V1
1. Replicar primeiro as páginas e funcionalidades da versão efetivamente publicada: landing, login, registo, cupom público, parceiro, influenciador e administrador.
2. Acrescentar um centro de operações de homologação, com eventos correlacionados entre influenciador, parceiro, seguidor e administrador.
3. Separar base de dados, sessões, tokens, webhooks e credenciais de produção. Não copiar dados pessoais ou financeiros de utilizadores reais.
4. Utilizar pagamentos simulados/Stripe Test Mode; nunca efetuar cobranças reais no protótipo.
5. Priorizar a experiência mobile, sem remover funcionalidades existentes e sem integrar branches divergentes sem revisão.
6. Comparar o commit efetivamente publicado com a base desta branch antes de alegar fidelidade à produção.
7. Não modificar DNS nem domínio oficial antes de existir serviço de prévia publicado e verificado.
8. Confirmar a regra de distribuição financeira antes de implementar cálculos de split; há decisões anteriores divergentes.

## Critérios de aceitação
- Navegação mobile em ecrãs pequenos e grandes.
- Percurso demonstrável campanha → QR → validação → checkout simulado → atualização dos quatro perfis.
- Logs de eventos, estados e erros visíveis no centro de operações.
- Isolamento comprovado de produção.
- Build e testes reproduzíveis.
- Aprovação do utilizador antes de promover mudanças ao site oficial.
