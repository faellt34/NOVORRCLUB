import { useEffect, useState } from "react";
import { api, apiError } from "../lib/api";

const labels = {
  api_key: "Chave da conta brasileira",
  platform_country_br: "Operação configurada para o Brasil",
  webhook: "Confirmação automática de pagamentos",
  payment_method_configuration: "Checkout exclusivo para Pix",
  allowed_origins: "Endereços autorizados",
};
const providerLabels = {
  platform_country_br: "Conta da operação brasileira",
  platform_currency_brl: "Liquidação em reais",
  platform_charges_enabled: "Conta autorizada a cobrar",
  platform_pix_active: "Pix habilitado na Stripe",
  configuration_active: "Configuração de checkout ativa",
  configuration_pix_only: "Checkout exclusivo para Pix",
  configuration_mode_matches: "Modo de teste ou produção consistente",
  webhook_registered: "Endpoint de confirmação e eventos registados",
};

export default function PixReadiness() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(false);
  const [provider, setProvider] = useState(null);
  const [checking, setChecking] = useState(false);
  const [providerError, setProviderError] = useState("");
  const verifyProvider = async () => {
    setChecking(true); setProviderError(""); setProvider(null);
    try { const { data } = await api.get("/admin/pix/provider-readiness"); setProvider(data); }
    catch (e) { setProviderError(apiError(e)); }
    finally { setChecking(false); }
  };
  useEffect(() => {
    api.get("/admin/pix/readiness").then(({ data }) => setState(data)).catch(() => setError(true));
  }, []);
  return <section className="card-soft p-5 space-y-3" data-testid="pix-readiness">
    <h3 className="text-lg font-semibold text-slate-900">Pix · Brasil</h3>
    <p className="text-sm text-slate-600">{error ? "Não foi possível verificar a configuração." : !state ? "A verificar configuração..." : state.accepting_new_payments ? "Configuração habilitada. Validar os pagamentos na Stripe antes de liberar a operação." : "Aguardando configuração para liberar cobranças."}</p>
    {state && <ul className="text-xs space-y-2">{Object.entries(labels).map(([key, label]) => <li key={key} className={state.configuration?.[key] ? "text-emerald-700" : "text-amber-700"}>{state.configuration?.[key] ? "✓" : "○"} {label}</li>)}</ul>}
    <p className="text-xs text-slate-500">Os cadastros podem ser criados antes da ativação. Numa conta de R$ 100, o cliente paga R$ 95: R$ 80 para o parceiro, R$ 5 para o influencer e R$ 10 para a RR Club, que assume as taxas.</p>
    <p className="text-xs text-slate-500">Esta verificação confere a configuração local. A validação com a conta brasileira ainda é necessária.</p>
    <button type="button" onClick={verifyProvider} disabled={checking} className="rounded-xl bg-purple-600 px-4 py-2 text-sm text-white disabled:opacity-50">{checking ? "A consultar Stripe..." : "Verificar Stripe sem cobrar"}</button>
    {providerError && <p role="alert" className="text-sm text-red-700">{providerError}</p>}
    {provider && <div data-testid="pix-provider-readiness" className="space-y-2 text-xs">
      <p>{provider.provider_verified ? "Configuração conferida na Stripe. Ainda é necessário validar pagamento, webhook e repasses em ambiente de teste." : "Existem requisitos pendentes. A consulta não ativou cobranças nem alterou contas."}</p>
      {provider.platform_country && <p>País da conta consultada: {provider.platform_country} · liquidação: {provider.settlement_currency?.toUpperCase()}</p>}
      {!!provider.missing_configuration?.length && <p>Complete os itens de configuração acima antes de consultar a conta.</p>}
      <ul className="space-y-1">{Object.entries(provider.checks || {}).map(([key, ok]) => <li key={key} className={ok ? "text-emerald-700" : "text-amber-700"}>{ok ? "✓" : "○"} {providerLabels[key] || key}</li>)}</ul>
    </div>}
  </section>;
}
