import { useCallback, useEffect, useRef, useState } from "react";
import { Briefcase, Send, Loader2, Check, X, ClipboardList, FileText } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

const SUGGESTIONS = ["Resumo do dashboard", "Pede ao subagente Marketing um plano para aumentar a conversão", "Pede ao subagente Frontend uma auditoria da página pública do cupão", "Pede ao subagente Backend uma revisão de segurança dos pagamentos"];
const TIPO = { criar_campanha: "Campanha", gerar_contrato: "Contrato", enviar_email: "Email", gerar_qr_code: "QR Code", propor_correcao: "Correção de código" };
const fmt = (d) => new Date(d).toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export default function Diretor() {
  const [msgs, setMsgs] = useState([]);
  const [acoes, setAcoes] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("pendente");
  const box = useRef(null);

  const load = useCallback(() => Promise.all([api.get("/diretor/conversas"), api.get("/diretor/acoes")]).then(([c, a]) => { setMsgs(c.data); setAcoes(a.data); }).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q) => {
    const mensagem = (q ?? input).trim();
    if (!mensagem || busy) return;
    setInput(""); setBusy(true);
    try {
      const { data } = await api.post("/diretor/conversar", { mensagem }, { timeout: 120000 });
      setMsgs((m) => [...m, data]);
      if (data.acoes_pendentes?.length) { toast.info(`${data.acoes_pendentes.length} ação(ões) aguardam a sua aprovação`); setAcoes((a) => [...data.acoes_pendentes, ...a]); setTab("pendente"); }
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const decide = async (id, op) => {
    try { const { data } = await api.post(`/diretor/acoes/${id}/${op}`); toast.success(op === "aprovar" ? `Ação executada${data.resultado?.cupom ? ` · cupão ${data.resultado.cupom}` : ""}` : "Ação rejeitada"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const shown = acoes.filter((a) => a.status === tab);
  return (
    <div className="space-y-6" data-testid="diretor-page">
      <div>
        <h1 data-testid="diretor-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Diretor Geral · IA</h1>
        <p className="text-sm text-slate-500 mt-1">Gemini 2.5 Flash com acesso aos dados reais. Ações que alteram dados só executam após a sua aprovação.</p>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 card-soft p-5 flex flex-col min-h-[560px]" data-testid="diretor-chat">
          <div className="flex items-center gap-2 mb-3"><span className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#B47BFF] to-[#6E2BFF] text-white flex items-center justify-center"><Briefcase className="w-4 h-4" /></span><h3 className="text-lg font-semibold text-slate-900">Conversa com o Diretor</h3></div>
          <div ref={box} data-testid="diretor-messages" className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[520px]">
            {msgs.length === 0 && <div className="flex flex-wrap gap-2">{SUGGESTIONS.map((s) => <button key={s} data-testid="diretor-suggestion" onClick={() => send(s)} className="text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-full btn-press">{s}</button>)}</div>}
            {msgs.map((m) => (
              <div key={m.id} className="space-y-2">
                <div data-testid="diretor-msg-user" className="ml-auto max-w-[85%] rounded-2xl px-4 py-2.5 bg-purple-600 text-white text-sm whitespace-pre-wrap">{m.mensagem_user}</div>
                <div data-testid="diretor-msg-diretor" className="max-w-[92%] rounded-2xl px-4 py-2.5 bg-slate-50 border border-slate-100 text-sm text-slate-800 whitespace-pre-wrap">
                  {m.resposta_diretor}
                  {m.chamadas?.filter((c) => c.resumo).map((c, i) => (
                    <details key={i} data-testid={`diretor-subagente-${c.funcao}`} className="mt-2 rounded-xl bg-white border border-purple-100 p-2">
                      <summary className="text-[11px] font-semibold text-purple-700 cursor-pointer">🧩 {c.funcao.replace("subagente_", "Subagente ")}{c.args?.ficheiro ? ` · ${c.args.ficheiro}` : ""}</summary>
                      <p className="mt-1 text-xs text-slate-600 whitespace-pre-wrap">{c.resumo}</p>
                    </details>
                  ))}
                  {(m.chamadas?.length > 0 || m.acoes_ids?.length > 0) && <p className="mt-2 text-[10px] uppercase tracking-wider text-slate-400">{m.chamadas?.map((c) => c.funcao).join(" · ")}{m.acoes_ids?.length ? ` · ${m.acoes_ids.length} ação pendente` : ""} · {fmt(m.timestamp)}</p>}
                </div>
              </div>
            ))}
            {busy && <div className="rounded-2xl px-4 py-2.5 bg-slate-50 border border-slate-100 w-fit" data-testid="diretor-thinking"><Loader2 className="w-4 h-4 animate-spin text-purple-500" /></div>}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-3 flex gap-2">
            <input data-testid="diretor-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ex.: Analisa o Hotel X e propõe uma campanha para outubro" className="flex-1 rounded-xl bg-slate-50 border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300" />
            <button data-testid="diretor-send" type="submit" disabled={busy || !input.trim()} className="px-3 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white btn-press">{busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}</button>
          </form>
        </div>

        <div className="card-soft p-5" data-testid="acoes-panel">
          <div className="flex items-center gap-2 mb-3"><ClipboardList className="w-5 h-5 text-purple-600" /><h3 className="text-lg font-semibold text-slate-900">Ações Pendentes</h3>
            <span data-testid="acoes-pendentes-count" className="ml-auto text-[10px] font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full">{acoes.filter((a) => a.status === "pendente").length}</span></div>
          <div className="inline-flex rounded-xl bg-slate-100 p-1 mb-3">
            {[["pendente", "Pendentes"], ["aprovada", "Aprovadas"], ["rejeitada", "Rejeitadas"]].map(([k, l]) => <button key={k} data-testid={`acoes-tab-${k}`} onClick={() => setTab(k)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${tab === k ? "bg-white text-purple-700 shadow-sm" : "text-slate-500"}`}>{l}</button>)}
          </div>
          <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
            {shown.length === 0 && <p data-testid="acoes-empty" className="text-sm text-slate-400 py-8 text-center">Sem ações {tab === "pendente" ? "pendentes" : tab + "s"}.</p>}
            {shown.map((a) => (
              <div key={a.id} data-testid={`acao-${a.id}`} className="rounded-2xl border border-slate-100 bg-slate-50 p-3 space-y-2 fade-up">
                <div className="flex items-center gap-2"><span className="text-[10px] font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-md">{TIPO[a.tipo_acao] || a.tipo_acao}</span><span className="ml-auto text-[10px] text-slate-400">{fmt(a.timestamp)}</span></div>
                <p className="text-sm font-semibold text-slate-900">{a.descricao}</p>
                {a.tipo_acao === "propor_correcao" && a.dados_json?.diff && <pre data-testid={`acao-diff-${a.id}`} className="text-[11px] text-emerald-300 bg-slate-900 rounded-lg p-2 overflow-x-auto max-h-40 whitespace-pre">{a.dados_json.diff}</pre>}
                <pre className="text-[11px] text-slate-500 bg-white rounded-lg p-2 overflow-x-auto max-h-28">{JSON.stringify(a.tipo_acao === "propor_correcao" ? { area: a.dados_json?.area, ficheiro: a.dados_json?.ficheiro } : a.dados_json, null, 1)}</pre>
                {a.status === "pendente" ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button data-testid={`acao-aprovar-${a.id}`} onClick={() => decide(a.id, "aprovar")} className="py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold inline-flex items-center justify-center gap-1 btn-press"><Check className="w-3.5 h-3.5" /> Aprovar</button>
                    <button data-testid={`acao-rejeitar-${a.id}`} onClick={() => decide(a.id, "rejeitar")} className="py-2 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold inline-flex items-center justify-center gap-1 btn-press"><X className="w-3.5 h-3.5" /> Rejeitar</button>
                  </div>
                ) : a.resultado && <p className="text-[11px] text-emerald-700 inline-flex items-center gap-1"><FileText className="w-3 h-3" /> {JSON.stringify(a.resultado)}</p>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
