import { useEffect, useState } from "react";
import { api, apiError, moneyIn } from "../lib/api";

const proofLabels = {
  transferred_to_connected_stripe_account: "Transferência confirmada para Stripe Connect",
  payment_not_succeeded: "Pagamento não confirmado",
  stripe_session_not_paid: "Checkout não confirmado",
  local_payment_not_confirmed: "Pagamento ainda não conciliado",
  no_transfer_evidence: "Sem comprovativo de transferência",
  partner_connect_unlinked: "Parceiro sem conta Connect associada",
  destination_unlinked: "Destinatário não identificado",
  destination_mismatch: "Destinatário da transferência diferente",
  reversed_or_partially_reversed: "Transferência revertida ou parcialmente revertida",
  stripe_payment_campaign_mismatch: "Campanha ou parceiro não corresponde",
  session_metadata_mismatch: "Metadados da campanha não correspondem",
  transfer_not_verifiable: "Transferência ainda não verificável",
  amount_mismatch: "Valores da transação não correspondem",
};

export default function FinanceReconciliationPanel() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [proofs, setProofs] = useState({});

  useEffect(() => {
    let active = true;
    api.get("/admin/finance/reconciliation")
      .then(({ data }) => { if (active) setRows(Array.isArray(data) ? data : []); })
      .catch((e) => { if (active) setError(apiError(e)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const verify = async (row) => {
    if (!row.session_id || row.payment_status !== "paid") return;
    setBusy(row.session_id);
    try {
      const { data } = await api.get(
        "/admin/finance/reconciliation/" + encodeURIComponent(row.session_id)
      );
      setProofs((prev) => ({ ...prev, [row.session_id]: data }));
    } catch (e) {
      setProofs((prev) => ({
        ...prev,
        [row.session_id]: { state: "error", message: apiError(e) },
      }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="card-soft p-5" data-testid="finance-reconciliation">
      <h2 className="text-lg font-semibold text-slate-900">Auditoria financeira · Stripe Portugal</h2>
      <p className="text-xs text-slate-500 mt-1 mb-4">
        Pagamento recebido, comissão apurada, transferência Connect e levantamento bancário
        são acontecimentos diferentes. Consulta de leitura apenas, sem movimentações financeiras.
      </p>
      {loading && <p className="text-sm text-slate-500">A carregar auditoria...</p>}
      {error && <p className="text-sm text-red-600" role="alert">Auditoria indisponível: {error}</p>}
      {!loading && !error && rows.length === 0 && (
        <p className="text-sm text-slate-500">Sem transações de cupões EUR neste relatório.</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-2 pr-3">Cupão / Parceiro</th>
              <th className="py-2 pr-3">Pagamento</th>
              <th className="py-2 pr-3">Transferência Stripe</th>
              <th className="py-2 pr-3">Banco</th>
              <th className="py-2">Verificar</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const id = row.session_id;
              const proof = proofs[id];
              const transferFound = proof?.state === "transferred_to_connected_stripe_account";
              return (
                <tr key={id || index} className="border-b border-slate-100">
                  <td className="py-3 pr-3">
                    <strong>{row.coupon || "—"}</strong>
                    <p className="text-xs text-slate-500">{row.partner || "Parceiro não identificado"}</p>
                  </td>
                  <td className="py-3 pr-3">
                    {moneyIn(row.amount || 0, "eur")}
                    <p className="text-xs text-slate-500">
                      {row.payment_status === "paid" ? "Recebido" : "Ainda não confirmado"}
                    </p>
                  </td>
                  <td className="py-3 pr-3">
                    <span className={transferFound ? "text-emerald-700" : "text-amber-700"}>
                      {!proof ? "Por verificar" : proofLabels[proof.state] || proof.message || proof.state}
                    </span>
                    {proof?.transfer_id && <p className="text-xs text-slate-500">{proof.transfer_id}</p>}
                  </td>
                  <td className="py-3 pr-3 text-xs text-slate-500">Não verificado</td>
                  <td className="py-3">
                    <button
                      type="button"
                      disabled={busy === id || !id || row.payment_status !== "paid"}
                      onClick={() => verify(row)}
                      className="rounded-lg border border-purple-200 px-3 py-2 text-xs font-semibold text-purple-700 disabled:opacity-50"
                    >
                      {busy === id ? "A consultar..." : "Verificar na Stripe"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
