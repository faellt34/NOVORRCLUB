import { useCallback, useEffect, useRef, useState } from "react";
import { MessageSquare, Plus, Send, ShieldCheck, Crown, QrCode } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { api, apiError } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";

const ROLE_LABEL = { influencer: "Influencer", partner: "Parceiro", admin: "Admin" };
const ROLE_ICON = { influencer: Crown, partner: QrCode, admin: ShieldCheck };

const fmt = (d) => new Date(d).toLocaleString("pt-PT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export default function Messages() {
  const { user, refreshUnread } = useApp();
  const [convs, setConvs] = useState(null);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [newOpen, setNewOpen] = useState(false);
  const [contacts, setContacts] = useState([]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const loadConvs = useCallback(() => api.get("/messages/conversations").then((r) => { setConvs(r.data); return r.data; }).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { loadConvs(); }, [loadConvs]);

  const openConv = useCallback(async (id) => {
    setActive(id);
    try {
      const { data } = await api.get(`/messages/conversations/${id}`);
      setMessages(data.messages);
      setConvs((p) => (p || []).map((c) => (c.id === id ? { ...c, unread: 0 } : c)));
      refreshUnread();
    } catch (e) { toast.error(apiError(e)); }
  }, [refreshUnread]);

  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => api.get(`/messages/conversations/${active}`).then((r) => setMessages(r.data.messages)).catch(() => {}), 8000);
    return () => clearInterval(t);
  }, [active]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (e) => {
    e?.preventDefault();
    if (!text.trim() || !active) return;
    setSending(true);
    try {
      const { data } = await api.post(`/messages/conversations/${active}`, { text });
      setMessages((p) => [...p, data]); setText(""); loadConvs();
    } catch (err) { toast.error(apiError(err)); } finally { setSending(false); }
  };

  const openNew = async () => {
    setNewOpen(true);
    try { setContacts((await api.get("/messages/contacts")).data); } catch (e) { toast.error(apiError(e)); }
  };

  const startConv = async (contact) => {
    try {
      const { data } = await api.post("/messages/conversations", { participant_id: contact.id });
      setNewOpen(false);
      await loadConvs();
      openConv(data.id);
    } catch (e) { toast.error(apiError(e)); }
  };

  const activeConv = convs?.find((c) => c.id === active);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 data-testid="messages-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Mensagens</h1>
          <p className="text-sm text-slate-500 mt-1">Conversas internas entre admin, influencers e parceiros</p>
        </div>
        <button data-testid="new-conversation-button" onClick={openNew} className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press"><Plus className="w-4 h-4" /> Nova conversa</button>
      </div>

      <div className="card-soft grid grid-cols-1 md:grid-cols-[300px_1fr] min-h-[560px] overflow-hidden">
        <div className="border-b md:border-b-0 md:border-r border-slate-100 overflow-y-auto max-h-[560px]" data-testid="conversation-list">
          {convs === null ? <p data-testid="conversations-loading" className="p-5 text-sm text-slate-400">A carregar...</p>
            : convs.length === 0 ? (
              <div className="p-8 text-center" data-testid="conversations-empty">
                <MessageSquare className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">Sem conversas. Comece uma nova.</p>
              </div>
            ) : convs.map((c) => {
              const Icon = ROLE_ICON[c.other.role] || MessageSquare;
              return (
                <button key={c.id} data-testid={`conversation-${c.id}`} onClick={() => openConv(c.id)} className={`w-full text-left px-4 py-3 flex items-center gap-3 border-b border-slate-50 hover:bg-purple-50/50 transition-colors ${active === c.id ? "bg-purple-50" : ""}`}>
                  <img src={c.other.avatar} alt="" className="w-10 h-10 rounded-full object-cover bg-slate-200" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900 truncate">{c.other.nome}</p>
                      {c.unread > 0 && <span data-testid={`conversation-unread-${c.id}`} className="min-w-[18px] h-[18px] px-1 rounded-full bg-purple-600 text-white text-[10px] font-bold flex items-center justify-center">{c.unread}</span>}
                    </div>
                    <p className="text-[11px] text-purple-600 flex items-center gap-1"><Icon className="w-3 h-3" /> {ROLE_LABEL[c.other.role]}</p>
                    <p className="text-xs text-slate-500 truncate">{c.last_message || "Sem mensagens ainda"}</p>
                  </div>
                </button>
              );
            })}
        </div>

        <div className="flex flex-col max-h-[560px]">
          {!activeConv ? (
            <div className="flex-1 flex items-center justify-center text-center p-8" data-testid="no-conversation-selected">
              <div>
                <MessageSquare className="w-10 h-10 text-purple-200 mx-auto mb-3" />
                <p className="text-sm text-slate-500">Selecione uma conversa ou inicie uma nova.</p>
              </div>
            </div>
          ) : (
            <>
              <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-3" data-testid="conversation-header">
                <img src={activeConv.other.avatar} alt="" className="w-9 h-9 rounded-full object-cover bg-slate-200" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">{activeConv.other.nome}</p>
                  <p className="text-xs text-slate-500">{ROLE_LABEL[activeConv.other.role]} · {activeConv.other.email}</p>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#FAFAFC]" data-testid="message-list">
                {messages.length === 0 && <p className="text-xs text-slate-400 text-center py-8">Envie a primeira mensagem.</p>}
                {messages.map((m) => {
                  const mine = m.sender_id === user.id;
                  return (
                    <div key={m.id} data-testid={`message-${m.id}`} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${mine ? "bg-purple-600 text-white rounded-br-md" : "bg-white border border-slate-100 text-slate-800 rounded-bl-md"}`}>
                        <p className="whitespace-pre-wrap break-words">{m.text}</p>
                        <p className={`text-[10px] mt-1 ${mine ? "text-purple-200" : "text-slate-400"}`}>{fmt(m.date)}</p>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>
              <form onSubmit={send} className="p-3 border-t border-slate-100 flex gap-2 items-end">
                <Textarea data-testid="message-input" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }} placeholder="Escreva uma mensagem... (Enter para enviar)" className="rounded-xl bg-slate-50 min-h-[44px] max-h-32 resize-none" rows={1} />
                <button type="submit" disabled={sending || !text.trim()} data-testid="send-message-button" className="shrink-0 w-11 h-11 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white flex items-center justify-center btn-press"><Send className="w-4 h-4" /></button>
              </form>
            </>
          )}
        </div>
      </div>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent data-testid="new-conversation-dialog" className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nova conversa</DialogTitle>
            <DialogDescription>Escolha com quem quer falar. {user.role === "admin" ? "Como admin pode contactar qualquer utilizador." : "Pode contactar a equipa Robson Club e os seus parceiros de campanha."}</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-50">
            {contacts.length === 0 && <p className="text-sm text-slate-400 py-6 text-center">Sem contactos disponíveis.</p>}
            {contacts.map((c) => {
              const Icon = ROLE_ICON[c.role] || MessageSquare;
              return (
                <button key={c.id} data-testid={`contact-${c.id}`} onClick={() => startConv(c)} className="w-full flex items-center gap-3 py-2.5 px-1 hover:bg-purple-50 rounded-lg text-left">
                  <img src={c.avatar} alt="" className="w-9 h-9 rounded-full object-cover bg-slate-200" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{c.nome}</p>
                    <p className="text-xs text-slate-500 flex items-center gap-1"><Icon className="w-3 h-3" /> {ROLE_LABEL[c.role]} · {c.email}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
