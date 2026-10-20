# Stripe Connect — requisitos de verificação para contas no Brasil

Data de registo: 20/10/2026. Estado: documentação de referência; **não** comprova pendências ou aprovação de qualquer conta.

## Âmbito
Configuração descrita na documentação fornecida: Accounts API v1; país da plataforma BR; país da conta BR; Dashboard none; service agreement full; pessoa física (individual); capacidades card_payments e transfers.

**Atenção:** este cenário BR→BR não comprova que uma plataforma sediada em Portugal possa conectar e repartir pagamentos para contas brasileiras. Confirmar suporte transfronteiriço, modelo Connect e obrigações específicas antes de implementar.

## Campos indicados
- Conta: business_profile.mcc, business_profile.url, tos_acceptance.date/ip, business_profile.monthly_estimated_revenue.amount/currency, external_account.
- Pessoa física: individual.first_name/last_name, individual.dob.day/month/year (18+), individual.address.city/line1/postal_code/state, individual.email, individual.phone, individual.political_exposure, individual.id_number (CPF), individual.verification.proof_of_liveness.
- Poderão ser exigidos documentos oficiais de identificação e prova de presença, conforme o fluxo de verificação e resultado KYC.

## Verificações e riscos
- Falta de dados ou falha de verificação pode suspender capacidades, pagamentos e/ou repasses conforme o campo.
- Verificação de CPF e situação cadastral; considerar erros verification_failed_id_number_inactive, verification_failed_keyed_match e verification_document_type_not_supported.
- Receita mensal estimada em centavos (exemplo: R$ 50.000,00 = 5000000).
- Onboarding hospedado ou incorporado da Stripe pode facilitar recolha segura de KYC e prova de presença.

## Próximas ações
1. Confirmar que a arquitetura e o país da plataforma correspondem ao cenário efetivo da RRClub Brasil.
2. Validar documentação atualizada da Stripe e enquadramento jurídico com responsável habilitado.
3. Testar onboarding com contas e credenciais de teste autorizadas, sem criar contas reais.
4. Nunca armazenar CPF, documentos ou dados sensíveis nos logs ou neste repositório.
5. Manter separação entre requisitos Brasil e Portugal; não alterar produção nem a branch main com esta documentação.

Fonte fornecida pelo utilizador: texto “Required verification information — Requirements for account-setup-A” (Stripe Connect, BR).
