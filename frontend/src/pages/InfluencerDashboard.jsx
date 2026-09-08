import { useMemo, useState } from "react";
import { Bell, Ticket, Users, Euro, Percent, Search, Copy, Download, Share2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { KpiCard, StatusBadge } from "../components/KpiCard";
import { CAMPAIGNS, PARTNERS, CHART_DATA, FEATURED_COUPON, eur, num } from "../lib/mockData";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";

const PERIOD_FACTOR = { "7": 0.24, "30": 1, "90": 2.7 };

export default function InfluencerDashboard() {
  const [period, setPeriod] = useState("30");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("todas");

  const f = PERIOD_FACTOR[period];
  const kpis = useMemo(() => [
    { id: "cupons-utilizados", icon: Ticket, label: "Cupons Utilizados", value: num(Math.round(1284 * f)), trend: "+18,4%" },
    { id: "clientes-impactados", icon: Users, label: "Clientes Impactados", value: num(Math.round(8420 * f)), trend: "+12,1%" },
    { id: "receita-gerada", icon: Euro, label: "Receita Gerada", value: eur(Math.round(84350 * f)), trend: "+24,8%" },
    { id: "sua-comissao", icon: Percent, label: "Sua Comissão (10%)", value: eur(Math.round(8435 * f)), trend: "+24,8%" },
  ], [f]);

  const filtered = CAMPAIGNS.filter((c) => {
    const matchSearch = `${c.name} ${c.partner} ${c.coupon} ${c.city}`.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "todas" || c.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const share = (action) => {
    if (action === "copiar") {
      navigator.clipboard?.writeText(FEATURED_COUPON.link).catch(() => {});
      toast.success("Link copiado para a área de transferência");
    } else if (action === "download") {
      toast.success("QR Code descarregado (simulado)");
    } else {
      toast.success("A abrir partilha no WhatsApp (simulado)");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h1 data-testid="influencer-greeting" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Olá, Robson! 👋</h1>
          <p className="text-sm text-slate-500 mt-1">Painel de desempenho e atribuição das suas parcerias de luxo</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger data-testid="period-selector" className="w-[160px] bg-white rounded-xl">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Últimos 7 dias</SelectItem>
              <SelectItem value="30">Últimos 30 dias</SelectItem>
              <SelectItem value="90">Últimos 90 dias</SelectItem>
            </SelectContent>
          </Select>
          <button data-testid="notifications-bell" onClick={() => toast.info("3 notificações novas")} className="relative w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center hover:bg-purple-50 btn-press">
            <Bell className="w-[18px] h-[18px] text-slate-600" />
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-purple-600 text-white text-[10px] font-bold flex items-center justify-center">3</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {kpis.map((k) => <KpiCard key={k.id} {...k} />)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="usage-chart-card" className="card-soft p-5 xl:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Evolução de Utilizações</h3>
            <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2.5 py-1 rounded-full">Diário</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={CHART_DATA[period]} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="purpleGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#94A3B8" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} formatter={(v) => [v, "Utilizações"]} />
              <Area type="monotone" dataKey="utilizacoes" stroke="#7C3AED" strokeWidth={2.5} fill="url(#purpleGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div data-testid="featured-coupon-card" className="card-soft p-5 flex flex-col items-center text-center">
          <h3 className="text-lg font-semibold text-slate-900 self-start mb-1">Seu Cupom em Destaque</h3>
          <p className="text-xs text-slate-500 self-start mb-4">{FEATURED_COUPON.partner} · {FEATURED_COUPON.discount}</p>
          <span data-testid="featured-coupon-code" className="font-coupon font-bold tracking-widest text-sm uppercase px-4 py-2 rounded-lg bg-purple-600 text-white mb-4">
            {FEATURED_COUPON.code}
          </span>
          <div data-testid="qr-code-featured-card" className="p-3 bg-white rounded-2xl border-2 border-purple-100">
            <QRCodeSVG value={FEATURED_COUPON.link} size={148} fgColor="#3B0764" />
          </div>
          <div className="grid grid-cols-3 gap-2 w-full mt-4">
            <button data-testid="coupon-copy-link" onClick={() => share("copiar")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press">
              <Copy className="w-4 h-4" /><span className="text-[10px] font-semibold">Copiar</span>
            </button>
            <button data-testid="coupon-download-qr" onClick={() => share("download")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press">
              <Download className="w-4 h-4" /><span className="text-[10px] font-semibold">QR</span>
            </button>
            <button data-testid="coupon-share-whatsapp" onClick={() => share("whatsapp")} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 btn-press">
              <Share2 className="w-4 h-4" /><span className="text-[10px] font-semibold">Partilhar</span>
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div data-testid="top-partners-card" className="card-soft p-5">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Top Parceiros</h3>
          <div className="space-y-4">
            {PARTNERS.map((p, i) => (
              <div key={p.id} data-testid={`top-partner-${p.id}`} className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-400 w-4">{i + 1}</span>
                <img src={p.avatar} alt={p.name} className="w-10 h-10 rounded-full object-cover" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{p.name}</p>
                  <p className="text-xs text-slate-500">{p.category} · {p.city}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-900">{eur(p.revenue)}</p>
                  <p className="text-xs text-slate-400">{num(p.uses)} utilizações</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div data-testid="active-campaigns-card" className="card-soft p-5 xl:col-span-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <h3 className="text-lg font-semibold text-slate-900" id="campanhas">Campanhas Ativas</h3>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input data-testid="campaign-search-input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Procurar campanha..." className="pl-9 w-[190px] rounded-xl bg-slate-50" />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger data-testid="campaign-status-filter" className="w-[120px] rounded-xl bg-slate-50">
                  <SelectValue />
                </SelectTrigger>
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
                  <th className="pb-3 pr-4 font-semibold">Utilizados</th>
                  <th className="pb-3 pr-4 font-semibold">Validade</th>
                  <th className="pb-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} data-testid={`campaign-row-${c.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40 transition-colors">
                    <td className="py-3 pr-4">
                      <p className="font-semibold text-slate-900">{c.name}</p>
                      <p className="text-xs text-slate-500">{c.partner} · {c.city}</p>
                    </td>
                    <td className="py-3 pr-4"><span className="font-coupon text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{c.coupon}</span></td>
                    <td className="py-3 pr-4 font-semibold text-slate-700">{num(c.uses)}</td>
                    <td className="py-3 pr-4 text-slate-500">{new Date(c.validUntil).toLocaleDateString("pt-PT")}</td>
                    <td className="py-3"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-400" data-testid="campaigns-empty-state">Nenhuma campanha encontrada.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
