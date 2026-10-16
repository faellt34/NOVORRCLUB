import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

export default function PixReceivingAccount() {
  const [status, setStatus] = useState(null);
  const [available, setAvailable] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api.get("/public/pix/availability").then(async ({ data }) => {
      if (cancelled) return;
      setAvailable(data.configured);
      if (data.configured) {
        const response = await api.get("/partner/pix/connect/status");
        if (!cancelled) setStatus(response.data);
      }
    }).catch(() => { if (!cancelled) setAvailable(false); });
    return () => { cancelled = true; };
  }, []);
  const configure = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/partner/pix/connect/onboard", { origin_url: window.location.origin });
      window.location.assign(data.url);
    } catch (e) { toast.error(apiError(e)); setBusy(false); }
  };
  return <section className="card-soft p-4 mb-4" data-testid="pix-receiving-account">
    <h3 className="text-sm font-semibold text-slate-900">Conta de recebimento · Brasil</h3>
    <p className="text-xs text-slate-500 mt-1">{available === false ? "A sua conta RR Club pode ser utilizada. Os recebimentos Pix aguardam a configuração brasileira da plataforma; poderá associar a sua conta depois." : status?.payouts_enabled ? "Recebimentos habilitados na Stripe. Os depósitos seguem os prazos da conta." : "Configure a sua conta brasileira para receber os 5% das vendas Pix. A RR Club assume as taxas de processamento."}</p>
    {!status?.payouts_enabled && <button type="button" onClick={configure} disabled={busy || !available} className="mt-3 rounded-xl bg-purple-600 text-white text-xs px-4 py-3 disabled:opacity-50">{busy ? "A abrir..." : "Configurar recebimentos"}</button>}
  </section>;
}
