import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { getToken } from "../lib/api";

const API = process.env.REACT_APP_BACKEND_URL;
const SUGGESTIONS = ["Resumo da semana em 3 frases", "Porque é que a conversão está baixa?", "Qual o influencer com melhor retorno?", "Que origem traz mais clientes?"];

export const AiAnalyst = ({ refreshKey }) => {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState(() => sessionStorage.getItem("rr_ai_session") || null);
  const box = useRef(null);
  const abortRef = useRef(null);
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" }); }, [msgs]);

  const ask = async (q) => {
    const question = (q ?? input).trim();
    if (!question || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    try {
      abortRef.current = new AbortController();
      const res = await fetch(`${API}/api/admin/ai/ask`, { method: "POST", signal: abortRef.current.signal, headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` }, body: JSON.stringify({ session_id: session, message: question }) });
      if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || `Erro ${res.status}`);
      const reader = res.body.getReader(), dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n"); buf = parts.pop();
        for (const p of parts) {
          const ev = (p.match(/^event: (\w+)/m) || [])[1] || "message";
          const data = (p.match(/^data: (.*)$/m) || [])[1];
          if (data == null) continue;
          if (ev === "meta") { const s = JSON.parse(data).session_id; setSession(s); sessionStorage.setItem("rr_ai_session", s); }
          else if (ev === "error") toast.error(`IA: ${JSON.parse(data)}`);
          else if (ev === "message") { const tok = JSON.parse(data); setMsgs((m) => { if (!m.length || m[m.length - 1].role !== "assistant") return m; const c = [...m]; c[c.length - 1] = { ...c[c.length - 1], content: c[c.length - 1].content + tok }; return c; }); }
        }
      }
    } catch (e) { if (e.name !== "AbortError") { toast.error(e.message); setMsgs((m) => (m.length && m[m.length - 1].role === "assistant" && !m[m.length - 1].content ? m.slice(0, -1) : m)); } }
    finally { setBusy(false); abortRef.current = null; }
  };

  const reset = () => { abortRef.current?.abort(); setMsgs([]); setSession(null); sessionStorage.removeItem("rr_ai_session"); };

  return (
    <div data-testid="ai-analyst-card" className="card-soft p-5 flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#B47BFF] to-[#6E2BFF] text-white flex items-center justify-center"><Sparkles className="w-4 h-4" /></span>
        <div><h3 className="text-lg font-semibold text-slate-900">Analista IA</h3><p className="text-xs text-slate-500">Claude Sonnet 4.6 · lê os dados reais dos últimos 30 dias</p></div>
        {msgs.length > 0 && <button data-testid="ai-reset" onClick={reset} title="Nova conversa" className="ml-auto p-2 rounded-lg text-slate-400 hover:text-purple-600 hover:bg-purple-50"><RotateCcw className="w-4 h-4" /></button>}
      </div>
      <div ref={box} data-testid="ai-messages" className="flex-1 min-h-[160px] max-h-[320px] overflow-y-auto space-y-3 pr-1">
        {msgs.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => <button key={s} data-testid="ai-suggestion" onClick={() => ask(s)} className="text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-full btn-press">{s}</button>)}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} data-testid={`ai-msg-${m.role}`} className={`text-sm whitespace-pre-wrap rounded-2xl px-4 py-2.5 max-w-[92%] ${m.role === "user" ? "ml-auto bg-purple-600 text-white" : "bg-slate-50 text-slate-800 border border-slate-100"}`}>
            {m.content || <Loader2 className="w-4 h-4 animate-spin text-purple-500" />}
          </div>
        ))}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); ask(); }} className="mt-3 flex gap-2">
        <input data-testid="ai-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Pergunte sobre vendas, conversão, influencers..." className="flex-1 rounded-xl bg-slate-50 border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-300" />
        <button data-testid="ai-send" type="submit" disabled={busy || !input.trim()} className="px-3 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white btn-press">{busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}</button>
      </form>
    </div>
  );
};
