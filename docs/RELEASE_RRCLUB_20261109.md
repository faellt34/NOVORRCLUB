# RRClub — pacote de pré-publicação controlada (2026-11-09)

**Projeto:** RRClub / R-Conekta. **Repositório:** `faellt34/NOVORRCLUB`.
**Branch de entrega:** `release/rrclub-20261109-predeploy`.
**Origem preservada:** `safe/rrclub-profile-security-version-20261109`.
**Pontos de recuperação GitHub:**
- `backup/rrclub-main-before-changes-20261109` — commit `d75d917f980400eb2f7027813348eb0585fb8ed8`.
- `backup/rrclub-safe-profile-before-deploy-20261109` — commit `ac15b12801f3782f3128206acef097c63e9b01ee`.

> **Estado:** fonte preparada para **inspeção e teste**, NÃO publicada. A versão em execução no workspace Emergent e os dados/segredos da produção **não foram inventariados**. Nenhum pagamento foi iniciado. Um teste de CI aprovado não comprova prontidão Stripe.

## Alterações contidas no pacote

1. `backend/routes_profile.py`: upload de avatar do parceiro/influenciador e capa do parceiro, com autenticação por papel, associação estrita `id/user_id`, restrições de tipo/tamanho e conversão segura para JPEG; endpoints públicos só de leitura para exibir imagens; diagnóstico da versão apenas para admin.
2. `backend/server.py`: monta as rotas do perfil sob `/api` reutilizando os routers existentes.
3. `frontend/src/components/ProfilePhotoDialog.jsx` e `frontend/src/components/layout/Sidebar.jsx`: botões de trocar foto/capa; sem novo dashboard.
4. `backend/routes_data.py` e `frontend/src/pages/PublicCoupon.jsx`: imagem de capa opcional no cupom; páginas antigas funcionam sem capa.
5. `backend/routes_admin.py` e `frontend/src/pages/AdminManage.jsx`: para **novas** palavras-passe e alterações explícitas, exigir 8–128 caracteres com letras e números; remover valor padrão previsível; não alterar hashes já existentes.
6. `backend/p5_checkout.py`: diagnóstico administrativo somente leitura de elegibilidade de beneficiários herdado da branch de 31/10; não autoriza transações por si só.
7. `scripts/rrclub_release_static_guard.py` e workflows GitHub: sintaxe, invariantes de segurança e compilação frontend em isolamento.

Não foram programadas novas operações Stripe nem novas quotas de split neste pacote.

## 1. Proteção obrigatória antes de integrar na Emergent

O relatório anterior `docs/RRCLUB_PT_AUDITORIA_DEPLOY_20261021.md` documenta divergência entre repositório GitHub e workspace Emergent. **PROIBIDO** usar `git reset --hard`, `git clean -fd`, `git checkout -f`, `git pull` diretamente sobre a árvore divergente, copiar projeto inteiro, apagar ficheiros locais ou repor uma base de dados.

Antes de qualquer aplicação ao workspace:
- Registar *sem expor segredos* o projeto/ambiente, branch, commit `HEAD`, `git status --short`, remotes disponíveis, e lista de ficheiros modificados ou não rastreados.
- Produzir backup privado do código **atual do workspace** (incluindo alterações não enviadas ao GitHub). Não enviar `.env`, chaves, segredos, bancos de dados ou identidades pessoais para GitHub.
- Confirmar snapshots/backup do MongoDB e o caminho de restauração com o operador antes de qualquer migração.
- **Comparar** cada ficheiro previsto com a versão local por diff de três vias. Resolver conflitos, preservando rotas, campanhas, autenticação Google, Pix, MB WAY, QR, URLs e funcionalidades do workspace.
- O release não deve fazer migração de coleção, alterar beneficiários Stripe Connect, reinicializar contadores, editar DNS nem alterar flags de pagamento.

## 2. Integração seletiva dos ficheiros do pacote

Rever individualmente (não copiar cegamente):
- Novos: `backend/routes_profile.py`, `frontend/src/components/ProfilePhotoDialog.jsx`.
- Ligação: `backend/server.py`, `frontend/src/components/layout/Sidebar.jsx`.
- Campanhas: `backend/routes_data.py`, `frontend/src/pages/PublicCoupon.jsx`.
- Segurança: `backend/routes_admin.py`, `frontend/src/pages/AdminManage.jsx`.
- Diagnóstico P5: `backend/p5_checkout.py` apenas a rota read-only `/admin/p5/recipient-diagnostic`, se ela ainda não existir; preservar o restante checkout do workspace.
- Rotinas de testes: `scripts/rrclub_release_static_guard.py` e CI. Sem alteração obrigatória ao runtime.

**O P5 deve manter os seus fluxos já funcionais.** Não usar um merge da branch completa para incorporar uma única rota se a árvore Emergent for diferente.

## 3. Diagnóstico de versão (após integração, não antes)

Com a versão aprovada e efetivamente publicada, definir `RRCLUB_RELEASE_SHA` no ambiente a partir **do commit realmente implantado** (não de uma branch assumida). Se não houver variável/commit verificável, `GET /api/admin/system/version` responderá `release_identified=false`.

A rota exige sessão de **admin**. A existência da rota ou o campo `release_identified=true` isoladamente não confirmam que todos os ficheiros do workspace são idênticos ao GitHub: confrontar hash/manifesto do artefacto instalado e o histórico de deploy da Emergent.

## 4. Teste de aceitação com operador, em ambiente isolado

**Sem cobrar, transferir ou ativar gateways.** Confirmar:
- Login anterior, login Google e estados de conta continuam válidos.
- Parceiro e influenciador abrem o mesmo dashboard anterior; podem selecionar JPG/PNG/WebP até 3 MB, guardar avatar, atualizar a sessão e rever foto.
- Parceiro pode selecionar capa comercial horizontal; cupão de campanha mostra a imagem sem ocultar QR, desconto, campanha ou valor.
- Foto de outra conta, arquivo inválido ou >3 MB é recusado. GET de imagem pública devolve JPEG; alterar avatar não altera campanha ou histórico.
- Nova conta administrativa requer senha forte; contas já existentes mantêm o hash anterior.
- Admin consulta a identificação de versão e o diagnóstico P5; não gera checkout.
- Pix BRL / MB WAY EUR / Cartão continuam exibindo **somente** estados efetivamente configurados. Não confundir `configured=true` ou `checkout_ready=true` com liquidação financeira.
- Comparar a aparência de cupão, menu e fotografias com prints/gravações de vídeo. A geração e publicação de vídeos próprios de marketing não faz parte deste pacote.
- Ver logs do backend e navegador durante upload; verificar a dependência `EMERGENT_LLM_KEY` para objstore **sem revelar a chave**.

## 5. P5 / segurança de pagamentos

- `PIX_ENABLED`, chaves Stripe, webhooks, split e contas Connect ficam **como estavam**; não ligar/desligar flags.
- Não testar pagamento real, transferência automática ou split live a partir deste pacote.
- Exigir prova separada: Stripe PaymentIntent/Checkout pago, webhook autenticado recebido/processado, ledger consistente, transferências idempotentes para contas corretamente associadas, reembolsos/disputas.
- Não declarar Pix operacional em produção com base apenas em um endpoint público.
- Não trocar política de comissão sem instrução explícita e reconciliação da percentagem residual.

## 6. Plano de retorno e recuperação

Se falhar **antes do deploy**, manter produção e eliminar **apenas a tentativa de integração local**, usando o backup privado e sem apagar alterações não relacionadas.

Se falhar **depois do deploy**, voltar ao artefacto **realmente anterior de produção** a partir do histórico de deploy Emergent / backup de workspace, nunca presumir que `main` GitHub corresponde à produção. Não fazer `reset --hard`. Restaurar ficheiros seletivamente, reiniciar serviços só após aprovação, confirmar login, QR e estado de pagamento.

**Backups GitHub não são backups de base de dados, segredos ou artefactos de deploy.** Validar separadamente a recuperação desses componentes.

## 7. Portões para autorizar publicação

1. GitHub Actions do release: `static-and-image-safety` e `frontend-build` concluídos com sucesso.
2. Inventário local da Emergent e backup privados realizados e verificados.
3. Comparação e integração seletiva concluídas, sem conflitos desconhecidos.
4. Testes de aceitação do operador num ambiente isolado.
5. Aprovação explícita da publicação. **Nenhuma etapa deste documento autoriza deploy automático.**
