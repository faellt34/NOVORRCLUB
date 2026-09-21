import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, LogIn, Sparkles } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";
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
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F8F9FC] relative">
      <div className="lg:hidden absolute inset-0 overflow-hidden" data-testid="login-hero-mobile" style={{ background: "radial-gradient(ellipse 120% 90% at 50% 20%, #5B21B6 0%, #5B21B6 40%, #2A1064 60%, #08061A 80%, #08061A 100%)" }}>
        <GlobeCanvas interactive={false} />
      </div>
      <div className="hidden lg:flex flex-col justify-between p-12 text-white relative overflow-hidden" data-testid="login-hero" style={{ background: "radial-gradient(ellipse 85% 120% at 15% 45%, #5B21B6 0%, #5B21B6 48%, #2A1064 62%, #08061A 78%, #08061A 100%)" }}>
        <div className="absolute inset-0 pointer-events-none" style={{ backgroundImage: "radial-gradient(1.5px 1.5px at 20% 30%, rgba(255,255,255,.9) 50%, transparent 51%), radial-gradient(1px 1px at 70% 20%, rgba(255,255,255,.8) 50%, transparent 51%), radial-gradient(1.5px 1.5px at 85% 55%, rgba(255,255,255,.9) 50%, transparent 51%), radial-gradient(1px 1px at 60% 80%, rgba(255,255,255,.7) 50%, transparent 51%), radial-gradient(1px 1px at 90% 85%, rgba(255,255,255,.8) 50%, transparent 51%), radial-gradient(1.5px 1.5px at 75% 40%, rgba(255,255,255,.9) 50%, transparent 51%), radial-gradient(1px 1px at 40% 10%, rgba(255,255,255,.7) 50%, transparent 51%), radial-gradient(1px 1px at 95% 15%, rgba(255,255,255,.8) 50%, transparent 51%), radial-gradient(1px 1px at 82% 70%, rgba(255,255,255,.6) 50%, transparent 51%), radial-gradient(1.2px 1.2px at 65% 60%, rgba(255,255,255,.8) 50%, transparent 51%)", backgroundSize: "100% 100%", animation: "twinkle 4s ease-in-out infinite alternate" }} />
        <GlobeCanvas interactive={false} />
        <BrandLogo size="lg" tagline className="relative" />
        <div className="relative max-w-md">
          <p className="text-purple-200 text-sm font-semibold uppercase tracking-widest mb-4 flex items-center gap-2 font-coupon"><Sparkles className="w-4 h-4" /> {t("heroTag")}</p>
          <h1 className="font-display text-4xl xl:text-5xl font-extrabold leading-[1.1] mb-6">{t("heroTitle")}</h1>
          <p className="text-purple-100/90 leading-relaxed">{t("heroText")}</p>
        </div>
        <div className="relative flex items-center justify-between"><p className="text-xs text-purple-200/70">© 2026 RRclub · Lisboa · Porto · Algarve · Douro · Internacional</p><Link to="/privacidade" data-testid="login-privacy-link" className="text-xs text-slate-400 hover:text-white">{t("privacy")}</Link></div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12 relative">
        <div className="w-full max-w-md bg-white/85 lg:bg-transparent backdrop-blur-md lg:backdrop-blur-none rounded-3xl lg:rounded-none p-6 lg:p-0 shadow-2xl lg:shadow-none mt-24 lg:mt-0" data-testid="login-panel">
          <div className="flex justify-end mb-4"><LanguageSwitcher /></div>
          <BrandLogo dark className="lg:hidden mb-8" />
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
