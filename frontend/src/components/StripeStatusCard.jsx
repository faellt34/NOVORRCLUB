import { useCallback, useEffect, useState } from "react";
import { CreditCard, CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

export const StripeStatusCard = () => {
  const [d, setD] = useState(null);
  const load = useCallback(() => { setD(null); api.get("/admin/stripe/status").then((r) => setD(r.data)).catch((e) => toast.error(apiError(e))); }, []);
  useEffect(() => { load(); }, [load]);
  const live = d?.config?.mode === "live" && d?.config?.account_ok;
  return (
    <div className="card-soft p-5 space-y-3" data-testid="stripe-status-card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2"><CreditCard className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">Stripe · pagamentos</h3></div>
        <div className="flex items-center gap-2">
          {d && <span data-testid="stripe-mode-badge" className={`text-xs font-bold px-2.5 py-1 rounded-full ${live ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{live ? "LIVE · dinheiro real" : d.config.account_ok ? "MODO TESTE" : "INDISPONÍVEL"} · {d.done}/{d.total}</span>}
          <button data-testid="stripe-status-refresh" onClick={load} className="p-2 rounded-lg text-slate-500 hover:bg-purple-50 hover:text-purple-600 btn-press"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>
      <p className="text-xs text-slate-500">Estado real da ligação ao Stripe em todo o site (cupões QR, e-books, subscrição, Connect). Cada item explica o que fazer, sem código.</p>
      {!d ? <p className="text-xs text-slate-400">A verificar o Stripe...</p> : (
        <ul className="divide-y divide-slate-100">
          {d.steps.map((s) => (
            <li key={s.id} data-testid={`stripe-step-${s.id}`} className="py-2.5 flex items-start gap-3">
              {s.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />}
              <div className="min-w-0"><p className="text-sm font-semibold text-slate-900">{s.label}</p>{!s.ok && s.action && <p className="text-xs text-purple-700 mt-0.5">→ {s.action}</p>}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
