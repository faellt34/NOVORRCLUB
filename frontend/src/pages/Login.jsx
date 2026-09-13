import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Crown, Eye, EyeOff, LogIn, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { useT } from "../context/I18nContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { GlobeCanvas } from "../components/GlobeCanvas";
import { api, apiError } from "../lib/api";
import { Input } from "../components/ui/input";

const ROLE_HOME = { influencer: "/influencer", partner: "/parceiro", admin: "/admin" };


export default function Login() {
  const { login } = useApp();
  const { t } = useT();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cities, setCities] = useState([]);
  useEffect(() => { api.get("/public/cities").then((r) => setCities(r.data)).catch(() => {}); }, []);

  const submit = async (e, creds) => {
    e?.preventDefault();
    const em = creds?.email ?? email, pw = creds?.password ?? password;
    if (!em.trim() || !pw) { setError("Preencha email e palavra-passe."); return; }
    setLoading(true); setError("");
    try {
      const u = await login(em.trim(), pw);
      toast.success(`${t("welcome")}, ${u.nome.split(" ")[0]}!`);
      navigate(ROLE_HOME[u.role] || "/");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F8F9FC]">
      <div className="hidden lg:flex flex-col justify-between p-12 bg-[#5B21B6] text-white relative overflow-hidden" data-testid="login-hero">
        <GlobeCanvas cities={cities} />
        <div className="relative flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-6 h-6" /></div>
          <div>
            <p className="font-display font-bold text-xl leading-tight">ןןClub</p>
            <p className="text-[11px] uppercase tracking-widest text-purple-200/80">Luxury Experiences</p>
          </div>
        </div>
        <div className="relative max-w-md">
          <p className="text-purple-200 text-sm font-semibold uppercase tracking-widest mb-4 flex items-center gap-2 font-coupon"><Sparkles className="w-4 h-4" /> {t("heroTag")}</p>
          <h1 className="font-display text-4xl xl:text-5xl font-extrabold leading-[1.1] mb-6">{t("heroTitle")}</h1>
          <p className="text-purple-100/90 leading-relaxed">{t("heroText")}</p>
          {cities.length > 0 && <p data-testid="hero-cities" className="mt-4 text-xs text-amber-300/90 font-semibold uppercase tracking-widest">● {cities.map((c) => c.name).join(" · ")}</p>}
        </div>
        <div className="relative flex items-center justify-between"><p className="text-xs text-purple-200/70">© 2026 ןןClub · Lisboa · Porto · Algarve · Douro · Internacional</p><Link to="/privacidade" data-testid="login-privacy-link" className="text-xs text-slate-400 hover:text-white">{t("privacy")}</Link></div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="flex justify-end mb-4"><LanguageSwitcher /></div>
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-5 h-5 text-white" /></div>
            <p className="font-display font-bold text-lg">ןןClub</p>
          </div>
          <h2 data-testid="login-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{t("loginTitle")}</h2>
          <p className="text-sm text-slate-500 mt-1 mb-8">{t("loginSub")}</p>

          <form onSubmit={submit} className="space-y-4" data-testid="login-form">
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">{t("email")}</label>
              <Input data-testid="login-email-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@theclub.pt" className="h-11 rounded-xl bg-white" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">{t("password")}</label>
              <div className="relative">
                <Input data-testid="login-password-input" type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="h-11 rounded-xl bg-white pr-11" />
                <button type="button" data-testid="toggle-password-visibility" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {error && <p data-testid="login-error" className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
            <div className="flex justify-end">
              <Link to="/esqueci-password" data-testid="forgot-password-link" className="text-xs font-semibold text-purple-700 hover:underline">{t("forgot")}</Link>
            </div>
            <button type="submit" disabled={loading} data-testid="login-submit-button" className="w-full h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press">
              <LogIn className="w-4 h-4" /> {loading ? t("entering") : t("enter")}
            </button>
          </form>

          <div className="mt-8 p-4 rounded-2xl bg-white border border-slate-200">
            <p className="text-sm text-slate-600 text-center">Ainda não tem conta? <Link to="/registar" data-testid="register-link" className="font-semibold text-purple-700 hover:underline">Criar conta</Link></p>
          </div>

        </div>
      </div>
    </div>
  );
}
