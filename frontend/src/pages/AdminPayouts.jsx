import { useCallback, useEffect, useState } from "react";
import { Wallet, CheckCircle2, Clock, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, eur, num } from "../lib/api";
import { PageSkeleton } from "../components/PageSkeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

const monthLabel = (id) => {
  const [y, m] = id.split("-");
  const s = new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("pt-PT", { month: "long", year: "numeric" });
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export default function AdminPayouts() {
  const [rows, setRows] = useState(null);
  const [filter, setFilter] = useState("todos");
  const [busy, setBusy] = useState(null);
  const [financeRows, setFinanceRows] = useState([]);
  const [financeBusy, setFinanceBusy] = useState(null);
  const [financeEvidence, setFinanceEvidence] = useState({});

  useEffect(() => {
    api.get("/admin/finance/reconciliation").then((r) => setFinanceRows(r.data))
      .catch((e) => toast.error(apiError(e)));
  }, []);

  const verifyStripe = async (r) => {
    setFinanceBusy(r.session_id);
    try {
      const { data } = await api.get(`/admin/finance/reconciliation/${encodeURIComponent(r.session_id)}`);
      setFinanceEvidence((old) => ({ ...old, [r.session_id]: data }));
    } catch (e) {
      toast.error(apiError(e));
    } finally { setFinanceBusy(null); }
  };


  const load = useCallback(() => api.get("/admin/payouts").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { load(); }, [load]);

  const markPaid = async (r) => {
    if (!window.confirm(`Marcar ${monthLabel(r.month)} de ${r.influencer} (${eur(r.commission)}) como pago?`)) return;
    setBusy(`${r.influencer_id}-${r.month}`);
    try { await api.post("/admin/payouts", { influencer_id: r.influencer_id, month: r.month }); toast.success(`Pagamento registado · ${r.influencer} notificado`); load(); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  const revert = async (r) => {
    setBusy(`${r.influencer_id}-${r.month}`);
    try { await api.delete(`/admin/payouts/${r.influencer_id}/${r.month}`); toast.success("Revertido para pendente"); load(); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  if (!rows) return <PageSkeleton />;
  const shown = rows.filter((r) => filter === "todos" || r.status === filter);
  const pending = rows.filter((r) => r.status === "Pendente").reduce((s, r) => s + r.commission, 0);
  const paid = rows.filter((r) => r.status === "Pago").reduce((s, r) => s + r.commission, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 data-testid="payouts-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Pagamentos de Comissões</h1>
          <p className="text-sm text-slate-500 mt-1">Marque cada extrato mensal como pago após a transferência — o influencer é notificado e vê a data</p>
        </div>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger data-testid="payouts-filter" className="w-[160px] bg-white rounded-xl"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos</SelectItem>
            <SelectItem value="Pendente">Pendentes</SelectItem>
            <SelectItem value="Pago">Pagos</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card-soft p-5 flex items-center gap-4" data-testid="payouts-pending-total">
          <span className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center"><Clock className="w-5 h-5" /></span>
          <div><p className="font-display text-2xl font-extrabold text-slate-900">{eur(+pending.toFixed(2))}</p><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Por pagar</p></div>
        </div>
        <div className="card-soft p-5 flex items-center gap-4" data-testid="payouts-paid-total">
          <span className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center"><Wallet className="w-5 h-5" /></span>
          <div><p className="font-display text-2xl font-extrabold text-slate-900">{eur(+paid.toFixed(2))}</p><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Já pago</p></div>
        </div>
      </div>

      <div className="card-soft p-5" data-testid="finance-reconciliation">
        <h2 className="text-lg font-semibold text-slate-900">Auditoria financeira · Stripe Portugal</h2>
        <p className="text-xs text-slate-500 mt-1 mb-4">
          Pagamento confirmado não é o mesmo que transferência ao parceiro nem levantamento bancário.
          Esta consulta à Stripe é de leitura apenas: não inicia pagamentos nem repasses.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-500 border-b">
              <th className="py-2 pr-3">Cupão / Parceiro</th>
              <th className="py-2 pr-3">Pagamento</th>
              <th className="py-2 pr-3">Transferência Stripe</th>
              <th className="py-2 pr-3">Banco</th>
              <th className="py-2">Verificação</th>
            </tr></thead>
            <tbody>
              {financeRows.map((r) => {
                const proof = financeEvidence[r.session_id];
                return <tr key={r.session_id} className="border-b border-slate-100">
                  <td className="py-3 pr-3"><p className="font-semibold">{r.coupon}</p>
                    <p className="text-xs text-slate-500">{r.partner}</p></td>
                  <td className="py-3 pr-3"><p>{r.currency === "eur" ? eur(r.amount || 0) : `${r.amount || 0} ${r.currency || ""}`}</p>
                    <p className="text-xs text-slate-500">{r.payment_status === "paid" ? "Confirmado" : "Não confirmado"}</p></td>
                  <td className="py-3 pr-3">
                    {proof?.state === "transferred_to_connected_stripe_account"
                      ? <span className="text-emerald-700 font-semibold">Confirmada na Stripe · {proof.transfer_id}</span>
                      : <span className="text-amber-700">{proof ? `Sem confirmação: ${proof.state}` : "Por verificar"}</span>}
                  </td>
                  <td className="py-3 pr-3 text-xs text-slate-500">Não verificado</td>
                  <td className="py-3"><button onClick={() => verifyStripe(r)}
                    disabled={financeBusy === r.session_id || r.payment_status !== "paid"}
                    className="px-3 py-1.5 rounded-lg border border-purple-200 text-purple-700 disabled:opacity-50 hover:bg-purple-50 text-xs font-semibold">
                    {financeBusy === r.session_id ? "A consultar..." : "Verificar na Stripe"}
                  </button></td>
                </tr>;
              })}
              {!financeRows.length && <tr><td colSpan={5} className="py-5 text-slate-500 text-center">
                Sem transações de cupões nesta consulta.
              </td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card-soft p-5">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm" data-testid="payouts-table">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                <th className="pb-3 pr-4 font-semibold">Mês</th>
                <th className="pb-3 pr-4 font-semibold">Influencer</th>
                <th className="pb-3 pr-4 font-semibold">Redenções</th>
                <th className="pb-3 pr-4 font-semibold">Comissão</th>
                <th className="pb-3 pr-4 font-semibold">Estado</th>
                <th className="pb-3 font-semibold text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => {
                const key = `${r.influencer_id}-${r.month}`;
                return (
                  <tr key={key} data-testid={`payout-row-${key}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40 transition-colors">
                    <td className="py-3 pr-4 font-semibold text-slate-900">{monthLabel(r.month)}</td>
                    <td className="py-3 pr-4 text-slate-700">{r.influencer}{r.iban && <p className="text-[11px] font-mono text-slate-400">{r.iban}</p>}</td>
                    <td className="py-3 pr-4 text-slate-600">{num(r.count)}</td>
                    <td className="py-3 pr-4 font-bold text-purple-700">{eur(r.commission)}</td>
                    <td className="py-3 pr-4">
                      {r.status === "Pago"
                        ? <span data-testid={`payout-status-${key}`} className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full"><CheckCircle2 className="w-3 h-3" /> Pago em {new Date(r.paid_at).toLocaleDateString("pt-PT")}</span>
                        : <span data-testid={`payout-status-${key}`} className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full"><Clock className="w-3 h-3" /> Pendente</span>}
                    </td>
                    <td className="py-3 text-right">
                      {r.status === "Pendente"
                        ? <button data-testid={`mark-paid-${key}`} disabled={busy === key} onClick={() => markPaid(r)} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white text-xs font-semibold btn-press">Marcar como pago</button>
                        : <button data-testid={`revert-paid-${key}`} disabled={busy === key} onClick={() => revert(r)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-semibold btn-press"><Undo2 className="w-3 h-3" /> Reverter</button>}
                    </td>
                  </tr>
                );
              })}
              {shown.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-slate-400">Sem registos.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
