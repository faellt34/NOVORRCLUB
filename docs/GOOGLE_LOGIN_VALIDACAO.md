# Login Google — integração isolada RRClub

Base: `mainNNOVO`, commit `18cb68bbad17b452120da6101931d815abc4e04c`.
Origem do trabalho recuperado: `BRANCH-copia-editar-a-vontade`, commit `3d765b2f98df486809c7b348022af67fe0e6a8b1`.

## Comportamento

O botão Google usa Google Identity Services. O servidor valida o ID token com
o Client ID configurado, emissor, validade, email verificado e nonce de uso
único. A identidade estável é `google_sub`.

Uma conta existente não é vinculada automaticamente pelo email: o usuário
entra pelo login atual e usa **Segurança da conta · Associar Google**. O email
deve coincidir e o mesmo Google não pode pertencer a outro usuário. O vínculo
preserva IDs, papel, moeda, parceiro/influencer e destinos Stripe existentes.

Novos cadastros exigem perfil e aceite da Política de Privacidade. Parceiros
continuam pendentes de aprovação; o navegador não pode criar administradores
nem promover o papel de contas existentes. O login tradicional permanece.

O frontend renova o nonce após tentativa recusada e após associação concluída;
assim uma nova tentativa não reutiliza o desafio já consumido pelo servidor.
Sem configuração Google, informa o estado e mantém email/senha disponível.

## Escopo

Somente autenticação, pontos de entrada do login/cadastro, associação explícita,
índices Google e testes. Não inclui marca CONEKTA, mapa, redesign, limpeza de
dados, alterações de contas Stripe, pagamentos ou variáveis Pix.

## Verificação realizada em 19/10/2026

- Backend: 16 testes offline aprovados, incluindo preservação de vínculos e
  permissões, não duplicação, suspensão/aprovação, rejeição de replay e
  configuração ausente. Banco em memória, sem conexão a produção.
- Frontend: 34 testes aprovados em 7 suites. Incluem Google, sessão existente,
  estado pendente do parceiro, termos, renovação de nonce e regressões dos
  componentes já presentes.
- Sintaxe Python de `routes_auth.py`, `google_identity.py` e `server.py`: válida.
- Build de produção: compilado com `REACT_APP_BACKEND_URL=https://rrclub.online`.
  Avisos de source maps da dependência `html5-qrcode`; sem erro de compilação.
  Na instalação local por npm, foi necessário instalar `ajv@8.17.1` com
  `--no-save` para resolver o AJV transitivo de `react-scripts`. O manifest de
  dependências não foi alterado. O repositório não tem lockfile; a instalação
  limpa no ambiente de implantação ainda precisa ser conferida.
- Login Google real no domínio final: não executado.

## Configuração necessária antes da ativação

1. Usar um cliente OAuth Google do tipo **Aplicativo da Web**.
2. Autorizar a origem real `https://rrclub.online`. Incluir `https://www.rrclub.online`
   somente se esse domínio também servir o frontend. A origem de preview usada
   nos testes também precisa ser autorizada.
3. Configurar `GOOGLE_CLIENT_ID` no backend. Esse identificador é público;
   este fluxo não usa Client Secret no frontend e não precisa de senha Google.
4. Manter frontend e API no mesmo domínio (`/api`) e conferir `CORS_ORIGINS`
   com as origens efetivamente usadas. Cookies de nonce e sessão exigem HTTPS.
5. Conferir o estado de publicação/usuários de teste no projeto Google e as
   permissões necessárias à biblioteca oficial caso o alojamento use CSP.
6. Validar numa prévia a associação e nova entrada de uma conta existente,
   um novo influencer e um parceiro pendente, além de rejeitar conta suspensa.
   Conferir que IDs e vínculos Stripe permanecem iguais.
7. Só então publicar o código integrado. Não substituir a versão atual pela
   branch antiga inteira. Nenhum deploy foi executado nesta preparação.

No arranque são criados índices específicos para `google_sub` (único/parcial)
e expiração de desafios Google. Não apagam registros existentes; conflitos
de índice precisam ser resolvidos antes de aprovar a implantação.

Referências oficiais:
- https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid
- https://developers.google.com/identity/gsi/web/guides/verify-google-id-token

## Configuração do Client ID público (19/10/2026)

O identificador público OAuth Web da RRClub está definido como fallback em `backend/google_identity.py`, permitindo que o backend disponibilize `/api/auth/google/config` mesmo antes da criação da variável no painel Emergent. `GOOGLE_CLIENT_ID` continua a ter prioridade quando definida. A mesma origem é usada na verificação do ID token, não apenas na interface.

Este fallback **não é um Client Secret** e não substitui os requisitos: publicar primeiro a branch integrada correta, confirmar que a Emergent está a construir essa versão, instalar dependências, testar o OAuth real, verificar os utilizadores de teste da tela de consentimento e obter autorização antes de republicar. O botão não pode aparecer no site já publicado apenas por um commit GitHub. Não copiar nem publicar a chave secreta OAuth.
