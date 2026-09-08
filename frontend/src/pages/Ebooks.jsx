import { useEffect, useMemo, useState } from "react";
import { Lock, Eye, Crown, BookOpen, Globe } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, slug, eur } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { PageSkeleton } from "../components/PageSkeleton";

const CATEGORIES = ["Todas", "Restaurantes", "Hotéis", "Rooftops", "Passeios"];

export default function Ebooks() {
  const [ebooks, setEbooks] = useState(null);
  const [country, setCountry] = useState("Todos");
  const [region, setRegion] = useState("Todas");
  const [category, setCategory] = useState("Todas");
  const [preview, setPreview] = useState(null);

  useEffect(() => { api.get("/ebooks").then((r) => setEbooks(r.data)).catch((e) => toast.error(apiError(e))); }, []);

  const countries = useMemo(() => ["Todos", ...Array.from(new Set((ebooks || []).map((e) => e.pais)))], [ebooks]);
  const regions = useMemo(() => ["Todas", ...Array.from(new Set((ebooks || []).filter((e) => country === "Todos" || e.pais === country).map((e) => e.regiao)))], [ebooks, country]);

  if (!ebooks) return <PageSkeleton />;

  const filtered = ebooks.filter((e) => (country === "Todos" || e.pais === country) && (region === "Todas" || e.regiao === region) && (category === "Todas" || e.categoria === category));

  const pill = (active, on) => `px-3.5 py-1.5 rounded-full text-xs font-semibold btn-press transition-colors ${active ? on : "bg-white border border-slate-200 text-slate-600 hover:bg-purple-50"}`;

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="ebooks-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">E-books & Guias Premium</h1>
        <p className="text-sm text-slate-500 mt-1">Guias curados de experiências de luxo em Portugal e no mundo — preview público e conteúdo premium bloqueado</p>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Globe className="w-4 h-4 text-slate-400" />
          {countries.map((c) => (
            <button key={c} data-testid={`country-filter-${slug(c)}`} onClick={() => { setCountry(c); setRegion("Todas"); }} className={pill(country === c, "bg-purple-600 text-white")}>{c}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {regions.map((r) => (
            <button key={r} data-testid={`region-filter-${slug(r)}`} onClick={() => setRegion(r)} className={pill(region === r, "bg-purple-100 text-purple-800 border border-purple-200")}>{r}</button>
          ))}
          <span className="w-px h-5 bg-slate-200 mx-1" />
          {CATEGORIES.map((c) => (
            <button key={c} data-testid={`category-filter-${slug(c)}`} onClick={() => setCategory(c)} className={pill(category === c, "bg-slate-900 text-white")}>{c}</button>
          ))}
        </div>
      </div>

      <div data-testid="ebooks-grid" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {filtered.map((e) => (
          <div key={e.id} data-testid={`ebook-card-${e.id}`} className="card-soft overflow-hidden flex flex-col fade-up">
            <div className="relative h-40">
              <img src={e.capa} alt={e.titulo} className={`w-full h-full object-cover ${e.premium ? "blur-[2px] scale-105" : ""}`} />
              <div className="absolute top-3 left-3 flex gap-1.5 flex-wrap">
                <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-white/90 text-slate-700">{e.pais} · {e.regiao}</span>
                <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-white/90 text-slate-700">{e.categoria}</span>
              </div>
              {e.idioma && <span className="absolute bottom-3 right-3 text-[10px] font-bold px-2 py-1 rounded-full bg-slate-900/70 text-white">{e.idioma}</span>}
              {e.premium && (
                <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center">
                  <span data-testid={`ebook-premium-badge-${e.id}`} className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-purple-600 px-3 py-1.5 rounded-full"><Crown className="w-3.5 h-3.5" /> Premium</span>
                </div>
              )}
            </div>
            <div className="p-4 flex flex-col flex-1">
              <h3 className="text-sm font-bold text-slate-900 mb-1">{e.titulo}</h3>
              <p className="text-xs text-slate-500 leading-relaxed flex-1">{e.descricao}</p>
              <p className="text-[11px] text-slate-400 mt-2 mb-3 flex items-center gap-1"><BookOpen className="w-3 h-3" /> {e.paginas} páginas{e.premium && e.preco ? ` · ${eur(e.preco)}` : ""}</p>
              {e.premium ? (
                <button data-testid={`ebook-unlock-${e.id}`} onClick={() => toast.info("Conteúdo premium — disponível em breve na subscrição do Robson Club")} className="w-full py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press"><Lock className="w-3.5 h-3.5" /> Desbloquear Premium</button>
              ) : (
                <button data-testid={`ebook-preview-${e.id}`} onClick={() => setPreview(e)} className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press"><Eye className="w-3.5 h-3.5" /> Pré-visualizar</button>
              )}
            </div>
          </div>
        ))}
        {filtered.length === 0 && <p data-testid="ebooks-empty-state" className="col-span-full text-center text-slate-400 py-12">Nenhum guia encontrado para estes filtros.</p>}
      </div>

      <Dialog open={!!preview} onOpenChange={() => setPreview(null)}>
        <DialogContent data-testid="ebook-preview-modal" className="max-w-lg">
          {preview && (
            <>
              <DialogHeader>
                <DialogTitle>{preview.titulo}</DialogTitle>
                <DialogDescription>{preview.pais} · {preview.regiao} · {preview.categoria} · preview público</DialogDescription>
              </DialogHeader>
              <img src={preview.capa} alt={preview.titulo} className="w-full h-44 object-cover rounded-xl" />
              <div className="text-sm text-slate-600 space-y-2">
                <p>{preview.descricao}</p>
                <p className="text-xs text-slate-400">Preview público: as primeiras 5 de {preview.paginas} páginas estão disponíveis gratuitamente. O guia completo requer subscrição premium.</p>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
