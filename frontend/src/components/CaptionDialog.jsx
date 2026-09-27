import { useState } from "react";
import { Sparkles, Copy, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const LANGS = [["pt", "🇵🇹 Português"], ["en", "🇬🇧 English"], ["es", "🇪🇸 Español"]];
const TONES = [["elegante", "Elegante"], ["divertido", "Divertido"], ["urgente", "Urgente"]];

export const CaptionDialog = ({ campaign: c, open, onOpenChange }) => {
  const [tom, setTom] = useState("elegante");
  const [lang, setLang] = useState("pt");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);

  const generate = async () => {
    setBusy(true); setData(null);
    try { const r = await api.post("/influencer/ai/captions", { campaign_id: c.id, tom }, { timeout: 90000 }); setData(r.data); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const copy = (t) => { navigator.clipboard?.writeText(t).catch(() => {}); toast.success("Legenda copiada — cole no seu story"); };

  if (!c) return null;
  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setData(null); }}>
      <DialogContent data-testid="caption-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-purple-600" /> Legendas IA para {c.cupom}</DialogTitle>
          <DialogDescription>{c.parceiro} · {c.desconto}% OFF — geradas por Claude em PT / EN / ES</DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-flex rounded-xl bg-slate-100 p-1" data-testid="caption-tone">
            {TONES.map(([k, l]) => <button key={k} data-testid={`caption-tone-${k}`} onClick={() => setTom(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${tom === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500"}`}>{l}</button>)}
          </div>
          <button data-testid="caption-generate" disabled={busy} onClick={generate} className="ml-auto inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-xs font-semibold btn-press">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : data ? <RefreshCw className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />} {busy ? "A escrever..." : data ? "Gerar outras" : "Gerar legendas"}
          </button>
        </div>
        {data && (
          <div className="space-y-3 fade-up">
            <div className="inline-flex rounded-xl bg-slate-100 p-1" data-testid="caption-lang">
              {LANGS.map(([k, l]) => <button key={k} data-testid={`caption-lang-${k}`} onClick={() => setLang(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${lang === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500"}`}>{l}</button>)}
            </div>
            <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
              {(data.captions[lang] || []).map((t, i) => (
                <div key={i} data-testid={`caption-${lang}-${i}`} className="rounded-2xl bg-slate-50 border border-slate-100 p-3 text-sm text-slate-800 whitespace-pre-wrap">
                  {t}
                  <button data-testid={`caption-copy-${lang}-${i}`} onClick={() => copy(`${t}\n${data.link}`)} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:underline"><Copy className="w-3 h-3" /> Copiar com link</button>
                </div>
              ))}
              {!(data.captions[lang] || []).length && <p className="text-xs text-slate-400">Sem legendas neste idioma — gere outras.</p>}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
