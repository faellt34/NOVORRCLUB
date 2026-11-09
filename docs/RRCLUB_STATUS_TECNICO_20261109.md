# RRClub — diagnóstico técnico e pontuação em 09/11/2026

**Pontuação estimada de prontidão técnica para publicação: 72/100.**

Esta é uma **avaliação ponderada de engenharia**, NÃO uma medição automática de uptime, tráfego, qualidade comercial, cobertura total nem certificação financeira. **Não inclui documentos, KYC, validações pessoais, contas de utilizadores pendentes ou decisões administrativas individuais.** Não tratar o resultado como percentagem de transações reais concluídas.

## Evidências verificadas em GitHub

Branch: `release/rrclub-20261109-predeploy`.
Testes offline de Python/financeiro/perfis: **105 aprovados + 20 subtestes**; rota de CI:
`https://github.com/faellt34/NOVORRCLUB/actions/runs/42555124769`.
React/Jest: **48 testes aprovados em 11 suítes**:
`https://github.com/faellt34/NOVORRCLUB/actions/runs/42555214677`.
Build React e verificações estáticas: ver workflow
`https://github.com/faellt34/NOVORRCLUB/actions/workflows/rrclub-release-20261109.yml`.

Todos esses testes são executados **sem chaves de produção, cobranças ou repasses reais**. Dependências de testes são instaladas no runner GitHub, não no servidor RRClub.

## Pontuação em 100 pontos — excluir só bloqueios dos utilizadores

| Grupo | Pontos possíveis | Pontos reconhecidos | Motivo |
|---|---:|---:|---|
| Código base: contas, campanhas, QR, P5 | 20 | 18 | Código presente; integração total no servidor não verificada |
| Autenticação, autorização e isolamento | 15 | 12 | Correção preparada, mas uma credencial antiga esteve exposta no histórico Git; rotação e revisão na produção pendentes |
| Interface e experiência | 15 | 13 | 48 testes React aprovados; aparência/dispositivos reais não avaliados |
| Qualidade e regressões automatizadas | 20 | 18 | 105 testes Python + 20 subtestes, 48 testes React; não são end-to-end reais |
| Publicação, observabilidade e integração real | 15 | 7 | Artefacto e plano de deploy preparados; commit do workspace Emergent desconhecido |
| Comprovação de liquidação financeira em produção | 10 | 0 | Sem evidência auditável conjunta de pagamento real + webhook + repasses aos dois destinatários |
| Recuperação e proteção de versões | 5 | 4 | Backups GitHub confirmados; snapshot do workspace/banco ainda não confirmado |
| **Total** | **100** | **72** | **Pronto para reconciliação e ensaio controlado, NÃO autorizado como produção integral** |

## Pendências que pertencem à PLATAFORMA (e contam)

1. **Emergent:** identificar HEAD e alterações locais do workspace efetivamente publicado, comparar com a branch de release e fazer integração seletiva sem reset/pull global. Backup privado do workspace e dados MongoDB.
2. **Storage real:** testar gravação e entrega de avatar/capa utilizando o serviço objstore existente, autorização por papel, URL público e persistência entre sessões. O módulo passou testes com armazenamento simulado.
3. **P5 financeiro:** confirmar em Stripe BR e PT um pagamento real *já existente*, webhook assinado processado, razão de liquidação, transferência idempotente para parceiro e influenciador e evidência de payout quando aplicável. **Não criar novas cobranças para a auditoria.**
4. **Regra económica:** o código usa desconto 5% do bruto, parceiro 80% do bruto, influenciador 5% do bruto e plataforma 10% do bruto, distribuindo 95% pagos. Isto pode diferir da referência verbal 85/5/10 sobre o montante pago; a base de cálculo deve ser explicitamente conciliada antes de operações financeiras reais. **Não mudar automaticamente a regra em vigor.**
5. **Credenciais históricas:** retiradas do ficheiro de teste na branch de release, com opt-in obrigatório de ambiente isolado. Como uma credencial já foi incluída no histórico Git, a correção do ficheiro não a elimina do histórico: verificar e rodar qualquer senha ainda válida pelo canal oficial, sem publicar segredos. Não alterar o login de produção automaticamente.
6. **Publicação:** confirmação manual de aparência via fotos/vídeos, autenticação, cupão, QR, logs e rollback para artefacto efetivamente anterior da Emergent.

## Exclusões de pontuação (não são bloqueios de programação)

- Documentação de identidade/KYC de influenciadores/parceiros, IBAN ou cadastro individual pendente.
- Contas Connect de utilizadores não aprovadas por motivos pessoais.
- Atividade, preferência de campanha ou envio de fotografias de cada utilizador.

As exclusões acima **não autorizam** cobrar de contas pendentes nem dispensam verificações de segurança financeira das contas utilizadas.

## Decisão de entrega

**Preparação do GitHub e testes offline: aprovado.**
**Disponibilidade do fluxo financeiro real e compatibilidade exata com a Emergent: não confirmadas.**
**Deploy em produção: não executado nem autorizado automaticamente por este relatório.**
