import { useEffect, useState } from "react";
import { api, apiError } from "../lib/api";

// Clone-only sandbox; never marks a real order as paid.
export default function MbWaySandboxTest({ code, amount }) {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    api.get("/public/mbway-sandbox/availability").then(({data}) => {
      if (active) setEnabled(data.enabled === true && data.mode === "test");
    }).catch(() => { if (active) setEnabled(false); });
    return () => { active = false; };
  }, []);
  if (!enabled) return null;
  const start = async () => {
    const value = Number(String(amount || "").replace(",", "."));
    if (!Number.isFinite(value) || value < 0.5 || value > 5000) {
      setMessage("Indica um valor entre 0,50 € e 5.000 €.");
      return;
    }
    setBusy(true); setMessage("");
    try {
      const {data} = await api.post("/public/mbway-sandbox/checkout", {
        code, amount: value, origin_url: window.location.origin
      });
      if (data.mode !== "test" || !data.checkout_url?.startsWith("https://checkout.stripe.com/")) {
        throw new Error("Checkout de testes indisponível.");
      }
      window.location.assign(data.checkout_url);
    } catch (e) { setMessage(apiError(e)); setBusy(false); }
  };
  return <div data-testid="mbway-sandbox-card" className="rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50 p-4 space-y-2">
    <strong className="text-xs text-amber-900">MB WAY · TESTE STRIPE PORTUGAL</strong>
    <p className="text-xs text-amber-800">Simulação sem dinheiro real. Não regista vendas nem distribui comissões.</p>
    <button data-testid="mbway-sandbox-start" type="button" disabled={busy} onClick={start}
      className="w-full rounded-xl bg-amber-800 text-white px-4 py-2 text-sm disabled:opacity-50">
      {busy ? "A abrir teste…" : "Experimentar MB WAY em modo de teste"}
    </button>
    {message && <p role="alert" className="text-xs text-red-700">{message}</p>}
  </div>;
}
