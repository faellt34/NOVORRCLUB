import { useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dashboardMoney as money } from "../lib/api";
import { Activity } from "lucide-react";

const fmtDay = (d) => `${d.slice(8, 10)}/${d.slice(5, 7)}`;
const RANGES = [["7", "7 dias"], ["30", "30 dias"]];

export const RevenueClicksChart = ({ series = [] }) => {
  const [range, setRange] = useState("30");
  const data = series.slice(-Number(range)).map((p) => ({ ...p, dia: fmtDay(p.date) }));
  return (
    <div className="card-soft p-5" data-testid="revenue-clicks-chart">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center"><Activity className="w-4 h-4" /></span>
        <div><h3 className="text-lg font-semibold text-slate-900 leading-tight">Receita e cliques</h3><p className="text-xs text-slate-500">Evolução diária dos principais indicadores</p></div>
        <div className="ml-auto inline-flex rounded-xl bg-slate-100 p-1">
          {RANGES.map(([k, l]) => <button key={k} data-testid={`chart-range-${k}`} onClick={() => setRange(k)} className={`px-3 py-1 rounded-lg text-xs font-semibold ${range === k ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500"}`}>{l}</button>)}
        </div>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-slate-500 mb-2 justify-end">
        <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-indigo-600" /> Receita</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-sky-400" /> Cliques</span>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <defs>
              <linearGradient id="gRec" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2864F3" stopOpacity={0.35} /><stop offset="100%" stopColor="#2864F3" stopOpacity={0} /></linearGradient>
              <linearGradient id="gClk" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#67D2ED" stopOpacity={0.3} /><stop offset="100%" stopColor="#67D2ED" stopOpacity={0} /></linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F6" vertical={false} />
            <XAxis dataKey="dia" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis yAxisId="l" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} tickFormatter={(v) => money(v)} />
            <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} formatter={(v, n) => [n === "receita" ? money(v) : v, n === "receita" ? "Receita" : "Cliques"]} />
            <Area yAxisId="l" type="monotone" dataKey="receita" stroke="#2864F3" strokeWidth={2.5} fill="url(#gRec)" dot={false} activeDot={{ r: 4 }} />
            <Area yAxisId="r" type="monotone" dataKey="cliques" stroke="#67D2ED" strokeWidth={2} fill="url(#gClk)" dot={false} activeDot={{ r: 4 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
