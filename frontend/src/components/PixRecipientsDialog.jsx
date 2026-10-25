import { useEffect, useState } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const Flag = ({ ok, label }) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
    {ok ? "✓" : "•"} {label}
  </span>
);

const Recipient = ({ role, r }) => {
  const ev = r.evidencia_independente || {};
  return (
    <div data-testid={`pix-recipient-${role}`} className="rounded-xl border border-slate-200 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{role === "partner" ? "Parceiro" : "Influencer"} · {r.nome || "—"}</p>
        <span className="text-[11px] font-mono text-slate-500">{r.pix_account || "sem conta"}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Flag ok={r.charges_enabled} label="cobranças" />
        <Flag ok={r.payouts_enabled} label="depósitos" />
        <Flag ok={r.transfers_capability === "active"} label="transferências" />
        <Flag ok={Object.values(r.metadata_keys || {}).includes("ok")} label="associação" />
      </div>
      {ev.pontos !== undefined && (
        <div className="flex flex-wrap gap-1.5">
          <Flag ok={ev.email_stripe_igual_ao_cadastro} label="email" />
          <Flag ok={ev.nome_stripe_igual_ao_cadastro} label="nome" />
          <Flag ok={ev.kyc_stripe_concluido} label="KYC Stripe" />
          <Flag ok={ev.conta_unica_na_base} label="conta única" />
        </div>
      )}
      <p data-testid={`pix-recipient-${role}-status`} className={`text-xs ${r.bloqueio ? "text-amber-800" : "text-emerald-700"}`}>
        {r.bloqueio ? `Bloqueio: ${r.bloqueio}` : "Pronto para receber"}
      </p>
    </div>
  );
};

export const PixRecipientsDialog = ({ campaign: c, open, onOpenChange }) => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const load = async () => {
    if (!c) return;
    setBusy(true);
    try { const { data } = await api.get(`/admin/pix/recipients/${c.id}`); setData(data); }
    catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  };
  useEffect(() => { setData(null); setResult(null); if (open) load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, c?.id]);

  const reconcile = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/admin/pix/recipients/${c.id}/reconcile`);
      setResult(data.result);
      toast.success("Reconciliação executada; sem alterações financeiras.");
      await load();
    } catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  };

  const recipients = data?.recipients || {};
  const needs = Object.values(recipients).some((r) => r.bloqueio && !Object.values(r.metadata_keys || {}).includes("ok") && r.pix_account);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="pix-recipients-dialog" className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-600" /> Recebimentos Pix · {c?.cupom}</DialogTitle>
          <DialogDescription>Diagnóstico read-only das contas Stripe Connect Brasil. A reconciliação só grava a associação em contas legadas com metadata vazia, conta única e ≥2 provas de titularidade. Nunca cria contas nem altera dados bancários, KYC ou comissões.</DialogDescription>
        </DialogHeader>
        {!data && busy && <p className="text-sm text-slate-500">A consultar Stripe…</p>}
        {data && (
          <div className="space-y-3">
            {Object.entries(recipients).map(([role, r]) => <Recipient key={role} role={role} r={r} />)}
            {data.bloqueio_global && <p className="text-xs text-red-700">{data.bloqueio_global}</p>}
            {result && <p data-testid="pix-reconcile-result" className="text-xs text-slate-700 bg-slate-50 rounded-lg p-2">Parceiro: {result.partner} · Influencer: {result.influencer}</p>}
          </div>
        )}
        <div className="flex gap-2 justify-end">
          <button data-testid="pix-recipients-refresh" onClick={load} disabled={busy} className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50"><RefreshCw className={`w-4 h-4 ${busy ? "animate-spin" : ""}`} /> Atualizar</button>
          <button data-testid="pix-recipients-reconcile" onClick={reconcile} disabled={busy || !data || !needs} className="px-3 py-2 rounded-lg text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40">Reconciliar contas legadas</button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
