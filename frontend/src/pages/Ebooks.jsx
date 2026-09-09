import { useCallback, useEffect, useMemo, useState } from "react";
import { Lock, Eye, Crown, BookOpen, Globe, ShoppingCart, Sparkles, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { useT } from "../context/I18nContext";
import { api, apiError, slug, eur } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { PageSkeleton } from "../components/PageSkeleton";
import { PdfReader } from "../components/PdfReader";

const CATEGORIES = ["Todas", "Restaurantes", "Hotéis", "Rooftops", "Passeios"];

export default function Ebooks() {
  const { user } = useApp();
  const { t } = useT();
  const [sub, setSub] = useState(null);
  const [ebooks, setEbooks] = useState(null);
  const [access, setAccess] = useState({ subscribed: false, owned: [], subscription_price: 9.9 });
  const [country, setCountry] = useState("Todos");
  const [region, setRegion] = useState("Todas");
  const [category, setCategory] = useState("Todas");
  const [preview, setPreview] = useState(null);
  const [reader, setReader] = useState(null);
  const [buying, setBuying] = useState(null);

  const load = useCallback(() => Promise.all([api.get("/ebooks"), api.get("/payments/access"), api.get("/payments/subscription")]).then(([e, a, s]) => { setEbooks(e.data); setAccess(a.data); setSub(s.data); }).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { load(); }, [load]);

  const countries = useMemo(() => ["Todos", ...Array.from(new Set((ebooks || []).map((e) => e.pais)))], [ebooks]);
  const regions = useMemo(() => ["Todas", ...Array.from(new Set((ebooks || []).filter((e) => country === "Todos" || e.pais === country).map((e) => e.regiao)))], [ebooks, country]);

  const buy = async (lookup_key) => {
    setBuying(lookup_key);
    try {
      const { data } = await api.post("/payments/checkout", { lookup_key, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) { toast.error(apiError(e)); setBuying(null); }
  };

  const cancelSub = async () => {
    if (!window.confirm("Cancelar a subscrição Premium? Mantém o acesso até ao fim do período já pago.")) return;
    try { const { data } = await api.post("/payments/subscription/cancel"); toast.success(data.ends_at ? `Subscrição cancelada — acesso até ${new Date(data.ends_at).toLocaleDateString("pt-PT")}` : "Subscrição cancelada"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  if (!ebooks) return <PageSkeleton />;

  const filtered = ebooks.filter((e) => (country === "Todos" || e.pais === country) && (region === "Todas" || e.regiao === region) && (category === "Todas" || e.categoria === category));
  const pill = (active, on) => `px-3.5 py-1.5 rounded-full text-xs font-semibold btn-press transition-colors ${active ? on : "bg-white border border-slate-200 text-slate-600 hover:bg-purple-50"}`;

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 data-testid="ebooks-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{t("ebooksTitle")}</h1>
          <p className="text-sm text-slate-500 mt-1">{t("ebooksSub")}</p>
        </div>
        {user.role !== "admin" && (
          access.subscribed ? (
            <div className="flex flex-wrap items-center gap-2">
              <span data-testid="subscription-active-badge" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-50 text-emerald-700 text-xs font-semibold"><CheckCircle2 className="w-4 h-4" /> {t("subActive")}{sub?.cancel_at_period_end && sub?.ends_at ? ` · ${t("subEnds")} ${new Date(sub.ends_at).toLocaleDateString("pt-PT")}` : ""}</span>
              {!sub?.cancel_at_period_end && <button data-testid="cancel-subscription-button" onClick={cancelSub} className="px-3 py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-red-50 hover:text-red-600 text-slate-600 text-xs font-semibold btn-press">{t("cancelSub")}</button>}
            </div>
          ) : (
            <button data-testid="subscribe-button" disabled={!!buying} onClick={() => buy("club_monthly")} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 disabled:opacity-60 text-white text-xs font-semibold btn-press shadow-lg shadow-purple-600/20">
              <Sparkles className="w-4 h-4" /> {t("subscribe")} · {eur(access.subscription_price)}{t("perMonth")}
            </button>
          )
        )}
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Globe className="w-4 h-4 text-slate-400" />
          {countries.map((c) => <button key={c} data-testid={`country-filter-${slug(c)}`} onClick={() => { setCountry(c); setRegion("Todas"); }} className={pill(country === c, "bg-purple-600 text-white")}>{c}</button>)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {regions.map((r) => <button key={r} data-testid={`region-filter-${slug(r)}`} onClick={() => setRegion(r)} className={pill(region === r, "bg-purple-100 text-purple-800 border border-purple-200")}>{r}</button>)}
          <span className="w-px h-5 bg-slate-200 mx-1" />
          {CATEGORIES.map((c) => <button key={c} data-testid={`category-filter-${slug(c)}`} onClick={() => setCategory(c)} className={pill(category === c, "bg-slate-900 text-white")}>{c}</button>)}
        </div>
      </div>

      <div data-testid="ebooks-grid" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {filtered.map((e) => (
          <div key={e.id} data-testid={`ebook-card-${e.id}`} className="card-soft overflow-hidden flex flex-col fade-up">
            <div className="relative h-40">
              <img src={e.capa} alt={e.titulo} className={`w-full h-full object-cover ${e.premium && !e.unlocked ? "blur-[2px] scale-105" : ""}`} />
              <div className="absolute top-3 left-3 flex gap-1.5 flex-wrap">
                <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-white/90 text-slate-700">{e.pais} · {e.regiao}</span>
                <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-white/90 text-slate-700">{e.categoria}</span>
              </div>
              {e.idioma && <span className="absolute bottom-3 right-3 text-[10px] font-bold px-2 py-1 rounded-full bg-slate-900/70 text-white">{e.idioma}</span>}
              {e.premium && !e.unlocked && (
                <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center">
                  <span data-testid={`ebook-premium-badge-${e.id}`} className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-purple-600 px-3 py-1.5 rounded-full"><Crown className="w-3.5 h-3.5" /> Premium</span>
                </div>
              )}
              {e.premium && e.unlocked && <span data-testid={`ebook-owned-badge-${e.id}`} className="absolute bottom-3 left-3 inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-500 text-white"><CheckCircle2 className="w-3 h-3" /> {e.owned ? t("owned") : t("unlocked")}</span>}
            </div>
            <div className="p-4 flex flex-col flex-1">
              <h3 className="text-sm font-bold text-slate-900 mb-1">{e.titulo}</h3>
              <p className="text-xs text-slate-500 leading-relaxed flex-1">{e.descricao}</p>
              <p className="text-[11px] text-slate-400 mt-2 mb-3 flex items-center gap-1"><BookOpen className="w-3 h-3" /> {e.paginas} {t("pages")}{e.premium && e.preco ? ` · ${eur(e.preco)}` : ""}{!e.has_pdf ? ` · ${t("pdfSoon")}` : ""}</p>
              {e.unlocked ? (
                <button data-testid={`ebook-read-${e.id}`} onClick={() => (e.has_pdf ? setReader(e) : setPreview(e))} className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press">
                  {e.has_pdf ? <><BookOpen className="w-3.5 h-3.5" /> {t("readNow")}</> : <><Eye className="w-3.5 h-3.5" /> {t("preview")}</>}
                </button>
              ) : (
                <button data-testid={`ebook-unlock-${e.id}`} disabled={!!buying} onClick={() => buy(`ebook_${e.id}`)} className="w-full py-2 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-60 text-white text-xs font-semibold inline-flex items-center justify-center gap-1.5 btn-press">
                  {buying === `ebook_${e.id}` ? "A abrir pagamento..." : <><ShoppingCart className="w-3.5 h-3.5" /> {t("buyFor")} {eur(e.preco)}</>}
                </button>
              )}
            </div>
          </div>
        ))}
        {filtered.length === 0 && <p data-testid="ebooks-empty-state" className="col-span-full text-center text-slate-400 py-12">{t("noResults")}</p>}
      </div>

      <Dialog open={!!preview} onOpenChange={() => setPreview(null)}>
        <DialogContent data-testid="ebook-preview-modal" className="max-w-lg">
          {preview && (
            <>
              <DialogHeader>
                <DialogTitle>{preview.titulo}</DialogTitle>
                <DialogDescription>{preview.pais} · {preview.regiao} · {preview.categoria}</DialogDescription>
              </DialogHeader>
              <img src={preview.capa} alt={preview.titulo} className="w-full h-44 object-cover rounded-xl" />
              <div className="text-sm text-slate-600 space-y-2">
                <p>{preview.descricao}</p>
                <p className="text-xs text-slate-400 flex items-center gap-1"><Lock className="w-3 h-3" /> O PDF completo deste guia ainda não foi carregado pelo administrador.</p>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <PdfReader ebook={reader} onClose={() => setReader(null)} />
    </div>
  );
}
