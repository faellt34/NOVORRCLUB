import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Crown, Eye, EyeOff, LogIn, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { apiError } from "../lib/api";
import { Input } from "../components/ui/input";

const ROLE_HOME = { influencer: "/influencer", partner: "/parceiro", admin: "/admin" };

const DEMO = [
  { label: "Admin", email: "admin@robson.club", password: "admin123" },
  { label: "Influencer", email: "robson@robson.club", password: "robson123" },
  { label: "Parceiro", email: "gerencia@tivolisky.pt", password: "tivoli123" },
];

export default function Login() {
  const { login } = useApp();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e, creds) => {
    e?.preventDefault();
    const em = creds?.email ?? email, pw = creds?.password ?? password;
    if (!em.trim() || !pw) { setError("Preencha email e palavra-passe."); return; }
    setLoading(true); setError("");
    try {
      const u = await login(em.trim(), pw);
      toast.success(`Bem-vindo, ${u.nome.split(" ")[0]}!`);
      navigate(ROLE_HOME[u.role] || "/");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F8F9FC]">
      <div className="hidden lg:flex flex-col justify-between p-12 bg-[#0C0A14] text-white relative overflow-hidden">
        <div className="absolute -top-32 -left-32 w-[480px] h-[480px] rounded-full bg-purple-700/30 blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[380px] h-[380px] rounded-full bg-purple-500/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-6 h-6" /></div>
          <div>
            <p className="font-display font-bold text-xl leading-tight">Robson Club</p>
            <p className="text-[11px] uppercase tracking-widest text-purple-300/80">Luxury Experiences</p>
          </div>
        </div>
        <div className="relative max-w-md">
          <p className="text-purple-300 text-sm font-semibold uppercase tracking-widest mb-4 flex items-center gap-2"><Sparkles className="w-4 h-4" /> Plataforma de parcerias</p>
          <h1 className="font-display text-4xl xl:text-5xl font-extrabold leading-[1.1] mb-6">Influência que se converte em receita mensurável.</h1>
          <p className="text-slate-400 leading-relaxed">Cupões, QR codes, validação em loja e comissões travadas por redenção — tudo com audit log server-side.</p>
        </div>
        <p className="relative text-xs text-slate-500">© 2026 Robson Club · Lisboa · Porto · Algarve · Douro · Internacional</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-5 h-5 text-white" /></div>
            <p className="font-display font-bold text-lg">Robson Club</p>
          </div>
          <h2 data-testid="login-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Entrar na sua área</h2>
          <p className="text-sm text-slate-500 mt-1 mb-8">Aceda ao painel de Influencer, Parceiro ou Admin.</p>

          <form onSubmit={submit} className="space-y-4" data-testid="login-form">
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">Email</label>
              <Input data-testid="login-email-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@robson.club" className="h-11 rounded-xl bg-white" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">Palavra-passe</label>
              <div className="relative">
                <Input data-testid="login-password-input" type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="h-11 rounded-xl bg-white pr-11" />
                <button type="button" data-testid="toggle-password-visibility" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {error && <p data-testid="login-error" className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
            <button type="submit" disabled={loading} data-testid="login-submit-button" className="w-full h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press">
              <LogIn className="w-4 h-4" /> {loading ? "A entrar..." : "Entrar"}
            </button>
          </form>

          <div className="mt-8 p-4 rounded-2xl bg-white border border-slate-200">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Contas de demonstração</p>
            <div className="grid grid-cols-3 gap-2">
              {DEMO.map((d) => (
                <button key={d.label} type="button" data-testid={`demo-login-${d.label.toLowerCase()}`} onClick={(e) => submit(e, d)} className="py-2 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold btn-press">
                  {d.label}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-3">Clique para preencher e entrar automaticamente.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
