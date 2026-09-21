import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Crown, UserPlus, ArrowLeft, Store, CheckCircle2 } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { api, apiError, setToken } from "../lib/api";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

const CITIES = ["Lisboa", "Porto", "Algarve", "Douro", "Madrid", "Barcelona", "Paris", "Roma", "Dubai", "Outra"];
const INITIAL = { role: "influencer", nome: "", email: "", password: "", handle: "", cidade: "Lisboa", categoria: "Restaurante", telefone: "", aceita_termos: false };

export default function Register() {
  const { refreshUser } = useApp();
  const navigate = useNavigate();
  const [f, setF] = useState(INITIAL);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(null);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e }));

  const submit = async (e) => {
    e.preventDefault();
    if (!f.aceita_termos) { toast.error("Aceite a Política de Privacidade para continuar."); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", f);
      if (data.pending) { setPending(data.message); return; }
      setToken(data.token);
      await refreshUser();
      toast.success(`Bem-vindo, ${data.user.nome.split(" ")[0]}! A sua conta está ativa.`);
      navigate("/influencer");
    } catch (err) { toast.error(apiError(err)); } finally { setLoading(false); }
  };

  const RoleBtn = ({ value, icon: Icon, label, desc }) => (
    <button type="button" data-testid={`register-role-${value}`} onClick={() => setF((p) => ({ ...p, role: value }))}
      className={`p-4 rounded-2xl border text-left transition-colors ${f.role === value ? "border-purple-500 bg-purple-50" : "border-slate-200 bg-white hover:bg-slate-50"}`}>
      <Icon className={`w-5 h-5 mb-2 ${f.role === value ? "text-purple-600" : "text-slate-400"}`} />
      <p className="text-sm font-semibold text-slate-900">{label}</p>
      <p className="text-[11px] text-slate-500 leading-snug">{desc}</p>
    </button>
  );

  return (
    <div className="min-h-screen bg-[#F8F9FC] flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <BrandLogo dark className="mb-8" />
        {pending ? (
          <div className="card-soft p-8 text-center" data-testid="register-pending">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Pedido recebido</h2>
            <p className="text-sm text-slate-500 mb-6">{pending}</p>
            <Link to="/login" data-testid="register-pending-login" className="inline-flex px-5 py-2.5 rounded-xl bg-purple-600 text-white text-sm font-semibold btn-press">Voltar ao login</Link>
          </div>
        ) : (
          <>
            <h2 data-testid="register-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Criar conta</h2>
            <p className="text-sm text-slate-500 mt-1 mb-6">Influencers entram de imediato. Parceiros são verificados pela equipa antes da ativação.</p>
            <form onSubmit={submit} className="space-y-4" data-testid="register-form">
              <div className="grid grid-cols-2 gap-3">
                <RoleBtn value="influencer" icon={Crown} label="Sou Influencer" desc="Promovo experiências e ganho comissões por cupom." />
                <RoleBtn value="partner" icon={Store} label="Sou Parceiro" desc="Tenho um espaço e quero receber clientes." />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 mb-1.5 block">{f.role === "partner" ? "Nome do espaço" : "Nome completo"}</label>
                <Input data-testid="register-nome-input" value={f.nome} onChange={set("nome")} className="h-11 rounded-xl bg-white" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Email</label><Input data-testid="register-email-input" type="email" value={f.email} onChange={set("email")} className="h-11 rounded-xl bg-white" /></div>
                <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Palavra-passe (mín. 6)</label><Input data-testid="register-password-input" type="password" value={f.password} onChange={set("password")} className="h-11 rounded-xl bg-white" /></div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {f.role === "influencer" ? (
                  <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Handle Instagram/TikTok</label><Input data-testid="register-handle-input" value={f.handle} onChange={set("handle")} placeholder="@o.seu.perfil" className="h-11 rounded-xl bg-white" /></div>
                ) : (
                  <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Categoria</label>
                    <Select value={f.categoria} onValueChange={set("categoria")}><SelectTrigger data-testid="register-categoria-select" className="h-11 rounded-xl bg-white"><SelectValue /></SelectTrigger>
                      <SelectContent>{["Restaurante", "Hotel", "Rooftop", "Passeio"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select></div>
                )}
                <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Cidade</label>
                  <Select value={f.cidade} onValueChange={set("cidade")}><SelectTrigger data-testid="register-cidade-select" className="h-11 rounded-xl bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>{CITIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select></div>
              </div>
              <div><label className="text-xs font-semibold text-slate-600 mb-1.5 block">Telefone / WhatsApp (opcional)</label><Input data-testid="register-telefone-input" value={f.telefone} onChange={set("telefone")} className="h-11 rounded-xl bg-white" /></div>
              <label className="flex items-start gap-2 text-xs text-slate-600">
                <input type="checkbox" data-testid="register-terms-checkbox" checked={f.aceita_termos} onChange={set("aceita_termos")} className="mt-0.5 accent-purple-600" />
                <span>Li e aceito a <Link to="/privacidade" className="text-purple-700 underline" target="_blank">Política de Privacidade</Link> e o tratamento dos meus dados para funcionamento da plataforma.</span>
              </label>
              <button type="submit" disabled={loading} data-testid="register-submit-button" className="w-full h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press"><UserPlus className="w-4 h-4" /> {loading ? "A criar conta..." : "Criar conta"}</button>
            </form>
            <Link to="/login" data-testid="register-back-login" className="mt-6 inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 hover:underline"><ArrowLeft className="w-3.5 h-3.5" /> Já tenho conta</Link>
          </>
        )}
      </div>
    </div>
  );
}
