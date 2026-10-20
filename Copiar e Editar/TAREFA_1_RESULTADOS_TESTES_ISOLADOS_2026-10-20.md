# Tarefa 1 — execução inicial de testes isolados P5 (20/10/2026)

Escopo: cópias locais dos módulos backend/p5_quote.py e backend/p5_cash_rules.py, obtidos da branch BRANCH-copia-editar-a-vontade. Execução local com Python unittest, sem acesso a Stripe, base de dados ou produção.

**Resultado: 11 testes executados, 11 passaram, 0 falhas.**

Casos: cotação 100 EUR com desconto 5% resulta 95 EUR; arredondamento de 10,01 EUR; rejeição de país inválido, NaN e valor negativo; dinheiro pendente com comissão de 5% passada explicitamente como parâmetro de teste (não prova comissão comercial aprovada); confirmação de dinheiro autorizada; rejeição de dinheiro não recebido, parceiro não correspondente, segunda confirmação e comissão maior que valor devido.

Limitações: os testes validam apenas lógica isolada e reproduzida fielmente dos dois módulos, não rotas HTTP, concorrência, persistência, QR, cupão único, checkout, Stripe, webhooks, segurança RGPD/LGPD ou conformidade jurídica. O desconto de 5% é um parâmetro do teste; falta garantir que a origem seja a campanha aprovada no servidor.

Tarefa 1 permanece aberta. Não houve alteração de produção nem de pagamentos reais.
