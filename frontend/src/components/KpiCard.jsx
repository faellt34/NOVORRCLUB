import { TrendingUp, TrendingDown, MoreHorizontal } from "lucide-react";
import { useCountUp } from "../services/live";

const Spark = ({ seed, negative }) => {
  const pts = Array.from({ length: 12 }, (_, i) => 18 - ((Math.sin(seed * 0.37 + i * 1.3) + 1) * 5 + i * (negative ? -0.6 : 0.9)));
  const d = pts.map((y, i) => `${i === 0 ? "M" : "L"}${i * 6},${y.toFixed(1)}`).join(" ");
  const c = negative ? "#ef4444" : "#4F46E5";
  return (
    <svg viewBox="0 0 66 24" className="w-20 h-7" aria-hidden>
      <path d={`${d} L66,24 L0,24 Z`} fill={c} opacity="0.12" />
      <path d={d} fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
};

export const KpiCard = ({ id, icon: Icon, label, value, trend, period = "vs. últimos 30 dias", live, format, flash }) => {
  const negative = trend?.startsWith("-");
  const isLive = typeof live === "number";
  const [animated, updating] = useCountUp(isLive ? live : 0);
  const shown = isLive ? (format ? format(animated) : Math.round(animated)) : value;
  const seed = String(id).split("").reduce((a, ch) => a + ch.charCodeAt(0), 0);
  return (
    <div data-testid={`kpi-${id}`} className={`card-soft p-4 fade-up stat ${flash ? "live-updated" : ""}`} data-live={isLive ? "true" : undefined}>
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center"><Icon className="w-[18px] h-[18px]" /></div>
        <MoreHorizontal className="w-4 h-4 text-slate-300" />
      </div>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <div className="flex items-end justify-between gap-2 mt-1">
        <div className="min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <p data-testid={`kpi-${id}-value`} className={`stat-val font-display text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 ${updating ? "updating" : ""}`}>{shown}</p>
            {trend && <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${negative ? "text-red-500" : "text-emerald-600"}`}>{negative ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}{trend}</span>}
          </div>
          <p className="text-[10px] text-slate-400 mt-0.5">{period}</p>
        </div>
        <Spark seed={seed} negative={negative} />
      </div>
    </div>
  );
};

export const StatusBadge = ({ status }) => {
  const styles = {
    Ativa: "bg-emerald-50 text-emerald-600",
    Pausada: "bg-amber-50 text-amber-600",
    Expirada: "bg-slate-100 text-slate-500",
  };
  return (
    <span data-testid={`status-badge-${status.toLowerCase()}`} className={`text-xs font-medium px-2.5 py-1 rounded-full ${styles[status] || styles.Expirada}`}>
      {status}
    </span>
  );
};
