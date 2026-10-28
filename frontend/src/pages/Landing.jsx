import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { QrCode, ScanLine, Percent, Wallet, ArrowRight, Store, Megaphone, Users, ShieldCheck, Smartphone } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";

const STEPS = [
  { icon: QrCode, title: "Seguidor abre o cupão", text: "Clica no link do influenciador e recebe um QR pessoal com desconto." },
  { icon: ScanLine, title: "Parceiro lê o QR", text: "No balcão, o parceiro lê o QR e introduz o valor da conta." },
  { icon: Percent, title: "5% de desconto automático", text: "O seguidor paga por MB WAY, Apple Pay, cartão ou Pix (Brasil)." },
  { icon: Wallet, title: "Repartição automática", text: "80% parceiro · 5% influenciador · 10% RRClub. Sem faturas manuais." },
];

const fmt = (v, cur) => new Intl.NumberFormat(cur === "BRL" ? "pt-BR" : "pt-PT", { style: "currency", currency: cur }).format(v);

const Simulator = () => {
  const [ticket, setTicket] = useState(40);
  const [clients, setClients] = useState(60);
  const [cur, setCur] = useState("EUR");
  const r = useMemo(() => {
    const gross = ticket * clients;
    return { gross, partner: gross * 0.8, influencer: gross * 0.05, follower: gross * 0.05, club: gross * 0.1 };
  }, [ticket, clients]);
  return (
    <div data-testid="landing-simulator" className="rounded-3xl bg-slate-900 text-white p-6 sm:p-8 space-y-6 shadow-2xl">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-lg sm:text-xl font-bold">Simule a sua receita mensal</h3>
        <select data-testid="landing-sim-currency" value={cur} onChange={(e) => setCur(e.target.value)} className="bg-white/10 rounded-lg text-xs px-2 py-1.5">
          <option value="EUR" className="text-slate-900">EUR · Portugal</option>
          <option value="BRL" className="text-slate-900">BRL · Brasil</option>
        </select>
      </div>
      <label className="block space-y-2">
        <span className="flex justify-between text-sm text-white/70"><span>Ticket médio</span><b className="text-white">{fmt(ticket, cur)}</b></span>
        <input data-testid="landing-sim-ticket" type="range" min="5" max="300" step="5" value={ticket} onChange={(e) => setTicket(+e.target.value)} className="w-full accent-violet-400" />
      </label>
      <label className="block space-y-2">
        <span className="flex justify-between text-sm text-white/70"><span>Clientes trazidos por influenciadores / mês</span><b className="text-white">{clients}</b></span>
        <input data-testid="landing-sim-clients" type="range" min="5" max="500" step="5" value={clients} onChange={(e) => setClients(+e.target.value)} className="w-full accent-violet-400" />
      </label>
      <div className="grid grid-cols-2 gap-3">
        {[["Parceiro recebe", r.partner, "80%", "landing-sim-partner"], ["Influenciador ganha", r.influencer, "5%", "landing-sim-influencer"], ["Seguidores poupam", r.follower, "5%", "landing-sim-follower"], ["Volume gerado", r.gross, "100%", "landing-sim-gross"]].map(([l, v, p, id]) => (
          <div key={l} className="rounded-2xl bg-white/5 border border-white/10 p-3">
            <p className="text-[11px] uppercase tracking-wider text-white/50">{l} · {p}</p>
            <p data-testid={id} className="font-display text-lg sm:text-2xl font-bold tabular-nums">{fmt(v, cur)}</p>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-white/50">Simulação ilustrativa. Valores reais dependem das compras pagas através do cupão.</p>
    </div>
  );
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#F8F9FC] text-slate-900 overflow-x-clip">
      <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" aria-label="R-Conekta"><BrandLogo dark /></Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link to="/login" data-testid="landing-login" className="px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100">Entrar</Link>
            <Link to="/registar" data-testid="landing-register" className="px-3 py-2 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800">Criar conta</Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-4 pt-12 pb-10 grid lg:grid-cols-2 gap-10 items-center">
        <div className="space-y-6">
          <span className="inline-flex items-center gap-2 text-xs font-semibold text-violet-700 bg-violet-50 rounded-full px-3 py-1"><Smartphone className="w-3.5 h-3.5" /> Portugal · Brasil · pagamentos reais</span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.05]">Influenciadores trazem clientes. <span className="text-violet-700">Toda a gente ganha.</span></h1>
          <p className="text-base sm:text-lg text-slate-600 max-w-xl">A R-Conekta liga restaurantes, hotéis e lojas a criadores de conteúdo com um cupão QR, desconto de 5% para quem compra e repartição automática do pagamento — sem folhas de cálculo nem faturas manuais.</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link to="/registar?tipo=parceiro" data-testid="landing-cta-partner" className="inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl bg-violet-700 text-white font-semibold hover:bg-violet-800 btn-press"><Store className="w-4 h-4" /> Sou parceiro</Link>
            <Link to="/registar?tipo=influencer" data-testid="landing-cta-influencer" className="inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl bg-white border border-slate-200 font-semibold hover:bg-slate-50 btn-press"><Megaphone className="w-4 h-4" /> Sou influenciador</Link>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-emerald-600" /> Pagamentos via Stripe</span>
            <span className="inline-flex items-center gap-1.5"><Users className="w-4 h-4 text-violet-600" /> Seguidor · Parceiro · Influenciador</span>
          </div>
        </div>
        <Simulator />
      </section>

      <section className="max-w-6xl mx-auto px-4 py-12">
        <h2 className="font-display text-base md:text-lg font-bold uppercase tracking-wider text-slate-500 mb-6">Como funciona (P5)</h2>
        <ol className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((s, i) => (
            <li key={s.title} data-testid={`landing-step-${i + 1}`} className="rounded-2xl bg-white border border-slate-100 p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="w-10 h-10 rounded-xl bg-violet-50 text-violet-700 flex items-center justify-center"><s.icon className="w-5 h-5" /></span>
                <span className="font-coupon text-xs text-slate-400">0{i + 1}</span>
              </div>
              <p className="font-semibold">{s.title}</p>
              <p className="text-sm text-slate-600">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="max-w-6xl mx-auto px-4 pb-16">
        <div className="rounded-3xl bg-white border border-slate-100 p-6 sm:p-10 grid md:grid-cols-3 gap-6">
          {[["Parceiros", "Mais clientes sem custo fixo. Só paga 20% sobre as compras que realmente aconteceram, já com o desconto do cliente incluído."],
            ["Influenciadores", "Cupão próprio, extrato em tempo real e 5% de cada compra transferido para a sua conta Stripe."],
            ["Seguidores", "5% de desconto imediato, pagamento no telemóvel e recibo digital."]].map(([t, d]) => (
            <div key={t} className="space-y-2">
              <p className="font-display font-bold text-lg">{t}</p>
              <p className="text-sm text-slate-600">{d}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <p>© {new Date().getFullYear()} R-Conekta by RRClub · <Link to="/privacidade" className="underline">Privacidade</Link></p>
          <Link to="/registar" data-testid="landing-cta-bottom" className="inline-flex items-center gap-2 font-semibold text-violet-700">Começar agora <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </section>
    </div>
  );
}
