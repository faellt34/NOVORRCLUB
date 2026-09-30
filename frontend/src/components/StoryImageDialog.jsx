import { useState } from "react";
import { Image as ImageIcon, Download, Loader2, RefreshCw, Share2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const STYLES = [["luxo", "Luxo"], ["fresco", "Fresco"], ["noite", "Noite"]];

export const StoryImageDialog = ({ campaign: c, open, onOpenChange }) => {
  const [estilo, setEstilo] = useState("luxo");
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState(null);

  const generate = async () => {
    setBusy(true);
    try {
      const r = await api.post("/influencer/ai/story-image", { campaign_id: c.id, estilo }, { responseType: "blob", timeout: 120000 });
      if (url) URL.revokeObjectURL(url);
      setUrl(URL.createObjectURL(r.data));
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const download = () => { const a = document.createElement("a"); a.href = url; a.download = `story-${c.cupom}.png`; a.click(); toast.success("Imagem guardada"); };
  const share = async () => {
    try {
      const blob = await (await fetch(url)).blob();
      const file = new File([blob], `story-${c.cupom}.png`, { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file], title: `Cupão ${c.cupom}` }); else download();
    } catch (e) { if (e?.name !== "AbortError") download(); }
  };

  if (!c) return null;
  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o && url) { URL.revokeObjectURL(url); setUrl(null); } }}>
      <DialogContent data-testid="story-image-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ImageIcon className="w-4 h-4 text-purple-600" /> Imagem de story IA · {c.cupom}</DialogTitle>
          <DialogDescription>{c.parceiro} · {c.desconto}% OFF — gerada pelo Gemini (Nano Banana), formato 9:16</DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-flex rounded-xl bg-slate-100 p-1" data-testid="story-style">
            {STYLES.map(([k, l]) => <button key={k} data-testid={`story-style-${k}`} onClick={() => setEstilo(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${estilo === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500"}`}>{l}</button>)}
          </div>
          <button data-testid="story-generate" disabled={busy} onClick={generate} className="ml-auto inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-xs font-semibold btn-press">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : url ? <RefreshCw className="w-4 h-4" /> : <ImageIcon className="w-4 h-4" />} {busy ? "A criar imagem (≈15s)..." : url ? "Gerar outra" : "Gerar imagem"}
          </button>
        </div>
        {busy && !url && <div className="aspect-[9/16] max-h-[360px] mx-auto w-[200px] rounded-2xl bg-gradient-to-b from-purple-100 to-slate-100 animate-pulse" data-testid="story-skeleton" />}
        {url && (
          <div className="space-y-3 fade-up">
            <img data-testid="story-image" src={url} alt={`Story ${c.cupom}`} className="mx-auto max-h-[420px] rounded-2xl shadow-xl border border-purple-100" />
            <div className="grid grid-cols-2 gap-2">
              <button data-testid="story-download" onClick={download} className="py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press"><Download className="w-3.5 h-3.5" /> Guardar PNG</button>
              <button data-testid="story-share" onClick={share} className="py-2.5 rounded-xl bg-gradient-to-r from-[#5B21B6] to-[#08061A] hover:opacity-90 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press"><Share2 className="w-3.5 h-3.5" /> Partilhar</button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
