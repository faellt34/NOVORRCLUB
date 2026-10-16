import { useEffect, useState } from "react";
import { api } from "../lib/api";

const labels = {
  api_key: "Chave da conta brasileira",
  platform_country_br: "Operação configurada para o Brasil",
  webhook: "Confirmação automática de pagamentos",
  payment_method_configuration: "Checkout exclusivo para Pix",
  allowed_origins: "Endereços autorizados",
};

export default function PixReadiness() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    api.get("/admin/pix/readiness").then(({ data }) => setState(data)).catch(() => setError(true));
  }, []);
  return <section className="card-soft p-5 space-y-3" data-testid="pix-readiness">
    <h3 className="text-lg font-semibold text-slate-900">Pix · Brasil</h3>
    <p className="text-sm text-slate-600">{error ? "Não foi possível verificar a configuração." : !state ? "A verificar configuração..." : state.accepting_new_payments ? "Configuração habilitada. Validar os pagamentos na Stripe antes de liberar a operação." : "Aguardando configuração para liberar cobranças."}</p>
    {state && <ul className="text-xs space-y-2">{Object.entries(labels).map(([key, label]) => <li key={key} className={state.configuration?.[key] ? "text-emerald-700" : "text-amber-700"}>{state.configuration?.[key] ? "✓" : "○"} {label}</li>)}</ul>}
    <p className="text-xs text-slate-500">Os cadastros podem ser criados antes da ativação. Numa conta de R$ 100, o cliente paga R$ 95: R$ 80 para o parceiro, R$ 5 para o influencer e R$ 10 para a RR Club, que assume as taxas.</p>
    <p className="text-xs text-slate-500">Esta verificação confere a configuração local. A validação com a conta brasileira ainda é necessária.</p>
  </section>;
}
