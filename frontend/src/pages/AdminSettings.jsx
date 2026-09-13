import { useCallback, useEffect, useState } from "react";
import { Mail, Send, Trash2, ShieldAlert, CheckCircle2, Smartphone, Landmark } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Input } from "../components/ui/input";
import { PageSkeleton } from "../components/PageSkeleton";

export default function AdminSettings() {
  const [s, setS] = useState(null);
  const [key, setKey] = useState("");
  const [sender, setSender] = useState("");
  const [confirm, setConfirm] = useState("");
  const [iban, setIban] = useState("");
  const [titular, setTitular] = useState("");
  const saveIban = async (e) => {
    e.preventDefault(); setBusy("iban");
    try { await api.post("/admin/settings/iban", { iban, titular }); toast.success("IBAN da plataforma guardado"); load(); }
    catch (err) { toast.error(apiError(err)); } finally { setBusy(""); }
  };
  const [busy, setBusy] = useState("");

  const load = useCallback(() => api.get("/admin/settings").then((r) => { setS(r.data); setSender(r.data.sender_email || ""); setIban(r.data.iban || ""); setTitular(r.data.iban_titular || ""); }).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { load(); }, [load]);

  const saveEmail = async (e) => {
    e.preventDefault(); setBusy("email");
    try { await api.post("/admin/settings/email", { resend_api_key: key, sender_email: sender }); toast.success("Definições de email guardadas"); setKey(""); load(); }
    catch (err) { toast.error(apiError(err)); } finally { setBusy(""); }
  };
  const testEmail = async () => {
    setBusy("test");
    try { await api.post("/admin/settings/email/test"); toast.success("Email de teste enviado para o seu endereço"); }
    catch (err) { toast.error(apiError(err)); } finally { setBusy(""); }
  };
  const reset = async () => {
    setBusy("reset");
    try { await api.post("/admin/reset-pilot", { confirm }); toast.success("Dados piloto zerados. A plataforma está limpa para produção."); setConfirm(""); load(); }
    catch (err) { toast.error(apiError(err)); } finally { setBusy(""); }
  };

  if (!s) return <PageSkeleton />;

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="settings-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Definições</h1>
        <p className="text-sm text-slate-500 mt-1">Controle total sem código: email automático, dados piloto e instalação no telemóvel</p>
      </div>

      <form onSubmit={saveIban} className="card-soft p-5 space-y-3" data-testid="settings-iban-card">
        <div className="flex items-center gap-2"><Landmark className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">IBAN da plataforma (conta para receber dinheiro)</h3></div>
        <p className="text-xs text-slate-500">Conta bancária da ןןClub onde recebe as comissões e os pagamentos por QR (quando o Stripe Connect não está ativo). Aparece nos extratos e no rodapé dos recibos para transferências manuais.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div><label className="text-xs font-semibold text-slate-600 mb-1 block">IBAN</label><Input data-testid="settings-iban-input" value={iban} onChange={(e) => setIban(e.target.value)} placeholder="PT50 0000 0000 0000 0000 0000 0" className="rounded-xl bg-slate-50 font-mono" /></div>
          <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Titular</label><Input data-testid="settings-iban-titular" value={titular} onChange={(e) => setTitular(e.target.value)} placeholder="Nome do titular" className="rounded-xl bg-slate-50" /></div>
        </div>
        <button type="submit" disabled={busy === "iban"} data-testid="settings-iban-save" className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">Guardar IBAN</button>
      </form>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <form onSubmit={saveEmail} className="card-soft p-5 space-y-3" data-testid="settings-email-card">
          <div className="flex items-center gap-2"><Mail className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">Email automático (Resend)</h3>
            {s.email_configured ? <span data-testid="email-status-on" className="text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Ativo</span> : <span data-testid="email-status-off" className="text-[11px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Desativado</span>}</div>
          <p className="text-xs text-slate-500">Crie uma conta gratuita em <a href="https://resend.com/api-keys" target="_blank" rel="noreferrer" className="text-purple-700 underline">resend.com</a>, copie a chave (começa por <code>re_</code>) e cole aqui. Para enviar a qualquer destinatário, verifique o seu domínio no Resend e use um remetente desse domínio.</p>
          <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Chave API Resend {s.resend_key_hint && <span className="font-normal text-slate-400">(atual: {s.resend_key_hint})</span>}</label>
            <Input data-testid="settings-resend-key" type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="re_..." className="rounded-xl bg-slate-50" /></div>
          <div><label className="text-xs font-semibold text-slate-600 mb-1 block">Remetente</label>
            <Input data-testid="settings-sender" value={sender} onChange={(e) => setSender(e.target.value)} placeholder="ןןClub <noreply@seudominio.com>" className="rounded-xl bg-slate-50" /></div>
          <div className="flex gap-2">
            <button type="submit" disabled={busy === "email"} data-testid="settings-email-save" className="flex-1 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">Guardar</button>
            <button type="button" disabled={!s.email_configured || busy === "test"} onClick={testEmail} data-testid="settings-email-test" className="px-4 py-2.5 rounded-xl bg-white border border-slate-200 hover:bg-purple-50 disabled:opacity-50 text-slate-700 text-sm font-semibold inline-flex items-center gap-1.5 btn-press"><Send className="w-4 h-4" /> Testar</button>
          </div>
        </form>

        <div className="card-soft p-5 space-y-3" data-testid="settings-pwa-card">
          <div className="flex items-center gap-2"><Smartphone className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">App no telemóvel</h3></div>
          <p className="text-xs text-slate-500 leading-relaxed">A ןןClub instala-se como aplicação (PWA) com ícone no ecrã inicial e acesso rápido ao scanner. Partilhe estas instruções com parceiros e influencers:</p>
          <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
            <li><b>Android (Chrome):</b> abrir o site → menu ⋮ → "Instalar aplicação" (ou o botão "Instalar app" na sidebar).</li>
            <li><b>iPhone (Safari):</b> abrir o site → botão Partilhar → "Adicionar ao ecrã principal".</li>
            <li>Parceiros ficam com o scanner de QR a um toque em <b>Validar Cupom</b>.</li>
          </ul>
          <p className="text-[11px] text-slate-400">Link a partilhar: <span className="font-mono">{window.location.origin}</span></p>
        </div>
      </div>

      {s.reset_allowed && (
      <div className="card-soft p-5 border-l-4 border-red-400" data-testid="settings-reset-card">
        <div className="flex items-center gap-2 mb-2"><ShieldAlert className="w-5 h-5 text-red-500" /><h3 className="text-lg font-semibold text-slate-900">Zerar teste piloto</h3>
          {s.demo_disabled && <span data-testid="pilot-reset-done" className="text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Zerado em {new Date(s.pilot_reset_at).toLocaleString("pt-PT")}</span>}</div>
        <p className="text-xs text-slate-500 mb-3">Apaga TODOS os dados de demonstração e de teste — redenções, campanhas, parceiros, influencers, utilizadores (exceto os admins), mensagens, indicações, pagamentos e audit log. Os e-books mantêm-se. Os dados de demonstração não voltam a ser criados. <b>Irreversível.</b></p>
        <p className="text-xs text-slate-500 mb-3">Atualmente: {s.counts.users} utilizadores · {s.counts.influencers} influencers · {s.counts.partners} parceiros · {s.counts.campaigns} campanhas · {s.counts.redemptions} redenções</p>
        <div className="flex flex-col sm:flex-row gap-2">
          <Input data-testid="reset-confirm-input" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder='Escreva ZERAR para confirmar' className="rounded-xl bg-slate-50 sm:max-w-xs" />
          <button disabled={confirm !== "ZERAR" || busy === "reset"} onClick={reset} data-testid="reset-pilot-button" className="px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-semibold inline-flex items-center justify-center gap-1.5 btn-press"><Trash2 className="w-4 h-4" /> {busy === "reset" ? "A zerar..." : "Zerar dados piloto"}</button>
        </div>
      </div>
      )}
      {!s.reset_allowed && s.demo_disabled && (
        <p data-testid="pilot-reset-info" className="text-xs text-slate-400 flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Teste piloto zerado em {new Date(s.pilot_reset_at).toLocaleString("pt-PT")} — a plataforma está em modo produção.</p>
      )}
    </div>
  );
}
