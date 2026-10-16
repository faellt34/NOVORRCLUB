# CONEKTA — cópia de trabalho

Branch: `BRANCH-copia-editar-a-vontade`. Base preservada: `8e90ad3`.
As alterações de segurança da worktree `codex/audit-remediation` continuam separadas; esta alteração de interface não significa que todas as falhas da auditoria foram resolvidas.

## Interface

- Visitantes veem uma página pública em `/`; utilizadores autenticados seguem para o painel do seu perfil.
- Acessos distintos para influencer/parceiro já escolhem o perfil no registo.
- Identidade CONEKTA em SVG com K invertido, símbolo inspirado na referência fornecida, ícones PWA 192/512, título e metadados em pt-PT.
- Painel de administração claro/azul, mapa esquemático com cidades agregadas de parceiros, sem geolocalização individual. Cidades sem coordenadas ficam apenas na lista. Valores limitados à moeda escolhida; legado sem moeda corresponde a EUR.
- Telemóvel: menu, atalhos inferiores por perfil, notificações e âncoras de campanhas/validação. Validação QR usa a funcionalidade existente; requer HTTPS e permissão de câmara num dispositivo real.
- PWA existente revista: instalação pelo navegador/Adicionar ao ecrã principal, áreas seguras do ecrã e página sem ligação. Sem cache de API, contas ou cupões. Operações e confirmações exigem internet. Não foi criado nem submetido um pacote nativo para lojas.

## Ativar acesso Google

A integração usa Google Identity Services e verificação de ID token no backend, incluindo audiência, emissor, validade, email verificado e nonce descartável de dez minutos.

1. Criar/usar um cliente OAuth do tipo aplicação Web, configurar consentimento e origens JavaScript autorizadas para o domínio efetivo do frontend. Usar HTTPS.
2. Definir `GOOGLE_CLIENT_ID` no backend. O identificador público é fornecido pelo endpoint `/api/auth/google/config`; não se usa client secret no frontend.
3. Configurar `CORS_ORIGINS` com as origens explícitas do frontend e permitir cookies credenciados. A cookie temporária de nonce é HttpOnly/Secure/SameSite=None. Preferir API no mesmo domínio/proxy `/api` para evitar bloqueio de cookies de terceiros.
4. Se existir CSP no alojamento, permitir os recursos oficiais do Google Identity Services. Não alterar globalmente cabeçalhos de segurança sem rever a política do alojamento.
5. Validar com uma conta de teste autorizada: novo influencer, parceiro pendente, conta suspensa e associação explícita de conta existente.

Sem configuração, a interface apresenta “Entrar com Google” desativado e informa a alternativa por email; não simula autenticação.

Contas existentes não são associadas só por coincidência do email. O utilizador entra primeiro com palavra-passe e abre “Segurança da conta · Associar Google”. Só pode associar o mesmo email. Parceiros novos continuam pendentes e nenhuma conta admin pode ser criada por este fluxo.

Os índices `users.google_sub` (único/parcial) e `google_challenges.expires_at` (TTL) são criados no arranque. Não se executou arranque de produção nem migração sobre dados reais durante esta alteração.

## Configuração preservada

Portugal/EUR continua a opção inicial. `PIX_ENABLED` conserva o valor padrão `false`; não foi alterado nem ativado. Diretor IA e Connect v2 permanecem no código da base. As ferramentas intencionais de limpeza de testes foram preservadas.

## Referência e validação

A página indicada da Flip não respondeu à leitura direta. A página principal `https://flip.net.br/` foi consultada em 16/10/2026: percursos por perfil, explicação por etapas, funcionalidades, FAQ e acompanhamento de resultados inspiraram a organização. Textos, números, depoimentos e promessas comerciais da Flip não foram copiados.

Resultado: build aprovado (com avisos de source maps já existentes da dependência de QR), 19 testes de frontend e 20 de backend aprovados. Percursos mobile de influencer e parceiro verificados em 360/390/768 px, incluindo atalhos, menu e formulário de IBAN, sem overflow ou erros de JavaScript.

Verificações locais, com bases em memória e respostas ilustrativas no navegador: build de produção, testes unitários de frontend, testes offline de identidade/mapa/política de pagamentos, larguras 360/390/768 e desktop. Nenhuma chamada paga, cobrança, alteração de dados reais ou deploy.

A autenticação real Google, instalação física iOS/Android, câmara e distribuição em lojas continuam a exigir validação no domínio/dispositivo final. Os problemas de sessão, pagamentos e limites de IA da auditoria anterior continuam a bloquear uma recomendação de deploy até serem integrados e validados.
