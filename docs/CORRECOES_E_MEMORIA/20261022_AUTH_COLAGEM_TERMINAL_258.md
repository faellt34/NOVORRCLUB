# RRClub P5 — correção de colagem acidental em `routes_auth.py` (22/10/2026)

## Problema observado no Emergent

- Screenshot da sessão: VS Code `/app/backend/routes_auth.py`, comando `curl ... rrclub_p5_ativar_sem_apagar_20261021.py ...` colado na **linha 258** do ficheiro Python.
- Terminal: `rrclub_auth_prefix_guard.py --repair` interrompido com `PARADO: Sintaxe inválida, mas não corresponde ao texto JSON observado. Parar.`.
- O reparador anterior tratava **somente texto JSON no cabeçalho**; não abrangia comandos de shell ao fim do ficheiro.
- Como o comando encadeava `&&`, o instalador P5 **não chegou a executar** nessa tentativa. Não considerar P5 ativo nem deploy efetuado.

## Resolução

- Script `scripts/rrclub_auth_terminal_paste_guard_20261022.py`.
- Só remove linhas completas contendo um comando de Terminal da RRClub com URL GitHub reconhecível.
- Exige AST válido **depois** da remoção e mantém as funções `login`, `logout`, `register`, `me` e `google_link`, imports e router.
- Se a origem tiver erros adicionais, NÃO tenta restaurar o ficheiro do GitHub sobre alterações locais.
- Faz backup para `/tmp/rrclub_auth_backup_20261022_*/routes_auth.py`.
- Não lê segredos, não modifica Stripe/Mongo/financeiro, não faz deploy, e não executa comandos colados no ficheiro.
- Testes: `scripts/rrclub_auth_terminal_paste_guard_test.py`.
- CI **aprovado**: https://github.com/faellt34/NOVORRCLUB/actions/runs/39835016380

## Próxima execução

1. Executar apenas no **Terminal** do VS Code, nunca dentro de `.py`.
2. Reparar `routes_auth.py` usando o guard, e apenas se passar continuar com `scripts/rrclub_p5_ativar_sem_apagar_20261021.py`.
3. Se o guard parar por funções em falta, investigar o estado real do ficheiro e cópias de segurança; não substituir com versão GitHub às cegas.
4. Com P5 QR EUR/BRL ativo, confirmar `/api/public/p5/config`, prévia de cupão e aprovação pelo parceiro; pagamentos reais apenas com conta Stripe apta e reconciliação.
5. **Não confundir** `awaiting_connect` (estado normal de KYC) com erro operacional.
6. O split Portugal automático depende de `PT_SPLIT_*` e prova de aptidão dos beneficiários; nunca ativá-lo automaticamente só para cumprir calendário.

## Estado

**Código reparador criado e validado no GitHub; execução no workspace Emergent ainda não comprovada.**
