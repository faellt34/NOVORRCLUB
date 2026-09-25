import { useEffect, useState } from "react";
import { Clapperboard, Play, Trash2, RefreshCw, CheckCircle2, Loader2, Circle } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, eur } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

const STEPS = ["Campanha criada", "QR gerado", "Cliente clicou no link", "QR baixado", "Pagamento processado", "Split executado"];

export const TestRunDialog = ({ open, onOpenChange, eventos, onDone }) => {
  const [infs, setInfs] = useState([]);
  const [parts, setParts] = useState([]);
  const [inf, setInf] = useState("");
  const [part, setPart] = useState("");
  const [valor, setValor] = useState("50");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState({});
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!open) return;
    Promise.all([api.get("/admin/influencers"), api.get("/admin/parceiros")]).then(([a, b]) => { setInfs(a.data); setParts(b.data); setInf((v) => v || a.data[0]?.id || ""); setPart((v) => v || b.data[0]?.id || ""); }).catch((e) => toast.error(apiError(e)));
  }, [open]);

  useEffect(() => {
    const ev = eventos[0];
    if (ev?.tipo === "teste_passo" && (running || result)) setSteps((s) => ({ ...s, [ev.passo]: { titulo: ev.titulo, estado: ev.estado } }));
  }, [eventos]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async () => {
    setRunning(true); setSteps({}); setResult(null);
    try { const { data } = await api.post("/admin/test-run", { influencer_id: inf, partner_id: part, valor }); setResult(data); onDone?.(); }
    catch (e) { toast.error(apiError(e)); }
    finally { setRunning(false); }
  };
  const clear = async () => {
    try { await api.delete(`/admin/test-run/${result.run_id}`); toast.success("Dados deste teste apagados"); setResult(null); setSteps({}); onDone?.(); onOpenChange(false); }
    catch (e) { toast.error(apiError(e)); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !running && onOpenChange(o)}>
      <DialogContent data-testid="test-run-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Clapperboard className="w-4 h-4 text-purple-600" /> Novo Teste — fluxo completo</DialogTitle>
          <DialogDescription>Simula clique → QR → pagamento (Stripe modo teste) → split, sem dinheiro real. Os dashboards atualizam ao vivo.</DialogDescription>
        </DialogHeader>
        {!running && !result && (
          <div className="space-y-3">
            <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Influencer</label>
              <Select value={inf} onValueChange={setInf}><SelectTrigger data-testid="test-influencer-select" className="rounded-xl bg-slate-50"><SelectValue placeholder="Escolher" /></SelectTrigger><SelectContent>{infs.map((i) => <SelectItem key={i.id} value={i.id}>{i.nome} {i.handle ? `· ${i.handle}` : ""}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Parceiro (restaurante)</label>
              <Select value={part} onValueChange={setPart}><SelectTrigger data-testid="test-partner-select" className="rounded-xl bg-slate-50"><SelectValue placeholder="Escolher" /></SelectTrigger><SelectContent>{parts.map((p) => <SelectItem key={p.id} value={p.id}>{p.nome} · {p.cidade}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Valor da conta (€)</label><Input data-testid="test-valor-input" value={valor} onChange={(e) => setValor(e.target.value)} inputMode="decimal" className="rounded-xl bg-slate-50" /></div>
            <button data-testid="test-run-execute" disabled={!inf || !part} onClick={run} className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press inline-flex items-center justify-center gap-2"><Play className="w-4 h-4" /> Executar fluxo completo</button>
          </div>
        )}
        {(running || result) && (
          <div className="space-y-4">
            <ol className="space-y-2" data-testid="test-steps">
              {STEPS.map((label, i) => { const n = i + 1, st = steps[n]; const ok = st?.estado === "ok" || (result && !st); const run = st?.estado === "run" && !result; return (
                <li key={n} data-testid={`test-step-${n}`} data-state={ok ? "ok" : run ? "run" : "wait"} className={`flex items-center gap-2 text-sm ${ok ? "text-slate-900" : run ? "text-purple-700" : "text-slate-400"}`}>
                  {ok ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : run ? <Loader2 className="w-4 h-4 animate-spin" /> : <Circle className="w-4 h-4" />}
                  <span className="font-semibold">Passo {n}:</span> {run ? st.titulo : ok ? (st?.titulo || label) : label}
                </li>
              ); })}
            </ol>
            {result && (
              <div data-testid="test-split" className="rounded-2xl bg-purple-50 p-4 text-sm space-y-1 fade-up">
                <p className="font-semibold text-slate-900 mb-2">💰 Split de {eur(result.valor)} · cupão <span className="font-coupon text-purple-700">{result.cupom}</span></p>
                {[["Restaurante", result.split.restaurante, "75%"], ["Influencer", result.split.influencer, "5%"], ["RR CLUB", result.split.rrclub, "10%"], ["Stripe", result.split.stripe, "10%"]].map(([k, v, p]) => (
                  <div key={k} className="flex justify-between"><span className="text-slate-600">{k}</span><span className="font-mono"><b className="text-slate-900">{eur(v)}</b> <span className="text-slate-400 text-xs">({p})</span></span></div>
                ))}
              </div>
            )}
            {result && (
              <div className="grid grid-cols-2 gap-2">
                <button data-testid="test-view-dashboard" onClick={() => onOpenChange(false)} className="py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-purple-50 text-slate-700 text-xs font-semibold btn-press inline-flex items-center justify-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" /> Ver dashboard</button>
                <button data-testid="test-clear-run" onClick={clear} className="py-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold btn-press inline-flex items-center justify-center gap-1.5"><Trash2 className="w-3.5 h-3.5" /> Limpar este teste</button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
