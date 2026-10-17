# Ideias e Memórias — RRClub 2.0

**Situação:** ideias arquivadas, NÃO implementar agora.

## 1. Separar testes da operação real
Manter testes e simulações em ambiente isolado, sem misturar dados fictícios com vendas, clientes, comissões e repasses reais.

## 2. Centro de Operações e histórico financeiro
Criar um painel de saúde da plataforma que informe o estado de Stripe, Pix, parceiros conectados, pagamentos, webhooks e transferências. Adicionar histórico financeiro protegido com identificadores, valores, parceiro, comissão, status, rastreabilidade e prevenção de duplicações.

## Prioridade atual (fora deste backlog)
Prosseguir com a habilitação e validação segura do Pix em BRL, integração Stripe Connect e cadastro/onboarding dos parceiros, sem fazer transferências reais sem validação.

## Decisão de interface
Remover os comandos **RESET ALL** e **LIMPAR** do site e bloquear ações destrutivas correspondentes no backend, sem apagar registros e mantendo as demais funcionalidades. Alterações anteriores informadas: commit `7c49ace86c33`; confirmar deploy antes de afirmar que estão no ar.
