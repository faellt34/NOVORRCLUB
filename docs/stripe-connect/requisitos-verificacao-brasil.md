# Stripe Connect — requisitos brasileiros (referência)

Registado em 20/10/2026. Documento informativo, sem alteração de código ou ativação de pagamentos.

## Configuração abrangida pela fonte
Accounts API v1; país da plataforma BR; país da conta BR; dashboard none; service agreement full; business type individual; capacidades card_payments e transfers.

## Requisitos apresentados pela Stripe
**Conta:** business_profile.mcc; business_profile.url; tos_acceptance.date e tos_acceptance.ip; business_profile.monthly_estimated_revenue.amount/currency; external_account.

**Pessoa física:** individual.first_name/last_name; individual.dob.day/month/year (maior de 18 anos); individual.address.city/line1/postal_code/state; individual.email; individual.phone; individual.political_exposure; individual.id_number (CPF); individual.verification.proof_of_liveness.

A Stripe pode exigir documentos oficiais de identidade, verificação de presença e validação do CPF. A ausência ou não verificação de dados pode suspender capacidades, pagamentos e/ou transferências, consoante o requisito. Receita mensal estimada é informada em centavos (R$ 50.000,00 = 5000000).

Erros KYC referidos: verification_failed_id_number_inactive; verification_failed_keyed_match; verification_document_type_not_supported.

## Limites da validação
O texto fornecido descreve **plataforma BR e conta BR**. A sua inclusão na branch principal não demonstra que uma plataforma portuguesa possa fazer Connect ou repartir fundos com contas brasileiras, nem demonstra conformidade jurídica ou aprovação da Stripe. Validar separadamente o cenário Portugal–Brasil, a configuração efetiva da plataforma e requisitos atuais no Dashboard.

Não armazenar dados pessoais de verificação neste repositório. Não alterar contas, configurações de pagamentos ou produção com base apenas nesta documentação.

Fonte: texto «Required verification information — Requirements for account-setup-A», partilhado pelo utilizador, relativo à Stripe Connect Brasil.
