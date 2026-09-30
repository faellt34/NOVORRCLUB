import { useCallback, useEffect, useState } from "react";
import { Coins } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

export const CreditMeter = ({ refreshKey }) => {
  const [u, setU] = useState(null);
  const load = useCallback(() => api.get("/diretor/uso").then((r) => setU(r.data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load, refreshKey]);
  const setLimit = async () => {
    const v = window.prompt("Limite diário de chamadas de IA (5–1000):", u?.limite ?? 60);
    if (!v) return;
    try { const { data } = await api.post("/diretor/uso/limite", { limite_diario: Number(v) }); setU((p) => ({ ...p, ...data })); toast.success(`Limite diário: ${data.limite}`); }
    catch (e) { toast.error(apiError(e)); }
  };
  if (!u) return null;
  const pct = Math.min(100, Math.round((u.hoje / u.limite) * 100));
  return (
    <button data-testid="credit-meter" onClick={setLimit} title="Clique para alterar o limite diário" className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs hover:border-purple-300 btn-press">
      <Coins className={`w-3.5 h-3.5 ${pct >= 90 ? "text-red-500" : "text-amber-500"}`} />
      <span className="font-semibold text-slate-700">Créditos IA hoje: <span data-testid="credit-meter-value">{u.hoje}/{u.limite}</span></span>
      <span className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden"><span className={`block h-full ${pct >= 90 ? "bg-red-500" : "bg-purple-500"}`} style={{ width: `${pct}%` }} /></span>
    </button>
  );
};
