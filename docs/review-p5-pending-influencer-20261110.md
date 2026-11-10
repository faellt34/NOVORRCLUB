# P5 Portugal — parceiro apto / influenciador pendente (revisão 2026-11-10)

## Evidência verificada
- `backend/pt_split.py::recipients_ready` exige ambos os beneficiários aptos; `settle_new_p5_payment` exige ambos os destinos e transfere sequencialmente.
- O cenário RR-BBB7 já tem transferência real **manual** de EUR 0,80 para Robson: `tr_1Ua8MGCZnwrqCuCtNWIpG43j`. **Nunca reprocessar.** Comissão Lucas EUR 0,05 apenas pendente.
- A comparação `main...release/rrclub-20261109-predeploy` mostrou 327 commits à frente e 39 atrás.

## Contrato proposto (não implementado)
1. Checkout novo: validar vínculo e capacidade do parceiro independentemente do influenciador; persistir um snapshot imutável de ambas as parcelas e dos estados; impedir pagamento caso o valor ou beneficiário do parceiro não esteja verificado.
2. Após webhook autenticado e pagamento confirmado: conciliar transferências existentes no Stripe por referência, destino e valor **antes** de qualquer criação. Não inferir inexistência de transferência apenas por falta de metadados ou ausência no grupo.
3. Transferir somente a parcela do parceiro apto; registrar comissão do influenciador em ledger pendente, sem criar transferência e sem redistribuir os EUR 0,05 à plataforma.
4. Reprocessar comissão pendente apenas após elegibilidade verificada, aprovação explícita e conciliação, com chave de idempotência por venda/beneficiário; preservar trilho de auditoria e travar estados incertos para revisão manual.
5. Evitar duas execuções simultâneas com transição atómica no banco; nunca usar somente um timestamp como exclusão mútua. Proibir pagamentos retroativos automáticos, incluindo RR-BBB7.

## Testes exigidos antes de qualquer merge
- Parceiro pronto + influenciador pendente: parcela do parceiro elegível, comissão permanece pendente; nenhum envio ao influenciador.
- Ambos prontos: duas parcelas corretas, sem duplicação.
- Parceiro não pronto: nenhuma transferência.
- Webhook duplicado, concorrente, atrasado, erro de rede, transferência Stripe existente sem metadados, tentativa incerta e retenção de idempotência expirada: nenhum repasse duplicado.
- Reembolso/disputa, divergência de montante/moeda/destino, associação Connect alterada: bloqueio e reconciliação.
- RR-BBB7: registo histórico manual apenas para conciliação; **zero** novos movimentos.
- Suite isolada com Stripe e MongoDB simulados, sem chaves live.

## Estado
Documento de revisão apenas. Nenhuma alteração funcional, cobrança, transferência, segredo ou deploy. A prontidão de 72% permanece estimativa histórica, não verificação end-to-end.
