import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, Ticket, Users, Euro, Percent, Search, Copy, Download, Share2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { useApp } from "../context/AppContext";
import { api, apiError, eur, num } from "../lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";
import { PageSkeleton } from "../components/PageSkeleton";

export default function InfluencerDashboard() {
  const { user, unread } = useApp();
  const [period, setPeriod] = useState("30");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("todas");
  const [data, setData] = useState(null);

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
  const link = featured ? `${window.location.origin}/c/${featured.cupom}` : "";

  const share = (action) => {
    if (action === "copiar") { navigator.clipboard?.writeText(link).catch(() => {}); toast.success("Link copiado para a área de transferência"); }
    else if (action === "download") {
      const svg = document.querySelector("[data-testid=qr-code-featured-card] svg");
      if (!svg) return;
      const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `qr-${featured.cupom}.svg`; a.click();
      toast.success("QR Code descarregado");
    } else window.open(`https://wa.me/?text=${encodeURIComponent(`${featured.desconto}% OFF em ${featured.parceiro} com o meu cupão ${featured.cupom}: ${link}`)}`, "_blank");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h1 data-testid="influencer-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Olá, {user.nome.split(" ")[0]}! 👋</h1>
          <p className="text-sm text-slate-500 mt-1">Painel de desempenho e atribuição das suas parcerias de luxo</p>
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

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard id="cupons-utilizados" icon={Ticket} label="Cupons Utilizados" value={num(kpis.uses)} trend={kpis.trend.uses} />
        <KpiCard id="clientes-impactados" icon={Users} label="Clientes que receberam cupom" value={num(kpis.customers)} trend={kpis.trend.customers} period={kpis.conversion != null ? `conversão em compra: ${String(kpis.conversion).replace(".", ",")}%` : "abriram o link/QR do cupom"} />
        <KpiCard id="receita-gerada" icon={Euro} label="Receita Gerada" value={eur(Math.round(kpis.revenue))} trend={kpis.trend.revenue} />
        <KpiCard id="sua-comissao" icon={Percent} label={`Sua Comissão (~${kpis.rate}%)`} value={eur(Math.round(kpis.commission))} trend={kpis.trend.commission} />
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
                  <th className="pb-3 font-semibold">Status</th>
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
                    <td className="py-3"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400" data-testid="campaigns-empty-state">Nenhuma campanha encontrada.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
