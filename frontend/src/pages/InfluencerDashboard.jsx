import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, Ticket, Users, Euro, Percent, Search, Copy, Download, Share2, Clapperboard, Landmark, QrCode } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { QRCodeSVG } from "qrcode.react";
import { CouponQrDialog, renderCouponPng } from "../components/CouponQrDialog";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur, num, getSiteUrl, couponLink } from "../lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";
import { PageSkeleton } from "../components/PageSkeleton";
import { useRealtime } from "../services/ws";
import { useFlash } from "../services/live";

export default function InfluencerDashboard() {
  const { user, unread } = useApp();
  const [period, setPeriod] = useState("30");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("todas");
  const [data, setData] = useState(null);
  const [flash, triggerFlash] = useFlash();
  const [live, setLive] = useState(false);
  useRealtime((ev) => {
    if (ev.tipo === "ligado") { setLive(true); return; }
    if (ev.tipo === "desligado") { setLive(false); return; }
    if (ev.tipo === "split_executado") {
      setData((d) => d && { ...d, kpis: { ...d.kpis, uses: d.kpis.uses + 1, revenue: d.kpis.revenue + Number(ev.valor_total || 0), commission: d.kpis.commission + Number(ev.valor_plataforma || 0) },
        campaigns: d.campaigns.map((c) => c.cupom === ev.cupom ? { ...c, uses: c.uses + 1 } : c) });
      triggerFlash("uses"); triggerFlash("revenue"); triggerFlash("commission");
      toast.success(`Venda validada · ${ev.cupom} · +${eur(ev.valor_plataforma)} de comissão`);
    } else if (ev.tipo === "clique_cupao") {
      setData((d) => d && { ...d, kpis: { ...d.kpis, customers: d.kpis.customers + 1 }, campaigns: d.campaigns.map((c) => c.cupom === ev.cupom ? { ...c, claims: (c.claims || 0) + 1 } : c) });
      triggerFlash("customers");
    }
  });
  const [videoBusy, setVideoBusy] = useState(false);
  const [profile, setProfile] = useState(null);
  const [iban, setIban] = useState("");
  const [ibanEdit, setIbanEdit] = useState(false);
  const [qrCampaign, setQrCampaign] = useState(null);
  const [site, setSite] = useState(window.location.origin);
  useEffect(() => { getSiteUrl().then(setSite); }, []);
  useEffect(() => { api.get("/influencer/me").then((r) => setProfile(r.data)).catch(() => {}); }, []);
  const saveIban = async (e) => {
    e.preventDefault();
    try { const { data: res } = await api.post("/influencer/iban", { iban }); setProfile((p) => ({ ...p, iban: res.iban })); setIbanEdit(false); toast.success("IBAN guardado — as comissões serão transferidas para esta conta"); }
    catch (err) { toast.error(apiError(err)); }
  };

  const downloadStory = async () => {
    setVideoBusy(true);
    try {
      const r = await api.get(`/influencer/story-video/${featured.id}`, { responseType: "blob", timeout: 120000 });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = url; a.download = `story-${featured.cupom}.mp4`; a.click(); URL.revokeObjectURL(url);
      toast.success("Vídeo pronto! Partilhe nos seus stories.");
    } catch (e) { toast.error(apiError(e)); } finally { setVideoBusy(false); }
  };

  useEffect(() => {
    setData(null);
    api.get(`/dashboard/influencer?period=${period}`).then((r) => setData(r.data)).catch((e) => toast.error(apiError(e)));
  }, [period]);

  const chart = useMemo(() => (data?.chart || []).map((d) => ({ ...d, label: new Date(d.date).toLocaleDateString("pt-PT", { day: "2-digit", month: "short" }) })), [data]);

  if (!data) return <PageSkeleton />;

  const { kpis, campaigns, topPartners, featured } = data;
  const filtered = campaigns.filter((c) => {
    const matchSearch = `${c.nome} ${c.parceiro} ${c.cupom} ${c.cidade}`.toLowerCase().includes(search.toLowerCase());
    return matchSearch && (statusFilter === "todas" || c.status === statusFilter);
  });
  const link = featured ? couponLink(site, featured.cupom) : "";

  const share = async (action) => {
    if (action === "copiar") { navigator.clipboard?.writeText(link).catch(() => {}); toast.success("Link copiado para a área de transferência"); }
    else if (action === "download") {
      const svg = document.querySelector("[data-testid=qr-code-featured-card] svg");
      if (!svg) return;
      const img = new Image();
      img.onload = async () => {
        const cv = document.createElement("canvas"); cv.width = cv.height = 700; const ctx = cv.getContext("2d");
        ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 700, 700); ctx.drawImage(img, 0, 0, 700, 700);
        const blob = await renderCouponPng(cv, featured, link);
        const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `cupao-${featured.cupom}.png`; a.click();
        toast.success("Imagem do cupão descarregada (PNG)");
      };
      img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(svg))));
    } else {
      const text = `${featured.desconto}% OFF em ${featured.parceiro} com o meu cupão ${featured.cupom}: ${link}`;
      if (navigator.share) { navigator.share({ text, title: `Cupão ${featured.cupom}`, url: link }).catch(() => {}); return; }
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h1 data-testid="influencer-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Olá, {user.nome.split(" ")[0]}! 👋</h1>
          <p className="text-sm text-slate-500 mt-1">Painel de desempenho e atribuição das suas parcerias de luxo {live && <span data-testid="influencer-live-badge" className="ml-2 inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 live-dot" /> ao vivo</span>}</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger data-testid="period-selector" className="w-[160px] bg-white rounded-xl"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Últimos 7 dias</SelectItem>
              <SelectItem value="30">Últimos 30 dias</SelectItem>
              <SelectItem value="90">Últimos 90 dias</SelectItem>
            </SelectContent>
          </Select>
          <Link to="/notificacoes" data-testid="notifications-bell" className="relative w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center hover:bg-purple-50 btn-press">
            <Bell className="w-[18px] h-[18px] text-slate-600" />
            {unread.notifications > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-purple-600 text-white text-[10px] font-bold flex items-center justify-center">{unread.notifications}</span>}
          </Link>
        </div>
      </div>

      <div data-testid="influencer-iban-card" className={`card-soft p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${profile && !profile.iban ? "border-l-4 border-amber-400" : ""}`}>
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center"><Landmark className="w-5 h-5" /></span>
          <div>
            <p className="text-sm font-semibold text-slate-900">IBAN para receber as comissões</p>
            <p className="text-xs text-slate-500">{profile?.iban ? <span className="font-mono" data-testid="influencer-iban-value">{profile.iban.replace(/(.{4})/g, "$1 ").trim()}</span> : "Ainda sem IBAN — adicione a sua conta bancária para receber os pagamentos mensais."}</p>
          </div>
        </div>
        {ibanEdit ? (
          <form onSubmit={saveIban} className="flex gap-2">
            <Input data-testid="influencer-iban-input" value={iban} onChange={(e) => setIban(e.target.value)} placeholder="PT50 0000 0000 0000 0000 0000 0" className="rounded-xl bg-slate-50 font-mono w-[280px]" />
            <button type="submit" data-testid="influencer-iban-save" className="px-3 py-2 rounded-xl bg-purple-600 text-white text-xs font-semibold btn-press">Guardar</button>
          </form>
        ) : (
          <button data-testid="influencer-iban-edit" onClick={() => { setIban(profile?.iban || ""); setIbanEdit(true); }} className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">{profile?.iban ? "Alterar IBAN" : "Adicionar IBAN"}</button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard id="cupons-utilizados" icon={Ticket} label="Cupons Utilizados" live={kpis.uses} format={num} flash={flash.uses} trend={kpis.trend.uses} />
        <KpiCard id="clientes-impactados" icon={Users} label="Clientes que receberam cupom" live={kpis.customers} format={num} flash={flash.customers} trend={kpis.trend.customers} period={kpis.conversion != null ? `conversão em compra: ${String(kpis.conversion).replace(".", ",")}%` : "abriram o link/QR do cupom"} />
        <KpiCard id="receita-gerada" icon={Euro} label="Receita Gerada" live={kpis.revenue} format={(v) => eur(Math.round(v))} flash={flash.revenue} trend={kpis.trend.revenue} />
        <KpiCard id="sua-comissao" icon={Percent} label={`Sua Comissão (~${kpis.rate}%)`} live={kpis.commission} format={(v) => eur(Math.round(v))} flash={flash.commission} trend={kpis.trend.commission} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="usage-chart-card" className="card-soft p-5 xl:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Evolução de Utilizações</h3>
            <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2.5 py-1 rounded-full">{period === "90" ? "3 em 3 dias" : "Diário"}</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chart} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="purpleGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#94A3B8" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} formatter={(v) => [v, "Utilizações"]} />
              <Area type="monotone" dataKey="utilizacoes" stroke="#7C3AED" strokeWidth={2.5} fill="url(#purpleGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div data-testid="featured-coupon-card" className="card-soft p-5 flex flex-col items-center text-center">
          <h3 className="text-lg font-semibold text-slate-900 self-start mb-1">Seu Cupom em Destaque</h3>
          {featured ? (
            <>
              <p className="text-xs text-slate-500 self-start mb-4">{featured.parceiro} · {featured.desconto}% OFF em experiências selecionadas</p>
              <span data-testid="featured-coupon-code" className="font-coupon font-bold tracking-widest text-sm uppercase px-4 py-2 rounded-lg bg-purple-600 text-white mb-4">{featured.cupom}</span>
              <div data-testid="qr-code-featured-card" className="p-3 bg-white rounded-2xl border-2 border-purple-100">
                <QRCodeSVG value={link} size={148} fgColor="#3B0764" />
              </div>
              <div className="grid grid-cols-3 gap-2 w-full mt-4">
                <button data-testid="coupon-copy-link" onClick={() => share("copiar")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press"><Copy className="w-4 h-4" /><span className="text-[10px] font-semibold">Copiar</span></button>
                <button data-testid="coupon-download-qr" onClick={() => share("download")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press"><Download className="w-4 h-4" /><span className="text-[10px] font-semibold">QR</span></button>
                <button data-testid="coupon-share-whatsapp" onClick={() => share("whatsapp")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press"><Share2 className="w-4 h-4" /><span className="text-[10px] font-semibold">Partilhar</span></button>
              </div>
              <button data-testid="coupon-story-video" disabled={videoBusy} onClick={downloadStory} className="w-full mt-2 py-2.5 rounded-xl bg-gradient-to-r from-[#5B21B6] to-[#08061A] hover:opacity-90 disabled:opacity-60 text-white text-xs font-semibold inline-flex items-center justify-center gap-2 btn-press">
                <Clapperboard className="w-4 h-4" /> {videoBusy ? "A gerar o seu vídeo (≈20s)..." : "Vídeo Story personalizado (MP4)"}
              </button>
            </>
          ) : <p className="text-sm text-slate-400 py-10">Sem campanhas ativas.</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="top-partners-card" className="card-soft p-5">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Top Parceiros</h3>
          <div className="space-y-4">
            {topPartners.map((p, i) => (
              <div key={p.id} data-testid={`top-partner-${p.id}`} className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-400 w-4">{i + 1}</span>
                <img src={p.avatar} alt={p.nome} className="w-10 h-10 rounded-full object-cover" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{p.nome}</p>
                  <p className="text-xs text-slate-500">{p.categoria} · {p.cidade}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-900">{eur(Math.round(p.revenue))}</p>
                  <p className="text-xs text-slate-400">{num(p.uses)} utilizações</p>
                </div>
              </div>
            ))}
            {topPartners.length === 0 && <p className="text-sm text-slate-400 py-6 text-center">Sem redenções no período.</p>}
          </div>
        </div>

        <div data-testid="active-campaigns-card" className="card-soft p-5 xl:col-span-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <h3 className="text-lg font-semibold text-slate-900" id="campanhas">Campanhas</h3>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input data-testid="campaign-search-input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Procurar campanha..." className="pl-9 w-[190px] rounded-xl bg-slate-50" />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger data-testid="campaign-status-filter" className="w-[120px] rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todas">Todas</SelectItem>
                  <SelectItem value="Ativa">Ativa</SelectItem>
                  <SelectItem value="Pausada">Pausada</SelectItem>
                  <SelectItem value="Expirada">Expirada</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="overflow-x-auto -mx-5 px-5">
            <table className="w-full text-sm" data-testid="campaigns-table">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                  <th className="pb-3 pr-4 font-semibold">Campanha</th>
                  <th className="pb-3 pr-4 font-semibold">Cupom</th>
                  <th className="pb-3 pr-4 font-semibold">Receberam</th>
                  <th className="pb-3 pr-4 font-semibold">Utilizados</th>
                  <th className="pb-3 pr-4 font-semibold">Comissão</th>
                  <th className="pb-3 pr-4 font-semibold">Validade</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 font-semibold text-right">QR</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} data-testid={`campaign-row-${c.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40 transition-colors">
                    <td className="py-3 pr-4">
                      <p className="font-semibold text-slate-900">{c.nome}</p>
                      <p className="text-xs text-slate-500">{c.parceiro} · {c.cidade}</p>
                    </td>
                    <td className="py-3 pr-4"><span className="font-coupon text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{c.cupom}</span></td>
                    <td className="py-3 pr-4 text-slate-600">{num(c.claims || 0)}</td>
                    <td className="py-3 pr-4 font-semibold text-slate-700">{num(c.uses)}</td>
                    <td className="py-3 pr-4 text-purple-700 font-semibold">{c.comissao}%</td>
                    <td className="py-3 pr-4 text-slate-500">{new Date(c.validade).toLocaleDateString("pt-PT")}</td>
                    <td className="py-3 pr-4"><StatusBadge status={c.status} /></td>
                    <td className="py-3 text-right"><button data-testid={`campaign-qr-${c.id}`} onClick={() => setQrCampaign(c)} title="Ver / descarregar QR" className="p-2 rounded-lg text-purple-600 hover:bg-purple-50 btn-press"><QrCode className="w-4 h-4" /></button></td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="py-8 text-center text-slate-400" data-testid="campaigns-empty-state">Nenhuma campanha encontrada.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <CouponQrDialog campaign={qrCampaign} open={!!qrCampaign} onOpenChange={(o) => !o && setQrCampaign(null)} />
    </div>
  );
}
