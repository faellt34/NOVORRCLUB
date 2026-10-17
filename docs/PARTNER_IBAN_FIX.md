# Correção isolada da associação no IBAN

Base: `8e90ad3`, branch `codex/pix-current-integration`. Branch da correção: `codex/fix-partner-iban-association`.

`POST /api/partner/iban` deixa de aceder diretamente a um partner_id ausente. Retorna 400 quando falta a ligação, 409 quando o estabelecimento não existe ou muda durante o pedido, e 403 quando o estabelecimento declara outro proprietário. O caso legado sem user_id continua a exigir o partner_id explícito na conta autenticada. Não há pesquisa nem associação automática pelo email.

A atualização condiciona o proprietário lido e verifica matched_count, evitando declarar sucesso se nenhum registo foi atualizado. O formato de validação do IBAN existente foi preservado. Nenhuma conta Stripe, destino de pagamento, configuração de Portugal ou flag Pix foi alterada. Não inclui o visual CONEKTA nem as correções mais amplas ainda em trabalho.

## Verificação local

7 testes passaram com MongoDB em memória (`mongomock-motor`), sem chamadas Stripe, cobranças ou dados reais:

`PYTHONPATH=backend python -m pytest backend/tests/test_partner_iban_association.py -q`

Dependências de teste: pytest, pytest-xdist, mongomock-motor, além das dependências do backend. A suite preserva as opções do backend/pytest.ini.

## Limites e publicação

Este patch evita o erro 500. Não repara automaticamente as contas órfãs, não ativa recebimentos Stripe e não resolve vídeos ou outros problemas da auditoria.

Antes de publicar, comparar a versão efetivamente carregada no Emergent com a base deste patch e integrar os ficheiros sem sobrescrever alterações mais recentes. Carregar do GitHub não significa que o ambiente Emergent já sincronizou. Re-publish atualiza código, mas não faz a associação utilizador-estabelecimento na base de produção; essa reparação exige identificar os registos corretos. Não foi feito deploy nesta entrega.
