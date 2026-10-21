import { useEffect, useState } from "react";
import { api, apiError } from "../lib/api";

/** Admin-only, read-only: never starts payments, Stripe transfers or KYC. */
export default function PortugalSplitPanel() {
  const [report, setReport] = useState(null);
  const [selected, setSelected] = useState(null);
  const [accountInventory, setAccountInventory] = useState(null);
  const [checking, setChecking] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.get("/admin/finance/pt-split/accounts")
      .then(({ data }) => { if (active) setAccountInventory(data); })
      .catch((err) => { if (active) setError(apiError(err)); });
    api.get("/admin/finance/pt-split/health")
      .then(({ data }) => { if (active) setReport(data); })
      .catch((err) => { if (active) setError(apiError(err)); });
    return () => { active = false; };
  }, []);

  const inspect = async (campaign) => {
    setChecking(campaign.id);
    setError("");
    try {
      const { data } = await api.get(
        "/admin/finance/pt-split/campaign/" + encodeURIComponent(campaign.id)
      );
      setSelected({ name: campaign.name, ...data });
    } catch (e) {
      setError(apiError(e));
    } finally {
      setChecking(null);
    }
  };

  const eligible = selected?.ready_for_new_p5_live_charge === true;
  return (
    <section className="card-soft p-5" data-testid="pt-split-readiness">
      <h2 className="text-lg font-semibold text-slate-900">
        Portugal · Estado real do split 5 / 80 / 5 / 10
      </h2>
      <p className="text-xs text-slate-500 mt-1">
        Desconto do seguidor: 5%. Parceiro: 80%. Influenciador: 5%.
        RRClub: 10%, antes das taxas Stripe. Consulta sem movimentar dinheiro.
      </p>
      {error && <p className="text-sm text-red-700 mt-3" role="alert">{error}</p>}
      {!report && !error && <p className="text-sm text-slate-500 mt-3">A verificar regras Portugal...</p>}
      {report && (
        <>
          <p className="mt-3 text-sm font-semibold">
            {report.configuration?.automatic_transfers_enabled
              ? "Automatização configurada — verificar destinatários por campanha"
              : "Automatização P5 Portugal desativada — pagamentos antigos não são redistribuídos"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Transferência Stripe Connect e depósito bancário são operações distintas.
          </p>
          {accountInventory && (
            <div className="mt-4 rounded-xl border border-slate-200 p-3 space-y-3" data-testid="pt-account-aliases">
              <h3 className="text-sm font-semibold">Contas Stripe PT identificadas por ID</h3>
              <p className="text-xs text-slate-600">
                PT-01 e PT-02 são nomes provisórios, não representam o titular nem autorizam transferências.
              </p>
              {accountInventory.platform_status !== "verified_live_portugal" && (
                <p className="text-xs text-amber-700" role="status">
                  Não foi possível validar as contas na plataforma Stripe Portugal LIVE neste ambiente:
                  {" "}{accountInventory.platform_status}.
                </p>
              )}
              {accountInventory.accounts?.map((account) => (
                <div key={account.account_id} className="rounded-lg bg-slate-50 p-3 text-xs space-y-1">
                  <p className="font-semibold text-slate-800">{account.label}</p>
                  <p className="font-mono text-slate-600 break-all">{account.account_id}</p>
                  <p className={account.financially_capable ? "text-emerald-700" : "text-amber-700"}>
                    {account.financially_capable ? "Recebimentos e transfers aptos"
                      : account.status === "not_checked" ? "Verificação indisponível neste ambiente"
                      : "Recebimentos não comprovados agora"}
                  </p>
                  <p className={account.binding_verified ? "text-emerald-700" : "text-amber-700"}>
                    {account.binding_verified
                      ? ("Vínculo confirmado: " + (account.role === "partner" ? "Parceiro" : "Influenciador"))
                      : "Titularidade não associada por ID: não usar para split"}
                  </p>
                  {account.partner_record && <p>Registo de parceiro encontrado: {account.partner_record.name || account.partner_record.id} (não comprova titularidade)</p>}
                  {account.influencer_record && <p>Registo de influenciador encontrado: {account.influencer_record.name || account.influencer_record.id} (não comprova titularidade)</p>}
                </div>
              ))}
            </div>
          )}
          <div className="mt-3 space-y-2">
            {report.campaigns?.map((c) => (
              <div key={c.id} className="flex flex-wrap gap-2 items-center justify-between border-b border-slate-100 py-2">
                <span className="text-sm text-slate-700">
                  {c.name} — {c.rule_matches ? "percentagens 5/80/5/10" : "regras ou beneficiários por corrigir"}
                </span>
                <button type="button" onClick={() => inspect(c)} disabled={checking === c.id}
                  className="text-xs font-semibold px-3 py-2 rounded-lg border border-purple-200 text-purple-700 disabled:opacity-50">
                  {checking === c.id ? "A consultar Stripe..." : "Verificar beneficiários"}
                </button>
              </div>
            ))}
          </div>
          {selected && (
            <div className="mt-4 rounded-lg border border-slate-200 p-3 text-sm">
              <strong>{selected.name}</strong>
              <p className={eligible ? "text-emerald-700" : "text-amber-700"}>
                {eligible
                  ? "Condições técnicas satisfeitas para nova cobrança P5"
                  : "Aguardando configuração, elegibilidade Connect ou correção das regras"}
              </p>
              <p>Parceiro: {selected.receivers?.partner?.ok ? "Connect apto" : selected.receivers?.partner?.reason || selected.receivers?.reason || "Não verificado"}</p>
              <p>Influenciador: {selected.receivers?.influencer?.ok ? "Connect apto" : selected.receivers?.influencer?.reason || selected.receivers?.reason || "Não verificado"}</p>
              <p className="text-xs text-slate-500">Depósito bancário: não comprovado por esta consulta.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
