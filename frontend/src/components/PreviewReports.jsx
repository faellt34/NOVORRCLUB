import React, { useMemo, useState } from "react";
import { ArrowDownToLine, FileText, Search, ShieldCheck } from "lucide-react";

const safeCell = v => '"' + String(v ?? "").replace(/"/g,'""').replace(/^[=+@-]/, "'$&") + '"';
const roleLabels = { admin:"Admin", partner:"Parceiro", influencer:"Influenciador", follower:"Seguidor" };
const statusNames = { Validado: "QR validado", "Checkout simulado": "Checkout demo", Demonstração:"Demonstração", Pendente:"Pendente" };

export default function PreviewReports({ events = [], country = "PT" }) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [onlyState, setOnlyState] = useState("all");
  const [visible, setVisible] = useState(10);
  const filtered = useMemo(() => events.filter(event => {
    const role = filter === "all" || event.role === filter;
    const status = onlyState === "all" || event.status === onlyState;
    const search = (event.label + " " + event.status + " " + (roleLabels[event.role]||event.role)).toLowerCase().includes(query.trim().toLowerCase());
    return role && status && search;
  }).slice().reverse(), [events,filter,onlyState,query]);
  const statusOptions = [...new Set(events.map(e=>e.status))];
  const exportFile = () => {
    const rows = [["ID","Perfil","Evento","Estado","Mercado","Origem"],...filtered.map(e=>[e.id,roleLabels[e.role]||e.role,e.label,e.status,country,"SIMULACAO LOCAL"])].map(row=>row.map(safeCell).join(";")).join("\r\n");
    const blob = new Blob(["\uFEFF"+rows],{type:"text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob);const a=document.createElement("a");
    a.href=url;a.download="rrclub-preview-relatorio-filtrado.csv";a.click();URL.revokeObjectURL(url);
  };
  const selectClass = "rounded-xl border border-[#DCE6EE] bg-white px-3 py-2.5 text-sm text-[#203047] min-h-11";
  return <section className="rounded-2xl bg-white p-4 sm:p-6 border border-[#DCE6EE] shadow-sm" aria-label="Relatórios demonstrativos">
    <div className="flex flex-wrap justify-between gap-3 mb-5">
      <div><p className="uppercase text-[11px] font-bold tracking-widest text-[#477FAE]">Relatórios · Dados de demonstração</p>
        <h2 className="text-xl font-extrabold mt-1 text-[#203047]">Histórico da operação</h2>
        <p className="text-xs text-slate-500 mt-1">Filtros e exportações funcionam apenas para os eventos desta sessão.</p>
      </div>
      <button type="button" onClick={exportFile} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#B7CCE0] text-sm font-bold text-[#203047] min-h-11">
        <ArrowDownToLine size={17}/> Exportar CSV filtrado
      </button>
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
      <label className="text-xs font-semibold text-slate-600">Perfil
        <select value={filter} onChange={e=>{setFilter(e.target.value);setVisible(10);}} className={"block w-full mt-1 "+selectClass}>
          <option value="all">Todos os perfis</option>
          <option value="admin">Admin</option><option value="influencer">Influenciador</option><option value="partner">Parceiro</option><option value="follower">Seguidor</option>
        </select>
      </label>
      <label className="text-xs font-semibold text-slate-600">Estado
        <select value={onlyState} onChange={e=>{setOnlyState(e.target.value);setVisible(10);}} className={"block w-full mt-1 "+selectClass}>
          <option value="all">Todos os estados</option>{statusOptions.map(s=><option value={s} key={s}>{statusNames[s]||s}</option>)}
        </select>
      </label>
      <label className="text-xs font-semibold text-slate-600">Procurar evento
        <div className="relative mt-1"><Search size={16} className="absolute left-3 top-3.5 text-slate-400"/>
          <input className={selectClass+" w-full pl-9"} value={query} onChange={e=>{setQuery(e.target.value);setVisible(10);}} placeholder="QR, campanha, pagamento..."/>
        </div>
      </label>
    </div>
    <div className="text-xs text-slate-500 flex items-center gap-2 mb-3"><ShieldCheck size={14}/> {filtered.length} evento(s) encontrados · Nenhum pagamento real apresentado</div>
    <div className="overflow-x-auto border border-slate-100 rounded-xl">
      <table className="min-w-[590px] w-full text-sm text-left">
        <thead className="bg-[#F4F7FB] text-[#51667B] text-xs uppercase tracking-wide"><tr>
          <th scope="col" className="px-4 py-3">Evento</th><th scope="col" className="px-4 py-3">Perfil</th><th scope="col" className="px-4 py-3">Estado</th><th scope="col" className="px-4 py-3">Mercado</th>
        </tr></thead>
        <tbody>{filtered.slice(0,visible).map(e=><tr key={e.id} className="border-t border-slate-100 align-top">
          <td className="px-4 py-3"><strong className="text-[#203047] font-semibold">{e.label}</strong><p className="text-xs text-slate-400 mt-1">#{e.id} · origem: demo local</p></td>
          <td className="px-4 py-3 text-slate-600">{roleLabels[e.role]||e.role}</td>
          <td className="px-4 py-3"><span className="inline-block rounded-full bg-[#E8F2FA] text-[#315F83] px-2.5 py-1 text-xs font-semibold">{statusNames[e.status]||e.status}</span></td>
          <td className="px-4 py-3 text-slate-600">{country}</td>
        </tr>)}
        {filtered.length===0&&<tr><td className="px-4 py-8 text-center text-slate-500" colSpan={4}>Nenhum evento para estes filtros.</td></tr>}
        </tbody>
      </table>
    </div>
    {filtered.length>visible&&<button onClick={()=>setVisible(x=>x+10)} className="text-sm font-semibold text-[#477FAE] mt-4 border rounded-xl px-4 py-2">Mostrar mais eventos</button>}
    <div className="mt-4 text-xs text-slate-500 flex items-center gap-2"><FileText size={14}/> O relatório não contém dados pessoais, transações bancárias ou informação da produção.</div>
  </section>;
}
