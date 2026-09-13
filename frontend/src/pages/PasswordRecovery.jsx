import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Crown, KeyRound, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Input } from "../components/ui/input";

const Shell = ({ title, subtitle, children }) => (
  <div className="min-h-screen bg-[#F8F9FC] flex items-center justify-center p-6">
    <div className="w-full max-w-md">
      <div className="flex items-center gap-2.5 mb-8">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center"><Crown className="w-5 h-5 text-white" /></div>
        <p className="font-display font-bold text-lg">ןןClub</p>
      </div>
      <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">{title}</h2>
      <p className="text-sm text-slate-500 mt-1 mb-8">{subtitle}</p>
      {children}
      <Link to="/login" data-testid="back-to-login" className="mt-6 inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 hover:underline"><ArrowLeft className="w-3.5 h-3.5" /> Voltar ao login</Link>
    </div>
  </div>
);

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try { await api.post("/auth/forgot-password", { email }); setDone(true); }
    catch (err) { toast.error(apiError(err)); } finally { setLoading(false); }
  };

  return (
    <Shell title="Recuperar acesso" subtitle="Indique o seu email. O administrador do ןןClub recebe o pedido e envia-lhe o link de recuperação.">
      {done ? (
        <div data-testid="forgot-success" className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100 text-sm text-emerald-800">Pedido registado. Se o email existir, o administrador irá contactá-lo com o link para definir uma nova palavra-passe (válido 24h).</div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1.5 block">Email</label>
            <Input data-testid="forgot-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@theclub.pt" className="h-11 rounded-xl bg-white" />
          </div>
          <button type="submit" disabled={loading} data-testid="forgot-submit-button" className="w-full h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press"><KeyRound className="w-4 h-4" /> {loading ? "A enviar..." : "Pedir recuperação"}</button>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [info, setInfo] = useState(undefined);
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) { setInfo(null); return; }
    api.get(`/auth/reset-password/${token}`).then((r) => setInfo(r.data)).catch(() => setInfo(null));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (pw.length < 6) { toast.error("A palavra-passe deve ter pelo menos 6 caracteres."); return; }
    if (pw !== pw2) { toast.error("As palavras-passe não coincidem."); return; }
    setLoading(true);
    try { await api.post("/auth/reset-password", { token, password: pw }); toast.success("Palavra-passe redefinida! Entre com a nova palavra-passe."); navigate("/login"); }
    catch (err) { toast.error(apiError(err)); } finally { setLoading(false); }
  };

  return (
    <Shell title="Nova palavra-passe" subtitle={info ? `Olá ${info.nome.split(" ")[0]}, defina a nova palavra-passe para ${info.email}.` : "Defina a sua nova palavra-passe."}>
      {info === undefined ? <p className="text-sm text-slate-400">A validar link...</p>
        : info === null ? <div data-testid="reset-invalid" className="p-4 rounded-2xl bg-red-50 border border-red-100 text-sm text-red-700">Este link é inválido ou expirou. Peça uma nova recuperação.</div>
        : (
          <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">Nova palavra-passe</label>
              <Input data-testid="reset-password-input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} className="h-11 rounded-xl bg-white" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1.5 block">Confirmar palavra-passe</label>
              <Input data-testid="reset-password-confirm-input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} className="h-11 rounded-xl bg-white" />
            </div>
            <button type="submit" disabled={loading} data-testid="reset-submit-button" className="w-full h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">{loading ? "A guardar..." : "Guardar nova palavra-passe"}</button>
          </form>
        )}
    </Shell>
  );
}
