import React, { useMemo, useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
import { BarChart3, ChevronRight, CircleCheck, CircleAlert, Copy, Eye, FileChartColumnIncreasing, LayoutDashboard, Megaphone, QrCode, ShieldCheck, Store, Users, Wallet, MousePointerClick } from "lucide-react";
import { DEMO_SOURCE, DEMO_STATUSES, deriveDemoMetrics, initialDemoEvents } from "../lib/previewData";

const PROFILES = [
  { id:"admin", label:"Administrador", Icon:ShieldCheck, description:"Acompanhamento geral e qualidade operacional" },
  { id:"partner", label:"Parceiro", Icon:Store, description:"Validação de QR e acompanhamento de vendas" },
  { id:"influencer", label:"Influenciador", Icon:Megaphone, description:"Campanhas, divulgação e desempenho" }
];
const storageKey = "rrclub_preview_v1_local_events";
function demoEvents() {
  try {
    const arr=JSON.parse(window.sessionStorage.getItem(storageKey) || "null");
    return Array.isArray(arr) && arr.length <= 300 ? arr.filter(e=>e && e.source===DEMO_SOURCE) : initialDemoEvents();
  } catch {return initialDemoEvents();}
}
function Kpi({label,value,Icon,sub}) {
  return <div className="rounded-2xl border border-[#e3e9f2] bg-white px-4 py-5 shadow-sm min-h-[124px]">
    <div className="flex items-center justify-between"><span className="text-xs font-semibold text-[#62748b]">{label}</span><span className="rounded-xl bg-[#edf4fc] p-2 text-[#315f8e]"><Icon size={18}/></span></div>
    <p className="mt-3 text-3xl font-black tracking-tight text-[#182b47]">{value}</p>
    <p className="mt-1 text-xs text-[#728197]">{sub}</p>
  </div>;
}
export default function PreviewApproval() {
  const [role,setRole]=useState("admin");
  const [country,setCountry]=useState("PT");
  const [events]=useState(demoEvents);
  const metrics=useMemo(()=>deriveDemoMetrics(events,country),[events,country]);
  const current=PROFILES.find(p=>p.id===role);
  const coverage=[
    {label:"QR e campanhas",desc:"Revisão de eventos de demonstração e origem",ok:true},
    {label:"Relatórios PT / BR",desc:"Mercados separados com eventos únicos",ok:true},
    {label:"Google SSO real",desc:"Depende de backend de homologação e concessões",ok:false},
    {label:"Pagamento P5 confirmado",desc:"Sem Stripe Test Mode e webhook testado",ok:false}
  ];
  const cards=role==="admin"?[
    ["Campanhas demo",metrics.campaignCount,Megaphone,"Criadas apenas para apresentação"],
    ["QR validados",metrics.scans,QrCode,"Operações únicas nesta sessão"],
    ["Checkouts fictícios",metrics.checkouts,Wallet,"Nunca representam receita"],
    ["Alertas de integridade",metrics.duplicates+metrics.orphan+metrics.invalid,CircleAlert,"Duplicações, órfãos e inválidos"]
  ]:role==="partner"?[
    ["QR validados",metrics.scans,QrCode,"Testes em "+country],
    ["Aguardam checkout",metrics.pending,Users,"Operações sem finalização"],
    ["Checkout fictício",metrics.checkouts,Wallet,"Sem cobranças"],
    ["Recebimentos reais","—",CircleAlert,"Não disponíveis nesta prévia"]
  ]:[
    ["Campanhas demo",metrics.campaignCount,Megaphone,"Criadas para esta demonstração"],
    ["Divulgações",metrics.shares,MousePointerClick,"Ações locais de partilha"],
    ["QR validados",metrics.scans,QrCode,"Interações simuladas"],
    ["Comissão real","—",Wallet,"Sem repasses processados"]
  ];
  const roleTitle=role==="admin"?"Visão geral da plataforma":role==="partner"?"Painel do parceiro":"Painel do influenciador";
  return <main className="min-h-screen bg-[#f5f8fc] text-[#172944]" data-testid="rrclub-approval-preview">
    <div className="bg-[#13233d] text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <BrandLogo size="sm" tagline/>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-bold">
          <span className="rounded-full bg-white/10 border border-white/20 px-3 py-2">Proposta visual V2</span>
          <span className="rounded-full bg-[#436785] px-3 py-2">Só demonstração</span>
        </div>
      </div>
    </div>
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 lg:py-9">
      <div className="flex items-start justify-between flex-wrap gap-3 mb-7">
        <div><a href="#/demo-contas" className="text-sm text-[#406a96] font-bold">← Voltar à central interativa</a><h1 className="text-2xl sm:text-3xl font-black tracking-tight mt-2">Prévia para aprovação</h1>
          <p className="mt-2 max-w-2xl text-sm text-[#63748d]">Visual proposto para os três dashboards, inspirado nas funções existentes da RRClub. Não é uma cópia ligada ao backend oficial.</p></div>
        <span className="rounded-xl px-3 py-2 border border-[#d5e1ef] bg-white text-xs font-bold text-[#406a96]">Sem alteração na produção</span>
      </div>
      <div className="grid lg:grid-cols-[225px_1fr] gap-5">
        <aside className="rounded-[22px] bg-[#192b46] text-white p-4 lg:min-h-[625px] shadow-lg">
          <p className="uppercase tracking-widest text-[11px] text-[#a9c0d9] font-bold px-2 mb-3">Ver como</p>
          <nav className="grid grid-cols-3 lg:grid-cols-1 gap-2" aria-label="Trocar perfil demonstrativo">
            {PROFILES.map(({id,label,Icon})=><button key={id} onClick={()=>setRole(id)} type="button" aria-pressed={role===id} className={"flex flex-col lg:flex-row items-center gap-2.5 rounded-xl p-3 text-xs lg:text-sm font-bold text-left transition-colors "+(role===id?"bg-white text-[#192b46]":"text-[#d1deec] hover:bg-white/10")}>
              <Icon size={18}/><span>{label}</span>{role===id&&<ChevronRight size={16} className="hidden lg:block ml-auto"/>}
            </button>)}
          </nav>
          <div className="mt-7 border-t border-white/15 pt-5 px-2">
            <span className="inline-flex gap-2 items-center text-xs font-semibold text-[#cad8e8]"><Eye size={15}/> Modo de revisão</span>
            <p className="text-xs text-[#a6bdd5] mt-2 leading-relaxed">Os perfis são demonstrativos. Trocar de painel não concede permissões reais.</p>
          </div>
        </aside>
        <section className="min-w-0">
          <div className="rounded-[22px] bg-white border border-[#e3e9f2] px-5 py-5 sm:px-6 flex flex-wrap gap-4 items-center justify-between shadow-sm">
            <div><p className="text-xs uppercase tracking-widest text-[#5c83aa] font-bold">RRClub / {current.label}</p>
              <h2 className="mt-1 text-xl sm:text-2xl font-black">{roleTitle}</h2>
              <p className="text-[#738199] text-xs mt-1">{current.description}</p></div>
            <div className="flex items-center gap-2"><span className="text-xs font-semibold text-[#718198]">Mercado</span>
              <div className="flex rounded-xl bg-[#f0f4fa] p-1 border border-[#e1e7f1]">
                {[["PT","Portugal"],["BR","Brasil"]].map(([id,label])=><button key={id} onClick={()=>setCountry(id)} type="button" className={"rounded-lg px-3 py-2 text-xs font-bold "+(country===id?"bg-white text-[#214970] shadow-sm":"text-[#77859a]")} aria-pressed={country===id}>{label}</button>)}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 my-4">
            {cards.map(([label,value,Icon,sub])=><Kpi key={label} label={label} value={value} Icon={Icon} sub={sub}/>)}
          </div>
          <div className="grid xl:grid-cols-[1.25fr_1fr] gap-4">
            <div className="rounded-[22px] bg-white border border-[#e3e9f2] p-5 sm:p-6 shadow-sm">
              <div className="flex justify-between gap-3"><div><p className="text-[11px] tracking-widest font-bold text-[#6586a4] uppercase">Percurso do cupom</p><h3 className="font-extrabold text-lg mt-1">Funil de acompanhamento</h3></div><BarChart3 size={22} className="text-[#537eaa]"/></div>
              <p className="text-xs mt-1 text-[#738199]">Sem dados reais nem receita contabilizada</p>
              <div className="space-y-5 mt-7">
                {[
                  ["Campanhas",metrics.campaignCount],
                  ["Partilhas",metrics.shares],
                  ["QR validados",metrics.scans],
                  ["Checkout simulado",metrics.checkouts]
                ].map(([label,n])=><div key={label}>
                  <div className="flex justify-between text-xs font-semibold mb-2"><span>{label}</span><span>{n}</span></div>
                  <div className="h-2.5 bg-[#edf3f9] rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-[#8bbbdc] to-[#2c649c] rounded-full" style={{width:Math.max(0,Math.min(100,(n/Math.max(metrics.campaignCount,metrics.shares,metrics.scans,metrics.checkouts,1))*100))+"%"}}/></div>
                </div>)}
              </div>
              <div className="mt-6 bg-[#f4f8fc] rounded-xl p-3 text-xs text-[#61748a]">Acompanhamento demonstrativo por operação. Os valores mudam quando geras eventos fictícios na central interativa.</div>
            </div>
            <div className="rounded-[22px] bg-white border border-[#e3e9f2] p-5 sm:p-6 shadow-sm">
              <p className="text-[11px] tracking-widest font-bold text-[#6586a4] uppercase">Revisão e qualidade</p><h3 className="font-extrabold text-lg mt-1">Estado das integrações</h3>
              <div className="mt-5 space-y-4">{coverage.map(x=><div key={x.label} className="flex gap-3 items-start">
                <span className={"p-2 rounded-lg "+(x.ok?"bg-[#e7f5ef] text-[#2b8565]":"bg-[#fff5e8] text-[#b87b2f]")}>{x.ok?<CircleCheck size={17}/>:<CircleAlert size={17}/>}</span>
                <div><p className="font-bold text-sm">{x.label}</p><p className="text-xs text-[#738199] mt-1">{x.desc}</p></div>
              </div>)}</div>
              <div className="mt-6 border-t border-[#ecf0f5] pt-4 flex items-center justify-between gap-3">
                <div><p className="font-bold text-sm">Base financeira</p><p className="text-xs text-[#738199]">Apenas pagamentos confirmados</p></div><span className="text-xs font-bold rounded-full border px-3 py-1.5 text-[#a8722e] bg-[#fff8eb]">Não ligada</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap justify-between items-center gap-3 mt-5 rounded-2xl bg-[#eaf1f9] border border-[#d5e5f3] px-5 py-4">
            <div><p className="text-sm font-extrabold">Esta versão é para aprovação visual</p><p className="text-xs text-[#5f7790] mt-1">É possível comparar organização, tipografia e hierarquia sem afetar o site oficial.</p></div>
            <a href="#/demo-contas" className="inline-flex items-center gap-2 bg-[#203955] text-white rounded-xl px-4 py-3 text-xs font-bold"><LayoutDashboard size={17}/> Testar funções da prévia</a>
          </div>
        </section>
      </div>
    </div>
  </main>;
}
