import { useEffect, useState } from "react";
import { FlaskConical, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";

export const StripeModeBanner = ({ compact = false }) => {
  const [cfg, setCfg] = useState(null);
  useEffect(() => { api.get("/payments/config").then((r) => setCfg(r.data)).catch(() => setCfg({ available: false })); }, []);
  if (!cfg || (cfg.mode === "live" && cfg.available)) return null;
  const test = cfg.available && cfg.mode === "test";
  return (
    <div data-testid={test ? "stripe-test-banner" : "stripe-unavailable-banner"} className={`rounded-xl px-3 py-2 text-xs font-semibold flex items-center gap-2 ${test ? "bg-amber-50 text-amber-800 border border-amber-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
      {test ? <FlaskConical className="w-3.5 h-3.5 shrink-0" /> : <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
      {test ? (compact ? "Stripe em modo TESTE — nenhum pagamento é real." : "Pagamentos em MODO TESTE: nenhum dinheiro real é cobrado. Use o cartão 4242 4242 4242 4242 para simular.")
        : "Pagamentos online indisponíveis de momento. Pague diretamente no estabelecimento e mostre o cupão."}
    </div>
  );
};
