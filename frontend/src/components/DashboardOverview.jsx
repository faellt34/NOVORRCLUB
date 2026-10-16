import { ArrowUpRight, ArrowDownRight, Wallet, HandCoins, TrendingUp, Receipt, Users, Store, Ticket, MousePointer2, RefreshCw, CalendarDays, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { dashboardMoney as money, num } from "../lib/api";
import { NetworkMap } from "./NetworkMap";

export default function DashboardOverview({ data, stats, connected, refreshKey, onRefresh }) {
  const metrics = [
    { id:"receita-sistema", label:"Receita atribuída", value:money(stats.receita), trend:data.trend.revenue, icon:Wallet, note:"Valor original das vendas", tone:"blue" },
    { id:"comissoes-agregadas", label:"Comissões geradas", value:money(stats.comissoes), trend:data.trend.commission, icon:HandCoins, note:"Taxas registadas por venda", tone:"cyan" },
    { id:"taxa-conversao", label:"Taxa de conversão", value:`${(stats.cliques ? stats.usos / stats.cliques * 100 : 0).toFixed(1).replace(".",",")}%`, icon:TrendingUp, note:`${num(stats.usos)} vendas / ${num(stats.cliques)} cliques`, tone:"indigo" },
    { id:"ticket-medio", label:"Ticket médio", value:money(stats.usos ? stats.receita / stats.usos : 0), icon:Receipt, note:"Receita atribuída por venda", tone:"slate" },
  ];
  return <>
    <header className="rr-overview-heading"><div><span className="rr-eyebrow">RRCLUB / CENTRO DE OPERAÇÕES</span><h1 data-testid="admin-greeting">Visão geral<span className="rr-title-dot">.</span></h1><p>A influência ganha dimensão. Os resultados ficam à vista.</p></div><div className="rr-heading-actions"><span className="rr-date-label"><CalendarDays size={14}/>Todos os registos</span><button onClick={onRefresh} className="rr-refresh" aria-label="Atualizar dashboard"><RefreshCw size={16}/></button><Link to="/admin/gestao" className="rr-primary-link">Gerir campanhas<ArrowUpRight size={15}/></Link></div></header>
    <div className="rr-metric-grid">{metrics.map(m => <article key={m.id} className={`rr-metric rr-metric-${m.tone}`} data-testid={`kpi-${m.id}`}><div className="rr-metric-top"><span>{m.label}</span><m.icon size={17}/></div><strong>{m.value}</strong><div className="rr-metric-bottom">{m.trend && <span className={`rr-trend ${m.trend.startsWith("-") ? "down" : ""}`}>{m.trend.startsWith("-") ? <ArrowDownRight size={12}/> : <ArrowUpRight size={12}/>}{m.trend}<small>30d vs. anteriores</small></span>}<small>{m.note}</small></div></article>)}</div>
    <div className="rr-network-stats">{[[Users,stats.influencers,"Influencers ativos"],[Store,stats.parceiros,"Parceiros ativos"],[Ticket,stats.campanhas,"Campanhas ativas"],[MousePointer2,stats.cliques,"Cliques registados"]].map(([Icon,value,label]) => <div key={label}><span className="rr-stat-icon"><Icon size={17}/></span><strong>{num(value)}</strong><span>{label}</span></div>)}<Link to="/admin/gestao">Ver a rede<ArrowRight size={14}/></Link></div>
    <NetworkMap refreshKey={refreshKey} connected={connected}/>
  </>;
}
