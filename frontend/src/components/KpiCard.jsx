import { TrendingUp, TrendingDown } from "lucide-react";
import { useCountUp } from "../services/live";

export const KpiCard = ({ id, icon: Icon, label, value, trend, period = "vs período anterior", live, format, flash }) => {
  const negative = trend?.startsWith("-");
  const isLive = typeof live === "number";
  const [animated, updating] = useCountUp(isLive ? live : 0);
  const shown = isLive ? (format ? format(animated) : Math.round(animated)) : value;
  return (
    <div data-testid={`kpi-${id}`} className={`card-soft p-5 fade-up stat ${flash ? "live-updated" : ""}`} data-live={isLive ? "true" : undefined}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-11 h-11 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
          <Icon className="w-5 h-5" />
        </div>
        {trend && (
          <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md ${negative ? "text-red-500 bg-red-50" : "text-emerald-600 bg-emerald-50"}`}>
            {negative ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
            {trend}
          </span>
        )}
      </div>
      <p data-testid={`kpi-${id}-value`} className={`stat-val font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 ${updating ? "updating" : ""}`}>{shown}</p>
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mt-1">{label}</p>
      {trend && <p className="text-[11px] text-slate-400 mt-0.5">{period}</p>}
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
